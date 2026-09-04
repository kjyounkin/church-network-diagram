import json
import psycopg2
import requests
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

def get_tract(lat, lon):
    try:
        url = f"https://geo.fcc.gov/api/census/block/find?latitude={lat}&longitude={lon}&format=json"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            fips = data.get('Block', {}).get('FIPS', '')
            if len(fips) >= 11:
                return fips[:11]
    except Exception as e:
        pass
    return None

def main():
    with open('geo_cache.json', 'r') as f:
        geo_cache = json.load(f)

    conn = psycopg2.connect(
        dbname="warehouse", user="meltano", password="WEFC", host="postgres", port="5432"
    )
    cur = conn.cursor()
    cur.execute("""
        SELECT a.attributes_street_line_1, a.attributes_city, a.attributes_state, a.attributes_zip
        FROM raw.v_people p
        JOIN raw.pco_addresses a ON p.person_id = a.relationships_person_data_id::INTEGER
        WHERE a.attributes_street_line_1 IS NOT NULL
          AND p.membership IN ('Member', 'Regular Attender')
          AND p.status = 'active'
          AND p.primary_campus = 'Westchester EFC'
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    coords = []
    for row in rows:
        street, city, state, zip_code = row
        street = (street or "").replace("\n", " ").strip()
        city = (city or "").strip()
        state = (state or "").strip()
        zip_code = (zip_code or "").strip()
        addr_str = f"{street}, {city}, {state} {zip_code}"
        
        geo = geo_cache.get(addr_str)
        if geo and geo.get('lat') is not None:
            coords.append((geo['lat'], geo['lon']))

    print(f"Total matching people with coordinates: {len(coords)}")
    
    unique_coords = list(set(coords))
    print(f"Total unique locations to map: {len(unique_coords)}")

    coord_to_tract = {}
    
    # Batch process
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(get_tract, lat, lon): (lat, lon) for lat, lon in unique_coords}
        for i, future in enumerate(futures):
            lat, lon = futures[future]
            tract = future.result()
            if tract:
                coord_to_tract[(lat, lon)] = tract
            if (i+1) % 20 == 0:
                print(f"Processed {i+1}/{len(unique_coords)} locations...")

    tract_counts = Counter()
    for lat, lon in coords:
        tract = coord_to_tract.get((lat, lon))
        if tract:
            tract_counts[tract] += 1

    total_mapped = sum(tract_counts.values())
    print(f"\nSuccessfully mapped {total_mapped} people to tracts.")

    target_80 = total_mapped * 0.8
    print(f"Target 80%: {target_80:.1f} people")

    sorted_tracts = tract_counts.most_common()
    
    cumulative = 0
    top_tracts = []
    for tract, count in sorted_tracts:
        cumulative += count
        top_tracts.append({'tract': tract, 'count': count, 'pct': count/total_mapped*100})
        if cumulative >= target_80:
            break

    print(f"\nFewest number of tracts for 80%: {len(top_tracts)}")
    for i, t in enumerate(top_tracts):
        print(f"{i+1}. Tract {t['tract']}: {t['count']} people ({t['pct']:.1f}%)")

    with open('top_tracts.json', 'w') as f:
        json.dump(top_tracts, f, indent=2)

if __name__ == "__main__":
    main()
