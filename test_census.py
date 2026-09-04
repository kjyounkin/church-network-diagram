import requests
url = "http://api.censusreporter.org/1.0/data/show/latest?table_ids=B01001&geo_ids=14000US19153000801,14000US19153010216"
headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
resp = requests.get(url, headers=headers)
print(resp.status_code)
data = resp.json()
print(list(data.get('data', {}).keys()))
