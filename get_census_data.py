import requests
url = "https://api.census.gov/data/2022/acs/acs5?get=group(B01001)&for=tract:000801&in=state:19+county:153"
resp = requests.get(url)
print(resp.status_code)
print(resp.text[:500])
