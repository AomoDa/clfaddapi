#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests, base64, re, socket, csv, time, os
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse, parse_qs, unquote
from collections import defaultdict
from pathlib import Path

# 从 .env 文件加载配置
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key, value)

# 订阅地址从环境变量读取 (必须配置 .env 文件)
# 支持多个订阅地址，用逗号分隔
SUB_URLS = os.environ.get("SUB_URLS")
if not SUB_URLS:
    raise ValueError("SUB_URLS 未配置！请复制 .env.example 为 .env 并设置订阅地址（多个 URL 用逗号分隔）")

# 解析多个订阅 URL
SUB_URL_LIST = [url.strip() for url in SUB_URLS.split(',') if url.strip()]

ASIA_NORTH_AMERICA = {
    'HK': 'hkg', 'TW': 'twn', 'JP': 'jpn', 'KR': 'kor',
    'SG': 'sgp', 'TH': 'tha', 'VN': 'vnm', 'MY': 'mys', 'PH': 'phl',
    'ID': 'idn', 'IN': 'ind', 'PK': 'pak', 'BD': 'bgd', 'LK': 'lka',
    'KH': 'khm', 'LA': 'lao', 'MM': 'mmr', 'BN': 'brn', 'MO': 'mac',
    'US': 'usa', 'CA': 'can', 'MX': 'mex',
}
# 排除的国家代码
EXCLUDED_COUNTRIES = {'CN'}

def get_vless_links_from_multiple_sources(url_list):
    """
    从多个订阅 URL 获取 vless 链接，合并后去重
    """
    all_links = []
    seen = set()  # 用于去重 (基于 IP:Port)
    
    for i, url in enumerate(url_list, 1):
        print(f"\n[{i}/{len(url_list)}] 获取订阅：{url[:50]}...")
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            try:
                links = base64.b64decode(r.text).decode('utf-8').strip().split('\n')
            except:
                links = r.text.strip().split('\n')
            
            vless_links = [l for l in links if l.startswith('vless://')]
            print(f"  找到 {len(vless_links)} 个 vless 链接")
            
            # 去重：解析每个链接，检查 IP:Port 是否已存在
            for link in vless_links:
                parsed = parse_vless(link)
                if parsed:
                    key = f"{parsed['ip']}:{parsed['port']}"
                    if key not in seen:
                        seen.add(key)
                        all_links.append(link)
                    # else:
                    #     print(f"  跳过重复节点：{key}")
        except Exception as e:
            print(f"  获取失败：{e}")
    
    print(f"\n合并去重后：{len(all_links)} 个唯一节点")
    return all_links


def get_vless_links(url):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        try:
            links = base64.b64decode(r.text).decode('utf-8').strip().split('\n')
        except:
            links = r.text.strip().split('\n')
        return [l for l in links if l.startswith('vless://')]
    except Exception as e:
        print(f"获取订阅失败：{e}")
        return []

def parse_vless(link):
    try:
        p = urlparse(link)
        name = unquote(p.fragment) if p.fragment else ""
        netloc = p.netloc.split('@', 1)[1] if '@' in p.netloc else p.netloc
        if netloc.startswith('['):
            m = re.match(r'\[([^\]]+)\]:(\d+)', netloc)
            ip, port = m.groups() if m else (None, None)
        else:
            parts = netloc.rsplit(':', 1)
            ip, port = parts if len(parts) == 2 else (None, None)
        return {'ip': ip, 'port': port, 'name': name, 'link': link} if ip else None
    except:
        return None

def get_country(ip):
    try:
        r = requests.get(f"http://ip-api.com/line/{ip}?fields=countryCode", timeout=3)
        if r.status_code == 200:
            return r.text.strip()
    except:
        pass
    return None

def measure_ping(ip, port, timeout=2, rounds=3, pings_per_round=10):
    """
    测试节点延迟，多轮多次 ping 测试
    - rounds: 测试轮数 (默认 3 轮)
    - pings_per_round: 每轮 ping 次数 (默认 10 次)
    - 如果有丢包则返回 inf
    - 返回平均延迟 (毫秒)
    """
    try:
        all_latencies = []
        for round_num in range(rounds):
            round_latencies = []
            for i in range(pings_per_round):
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(timeout)
                    start = time.time()
                    result = sock.connect_ex((ip, int(port)))
                    latency = (time.time() - start) * 1000
                    sock.close()
                    if result == 0:
                        round_latencies.append(latency)
                    else:
                        return float('inf')  # 连接失败，直接返回 inf
                except:
                    return float('inf')  # 异常，直接返回 inf
            
            # 每轮检查丢包率
            if len(round_latencies) < pings_per_round:
                return float('inf')  # 有丢包，抛弃该节点
            
            all_latencies.extend(round_latencies)
            time.sleep(0.1)  # 轮间间隔
        
        # 所有轮次都无丢包，返回平均延迟
        return sum(all_latencies) / len(all_latencies)
    except:
        return float('inf')

