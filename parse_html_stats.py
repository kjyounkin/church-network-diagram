import json
import re

with open("contiguous_tracts.html", "r") as f:
    html = f.read()

geo_match = re.search(r'const geojsonData = (\{.*?\});', html, re.DOTALL)
census_match = re.search(r'const censusStats = (\{.*?\});', html, re.DOTALL)

geo = json.loads(geo_match.group(1))
census = json.loads(census_match.group(1))

selected_tracts = [f['properties']['GEOID'] for f in geo['features'] if f['properties']['cumulative_pct'] <= 50]

agg = {
    'total_pop': 0, 'kids': 0, 'total_families': 0, 'single_parent_kids': 0,
    'total_marital': 0, 'married': 0, 'divorced_separated': 0, 'white': 0,
    'hispanic': 0, 'total_lang': 0, 'lep': 0, 'total_pov': 0, 'in_poverty': 0,
    'total_housing': 0, 'renters': 0,
    'age_0_17': 0, 'age_18_34': 0, 'age_35_49': 0, 'age_50_64': 0, 'age_65_plus': 0
}

for gid in selected_tracts:
    stats = census.get(gid, {})
    for k in agg:
        agg[k] += stats.get(k, 0)

for k, v in agg.items():
    if k in ['total_pop', 'total_families', 'total_marital', 'total_lang', 'total_pov', 'total_housing']:
        continue
    base = agg['total_pop']
    if k == 'single_parent_kids': base = agg['total_families']
    if k in ['married', 'divorced_separated']: base = agg['total_marital']
    if k == 'lep': base = agg['total_lang']
    if k == 'in_poverty': base = agg['total_pov']
    if k == 'renters': base = agg['total_housing']
    
    pct = (v / base * 100) if base else 0
    print(f"{k}: {pct:.1f}% ({v})")

print(f"Total Pop: {agg['total_pop']}")
print(f"Tracts: {len(selected_tracts)}")
