#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests, base64, re, socket, csv, time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse, parse_qs, unquote
from collections import defaultdict

ASIA_NORTH_AMERICA = {
    'CN': 'chn', 'HK': 'hkg', 'TW': 'twn', 'JP': 'jpn', 'KR': 'kor',
    'SG': 'sgp', 'TH': 'tha', 'VN': 'vnm', 'MY': 'mys', 'PH': 'phl',
    'ID': 'idn', 'IN': 'ind', 'PK': 'pak', 'BD': 'bgd', 'LK': 'lka',
    'KH': 'khm', 'LA': 'lao', 'MM': 'mmr', 'BN': 'brn', 'MO': 'mac',
    'US': 'usa', 'CA': 'can', 'MX': 'mex',
}

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

def measure_ping(ip, port, timeout=2):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        start = time.time()
        result = sock.connect_ex((ip, int(port)))
        latency = (time.time() - start) * 1000
        sock.close()
        return latency if result == 0 else float('inf')
    except:
        return float('inf')

def filter_nodes(vless_links):
    print(f"解析 {len(vless_links)} 个 vless 链接...")
    parsed = [p for p in [parse_vless(l) for l in vless_links] if p]
    print(f"成功解析 {len(parsed)} 个节点")

    nodes = []
    for n in parsed:
        c = get_country(n['ip'])
        if c and c.upper() in ASIA_NORTH_AMERICA:
            n['country'] = c
            nodes.append(n)
            print(f"  {n['ip']}:{n['port']} -> {c}")
    print(f"亚洲和北美节点：{len(nodes)} 个")

    by_country = defaultdict(list)
    for n in nodes:
        by_country[n['country']].append(n)

    results = []
    for country, ns in by_country.items():
        print(f"\n测试 {country} 的 {len(ns)} 个节点...")
        latencies = []
        with ThreadPoolExecutor(max_workers=20) as ex:
            futures = {ex.submit(measure_ping, n['ip'], n['port']): n for n in ns}
            for f in futures:
                n = futures[f]
                lat = f.result()
                latencies.append((lat, n))
                print(f"  {n['ip']}:{n['port']} - {lat:.2f}ms")
        latencies.sort(key=lambda x: x[0])
        for lat, n in latencies[:2]:
            abbr = ASIA_NORTH_AMERICA.get(country.upper(), country.lower())
            out = f"{n['ip']}:{n['port']}#{abbr}"
            results.append({'output': out, 'latency': lat})
            print(f"选中：{out} ({lat:.2f}ms)")
    return results

def save_to_csv(results, filename='cfbest.csv'):
    fixed = [
        'cf.090227.xyz:443#CF', 'saas.sin.fan:443#SAAS', 'store.ubi.com:443#UBI',
        'cf.danfeng.eu.org:443#DF', 'cloudflare.seeck.cn:443#CFS',
        'cu.877774.xyz:443#CFZU', 'cucc.cloudflare.seeck.cn:443#CFSU',
    ]
    with open(filename, 'w', encoding='utf-8') as f:
        for node in fixed + [r['output'] for r in results]:
            f.write(node + '\n')
    print(f"\n已保存到 {filename} (共 {len(fixed) + len(results)} 个节点)")

def main():
    url = "https://sub.995677.xyz/sub"
    print("获取 vless 订阅...")
    links = get_vless_links(url)
    if not links:
        print("未找到 vless 链接")
        return
    print(f"找到 {len(links)} 个 vless 链接\n过滤节点...")
    results = filter_nodes(links)
    if results:
        save_to_csv(results)
    else:
        print("没有符合条件的节点")

if __name__ == "__main__":
    main()