def filter_nodes(vless_links):
    print(f"解析 {len(vless_links)} 个 vless 链接...")
    parsed = [p for p in [parse_vless(l) for l in vless_links] if p]
    print(f"成功解析 {len(parsed)} 个节点")

    nodes = []
    for n in parsed:
        c = get_country(n['ip'])
        if c and c.upper() not in EXCLUDED_COUNTRIES and c.upper() in ASIA_NORTH_AMERICA:
            n['country'] = c
            nodes.append(n)
            print(f"  {n['ip']}:{n['port']} -> {c}")
    print(f"亚洲和北美节点（已排除 CN）: {len(nodes)} 个")

    # 所有地区一起测试 ping，不分组，全局排序取 top3
    print(f"\n测试所有 {len(nodes)} 个节点的延迟 (3 轮×10 次 ping)...")
    latencies = []
    with ThreadPoolExecutor(max_workers=20) as ex:
        futures = {ex.submit(measure_ping, n['ip'], n['port']): n for n in nodes}
        for f in futures:
            n = futures[f]
            lat = f.result()
            if lat == float('inf'):
                print(f"  {n['ip']}:{n['port']} - ✗ 丢包/超时")
            else:
                print(f"  {n['ip']}:{n['port']} - {lat:.2f}ms ✓")
                latencies.append((lat, n))
    
    # 按延迟排序，取 top3
    latencies.sort(key=lambda x: x[0])
    print(f"\n有效节点：{len(latencies)} 个")
    
    results = []
    for lat, n in latencies[:3]:
        country = n['country']
        abbr = ASIA_NORTH_AMERICA.get(country.upper(), country.lower())
        out = f"{n['ip']}:{n['port']}#{abbr}"
        results.append({'output': out, 'latency': lat})
        print(f"  ✓ 选中：{out} ({lat:.2f}ms)")
    
    return results

def get_cf_top5_ips(result_csv='/opt/cfst/result.csv', top_n=5):
    """
    从 CloudflareSpeedTest 结果中获取 Top N 个最快 IP（按下载速度排序）
    返回格式：IP:Port#name
    """
    cf_ips = []
    try:
        if not os.path.exists(result_csv):
            print(f"⚠️  未找到 CloudflareSpeedTest 结果文件：{result_csv}")
            return cf_ips
        
        with open(result_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        print(f"  读取 CSV: {len(rows)} 行，列名：{reader.fieldnames}")
        
        # 按下载速度排序，跳过速度为 0 的（列名：下载速度(MB/s)，注意速度和 ( 之间没有空格）
        valid_rows = []
        for r in rows:
            speed_str = r.get('下载速度(MB/s)', '0')
            try:
                speed = float(speed_str)
                if speed > 0:
                    valid_rows.append(r)
            except:
                pass
        
        print(f"  有效 IP (速度>0): {len(valid_rows)} 个")
        
        valid_rows.sort(key=lambda x: float(x.get('下载速度(MB/s)', 0)), reverse=True)
        
        # 取前 N 个
        for i, row in enumerate(valid_rows[:top_n], 1):
            ip = row.get('IP 地址', '')
            speed = float(row.get('下载速度(MB/s)', 0))
            if ip and speed > 0:
                # 格式：IP:443#cfb1, IP:443#cfb2, ...
                cf_ips.append(f"{ip}:443#cfb{i}")
                print(f"  ✓ CF Top{i}: {ip}:443 ({speed} MB/s)")
        
        if not cf_ips:
            print(f"⚠️  CloudflareSpeedTest 结果中无有效 IP（速度>0）")
    except Exception as e:
        print(f"⚠️  读取 CloudflareSpeedTest 结果失败：{e}")
    
    return cf_ips


def save_to_csv(results, filename='cfbest.csv'):
    # 获取 CloudflareSpeedTest Top 5 IP - 取 top3
    print("\n加载 CloudflareSpeedTest Top 3 IP...")
    cf_top3 = get_cf_top5_ips(top_n=3)
    
    # 固定节点 - 取前 4 个
    fixed = [
        'cf.090227.xyz:443#CF', 'saas.sin.fan:443#SAAS', 'store.ubi.com:443#UBI',
        'cf.danfeng.eu.org:443#DF', 'cloudflare.seeck.cn:443#CFS',
        'cu.877774.xyz:443#CFZU', 'cucc.cloudflare.seeck.cn:443#CFSU',
    ]
    fixed_nodes = fixed[:4]
    
    # VLESS 优选节点 - 已经是全局 top3
    vless_nodes = [r['output'] for r in results]
    
    # 合并：固定节点 4 个 + CF Top3 + VLESS Top3 = 10 个
    all_nodes = fixed_nodes + cf_top3 + vless_nodes
    
    with open(filename, 'w', encoding='utf-8') as f:
        for node in all_nodes:
            f.write(node + '\n')
    
    print(f"\n已保存到 {filename} (共 {len(all_nodes)} 个节点)")
    print(f"  • 固定节点：{len(fixed_nodes)} 个")
    print(f"  • CF Top3: {len(cf_top3)} 个")
    print(f"  • VLESS Top3: {len(vless_nodes)} 个")

def main():
    print(f"从 {len(SUB_URL_LIST)} 个订阅源获取 VLESS 节点...")
    print("=" * 60)
    
    # 从多个订阅源获取节点，合并去重
    links = get_vless_links_from_multiple_sources(SUB_URL_LIST)
    
    if not links:
        print("\n未找到 vless 链接")
        return
    
    print(f"\n总共 {len(links)} 个唯一 vless 链接\n开始过滤节点...")
    print("=" * 60)
    
    results = filter_nodes(links)
    if results:
        save_to_csv(results)
    else:
        print("没有符合条件的节点")

if __name__ == "__main__":
    main()
