import json
import psycopg2
import geopandas as gpd
from shapely.geometry import Point
import folium
import pandas as pd

def main():
    # 1. Load Tracts
    print("Loading Tract GeoJSON...")
    gdf_tracts = gpd.read_file('iowa_tracts.geojson')
    # Make sure we have GEOID
    
    # 2. Fetch People
    print("Fetching people...")
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
            coords.append(Point(geo['lon'], geo['lat']))

    gdf_people = gpd.GeoDataFrame(geometry=coords, crs="EPSG:4326")
    
    # Ensure tracts are in EPSG:4326
    if gdf_tracts.crs != "EPSG:4326":
        gdf_tracts = gdf_tracts.to_crs("EPSG:4326")

    # 3. Spatial Join
    print("Spatial joining...")
    joined = gpd.sjoin(gdf_people, gdf_tracts, how="inner", predicate="intersects")
    
    # Count people per tract
    tract_counts = joined['GEOID'].value_counts().to_dict()
    total_people = sum(tract_counts.values())
    target_66 = total_people * 0.66
    print(f"Total Mapped: {total_people}, Target 66%: {target_66:.1f}")

    # Assign counts to tract dataframe
    gdf_tracts['church_pop'] = gdf_tracts['GEOID'].map(tract_counts).fillna(0)

    # 4. Greedy Contiguous Search
    print("Building contiguous region...")
    church_tract_id = "19153000801"
    
    # In case church tract wasn't joined or has 0 pop, but we know it has 11
    selected_tracts = set([church_tract_id])
    current_pop = tract_counts.get(church_tract_id, 0)
    
    while current_pop < target_66:
        # Find neighbors of selected tracts
        selected_geom = gdf_tracts[gdf_tracts['GEOID'].isin(selected_tracts)].geometry.unary_union
        
        # Candidates are tracts that intersect the selected_geom and are not already selected
        candidates = gdf_tracts[
            (~gdf_tracts['GEOID'].isin(selected_tracts)) & 
            (gdf_tracts.geometry.intersects(selected_geom))
        ]
        
        if len(candidates) > 0 and candidates['church_pop'].max() > 0:
            # Pick the neighbor with the highest church population
            best_tract = candidates.loc[candidates['church_pop'].idxmax()]['GEOID']
            selected_tracts.add(best_tract)
            current_pop += tract_counts.get(best_tract, 0)
        else:
            # If all touching neighbors have 0 people, jump to the highest remaining tract anywhere
            remaining = gdf_tracts[~gdf_tracts['GEOID'].isin(selected_tracts)]
            if len(remaining) > 0 and remaining['church_pop'].max() > 0:
                best_tract = remaining.loc[remaining['church_pop'].idxmax()]['GEOID']
                selected_tracts.add(best_tract)
                current_pop += tract_counts.get(best_tract, 0)
            else:
                break # We ran out of people entirely

    print(f"Selected {len(selected_tracts)} contiguous tracts with {current_pop} people.")

    # 5. Generate Folium Map
    print("Generating map...")
    m = folium.Map(location=[41.637, -93.686], zoom_start=11, tiles="CartoDB dark_matter")

    # Filter to only the relevant tracts to keep HTML size small
    # Let's include any tract that has > 0 people, plus the selected ones
    gdf_display = gdf_tracts[(gdf_tracts['church_pop'] > 0) | (gdf_tracts['GEOID'].isin(selected_tracts))]

    def style_function(feature):
        geoid = feature['properties']['GEOID']
        pop = feature['properties']['church_pop']
        
        if geoid in selected_tracts:
            if geoid == church_tract_id:
                return {'fillColor': '#ffeb3b', 'color': '#ffffff', 'weight': 2, 'fillOpacity': 0.7} # Church = Yellow
            return {'fillColor': '#9c27b0', 'color': '#ffffff', 'weight': 1, 'fillOpacity': 0.6} # Core = Purple
        elif pop > 0:
            return {'fillColor': '#2196f3', 'color': '#2196f3', 'weight': 1, 'fillOpacity': 0.2} # Other people = Blue
        else:
            return {'fillOpacity': 0, 'weight': 0}

    # Add GeoJson to map
    folium.GeoJson(
        gdf_display,
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(
            fields=['GEOID', 'church_pop'],
            aliases=['Tract GEOID:', 'Church Core Pop:'],
            style="background-color: #333; color: white;"
        )
    ).add_to(m)
    
    # Add Church Marker
    folium.Marker(
        [41.6371503, -93.6860107],
        popup="Westchester EFC",
        icon=folium.Icon(color="orange", icon="info-sign")
    ).add_to(m)

    m.save('contiguous_tracts.html')
    print("Saved contiguous_tracts.html")

if __name__ == "__main__":
    main()
