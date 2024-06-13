import requests
import re
from base64 import b64decode
from urllib.parse import urlparse, parse_qs,unquote

def getAPI(url):
	response = requests.get(url)
	ip_addresses = []
	ips = []
	idx = 1 
	if response.status_code == 200:
		s1 = response.content
		s2 = b64decode(s1).decode("utf-8")
		s3 = unquote(s2)
		json_data = s3.split("\n")
		for item in json_data:
			rlt = extract_vless_info(item)
			if len(rlt)>0:
				server=rlt[0]
				server_port=rlt[1]
				if server in ips:
					continue
				ips.append(server)
				ip_addresses.append(f"{server}:{server_port}#HKG{idx}")
				idx = idx + 1  	
	return(ip_addresses)


def w2d(dat):
	if len(dat) > 0 :
		csv_file_path = "./myips.csv"
		with open(csv_file_path, 'w', newline='') as file:
			for ip in dat[:30]:
				file.write(str(ip).strip() + "\n") 


def isselect(tag):
	vls = ["HKG","HK","hkg","hk","联通","电信","移动"]
	for v in vls : 
		if v in tag:
			return(True)
	return(False)		


def extract_vless_info(vless_url):
	pattern = re.compile(r"vless://[^@]+@([^:]+):(\d+).+#(.+)")
	match = pattern.search(vless_url)
	if match:
		server_ip = match.group(1)
		port = match.group(2)
		name = match.group(3)
		if isselect(name):
			return([server_ip, port])
	return([])


if __name__ == '__main__':
	api_url = "https://alvless.comorg.us.kg/CMorg"
	w2d(getAPI(api_url))

