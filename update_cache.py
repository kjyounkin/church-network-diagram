import json
import requests
import time

CHURCH_LAT = 41.6371503
CHURCH_LON = -93.6860107

with open('geo_cache.json', 'r') as f:
    cache = json.load(f)

print(f"Recalculating {len(cache)} routes...")
for i, (addr, geo) in enumerate(cache.items()):
    if geo is not None:
        try:
            lat, lon = geo['lat'], geo['lon']
            route_res = requests.get(f"http://router.project-osrm.org/route/v1/driving/{CHURCH_LON},{CHURCH_LAT};{lon},{lat}?overview=false")
            route_data = route_res.json()
            if route_data.get('code') == 'Ok':
                geo['drive_time'] = round(route_data['routes'][0]['duration'] / 60, 1)
                geo['drive_dist'] = round(route_data['routes'][0]['distance'] / 1609.34, 1)
        except Exception as e:
            print(f"Error on {addr}: {e}")
        time.sleep(0.1) # Fast sleep, OSRM is fast

with open('geo_cache.json', 'w') as f:
    json.dump(cache, f)

print("Updated geo_cache.json!")
