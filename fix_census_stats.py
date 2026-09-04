import json

with open("generate_tract_map.py", "r") as f:
    code = f.read()

# Fix user agent
code = code.replace(
    "headers = {'User-Agent': 'Mozilla/5.0'}",
    "headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}"
)

# Print response to verify
code = code.replace(
    "resp = requests.get(url, headers=headers)\n    census_raw = resp.json().get('data', {})",
    "resp = requests.get(url, headers=headers)\n    if resp.status_code != 200:\n        print('CENSUS API ERROR:', resp.status_code, resp.text)\n    census_raw = resp.json().get('data', {})"
)

with open("generate_tract_map.py", "w") as f:
    f.write(code)
