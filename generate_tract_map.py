import json
import psycopg2
import geopandas as gpd
from shapely.geometry import Point
import pandas as pd
import warnings
from shapely.errors import ShapelyDeprecationWarning

warnings.filterwarnings("ignore", category=ShapelyDeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

def main():
    print("Loading Tract GeoJSON...")
    gdf_tracts = gpd.read_file('iowa_tracts.geojson')
    
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
    if gdf_tracts.crs != "EPSG:4326":
        gdf_tracts = gdf_tracts.to_crs("EPSG:4326")

    print("Spatial joining...")
    joined = gpd.sjoin(gdf_people, gdf_tracts, how="inner", predicate="intersects")
    tract_counts = joined['GEOID'].value_counts().to_dict()
    total_people = sum(tract_counts.values())

    gdf_tracts['church_pop'] = gdf_tracts['GEOID'].map(tract_counts).fillna(0)

    # Filter to only relevant tracts to keep json small
    church_tract_id = "19153000801"
    active_tracts = gdf_tracts[(gdf_tracts['church_pop'] > 0) | (gdf_tracts['GEOID'] == church_tract_id)].copy()

    print("Building full contiguous sequence...")
    selected_set = set()
    sequence = []
    current_pop = 0

    if church_tract_id in active_tracts['GEOID'].values:
        selected_set.add(church_tract_id)
        current_pop += tract_counts.get(church_tract_id, 0)
        sequence.append({'GEOID': church_tract_id, 'cumulative_pct': (current_pop / total_people) * 100, 'cumulative_pop': current_pop})

    # Loop until all tracts are sequenced
    while len(selected_set) < len(active_tracts):
        # use union_all to avoid deprecation warning if available, else unary_union
        try:
            selected_geom = active_tracts[active_tracts['GEOID'].isin(selected_set)].geometry.union_all()
        except:
            selected_geom = active_tracts[active_tracts['GEOID'].isin(selected_set)].geometry.unary_union
            
        candidates = active_tracts[
            (~active_tracts['GEOID'].isin(selected_set)) & 
            (active_tracts.geometry.intersects(selected_geom))
        ]
        
        if len(candidates) > 0:
            best_id = candidates.loc[candidates['church_pop'].idxmax()]['GEOID']
        else:
            remaining = active_tracts[~active_tracts['GEOID'].isin(selected_set)]
            best_id = remaining.loc[remaining['church_pop'].idxmax()]['GEOID']
            
        selected_set.add(best_id)
        current_pop += tract_counts.get(best_id, 0)
        sequence.append({'GEOID': best_id, 'cumulative_pct': (current_pop / total_people) * 100, 'cumulative_pop': current_pop})

    pct_map = {item['GEOID']: item['cumulative_pct'] for item in sequence}
    pop_map = {item['GEOID']: item['cumulative_pop'] for item in sequence}
    active_tracts['cumulative_pct'] = active_tracts['GEOID'].map(pct_map)
    active_tracts['cumulative_pop'] = active_tracts['GEOID'].map(pop_map)

    # Output to GeoJSON
    geojson_str = active_tracts[['GEOID', 'church_pop', 'cumulative_pct', 'cumulative_pop', 'geometry']].to_json()

    print("Generating interactive HTML...")
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Interactive Core Tracts</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        body {{ margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0d1117; color: #c9d1d9; }}
        #map {{ width: 100vw; height: 100vh; }}
        .nav {{ position: absolute; top: 20px; left: 60px; z-index: 1000; background: rgba(13, 17, 23, 0.8); padding: 10px; border-radius: 8px; border: 1px solid #30363d; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }}
        .nav a {{ color: #58a6ff; text-decoration: none; border: 1px solid #58a6ff; padding: 5px 10px; border-radius: 4px; font-size: 14px; margin-right: 10px; }}
        .controls {{ position: absolute; top: 80px; left: 60px; z-index: 1000; background: rgba(13, 17, 23, 0.9); padding: 20px; border-radius: 8px; border: 1px solid #30363d; width: 300px; box-shadow: 0 4px 6px rgba(0,0,0,0.5); }}
        .slider-container {{ margin-top: 15px; }}
        input[type=range] {{ width: 100%; cursor: pointer; }}
        .stats {{ margin-top: 15px; font-size: 14px; color: #8b949e; }}
        .stats span {{ color: #c9d1d9; font-weight: bold; }}
        .info-panel {{ background: rgba(13, 17, 23, 0.9); border: 1px solid #30363d; border-radius: 5px; padding: 10px; color: #c9d1d9; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="nav">
        <a href="index.html">&larr; Network</a>
        <a href="geo_map.html">Geo Map &rarr;</a>
    </div>
    
    <div class="controls">
        <h3 style="margin: 0 0 10px 0; color: #58a6ff;">Core Congregation Footprint</h3>
        <p style="margin: 0; font-size: 12px; color: #8b949e;">Adjust the slider to expand or shrink the contiguous neighborhood footprint.</p>
        
        <div class="slider-container">
            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                <span>Target Coverage:</span>
                <span style="color: #ffeb3b; font-weight: bold; font-size: 16px;" id="pctLabel">66%</span>
            </div>
            <input type="range" id="coverageSlider" min="1" max="100" value="66">
        </div>
        
        <div class="stats">
            <div>Tracts Selected: <span id="tractCount">0</span></div>
            <div>People Covered: <span id="peopleCount">0</span> / {total_people}</div>
        </div>
    </div>

    <div id="map"></div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        const map = L.map('map').setView([41.637, -93.686], 11);
        
        L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
            subdomains: 'abcd',
            maxZoom: 20
        }}).addTo(map);
        
        const geojsonData = {geojson_str};
        const churchTractId = "{church_tract_id}";
        let geojsonLayer;
        
        // Church marker
        L.marker([41.6371503, -93.6860107]).addTo(map)
            .bindPopup("<b>Westchester EFC</b>");

        const slider = document.getElementById('coverageSlider');
        const pctLabel = document.getElementById('pctLabel');
        const tractCountLabel = document.getElementById('tractCount');
        const peopleCountLabel = document.getElementById('peopleCount');

        let info = L.control();
        info.onAdd = function (map) {{
            this._div = L.DomUtil.create('div', 'info-panel');
            this.update();
            return this._div;
        }};
        info.update = function (props) {{
            this._div.innerHTML = props ?
                '<b>Tract: ' + props.GEOID + '</b><br />' + props.church_pop + ' Core People'
                : 'Hover over a tract';
        }};
        info.addTo(map);

        function highlightFeature(e) {{
            var layer = e.target;
            layer.setStyle({{
                weight: 3,
                color: '#fff',
                dashArray: '',
                fillOpacity: 0.8
            }});
            layer.bringToFront();
            info.update(layer.feature.properties);
        }}

        function resetHighlight(e) {{
            geojsonLayer.resetStyle(e.target);
            info.update();
        }}

        function onEachFeature(feature, layer) {{
            layer.on({{
                mouseover: highlightFeature,
                mouseout: resetHighlight
            }});
        }}

        function getStyle(feature, threshold) {{
            const props = feature.properties;
            if (props.GEOID === churchTractId) {{
                // Always highlight the church tract as yellow if it's within the threshold, else dark yellow
                return props.cumulative_pct <= threshold ? 
                    {{ fillColor: '#ffeb3b', color: '#ffffff', weight: 2, fillOpacity: 0.8 }} :
                    {{ fillColor: '#ffeb3b', color: '#888888', weight: 1, fillOpacity: 0.2 }};
            }}
            
            if (props.cumulative_pct <= threshold) {{
                return {{ fillColor: '#9c27b0', color: '#ffffff', weight: 1.5, fillOpacity: 0.6 }};
            }} else if (props.church_pop > 0) {{
                return {{ fillColor: '#2196f3', color: '#2196f3', weight: 1, fillOpacity: 0.15 }};
            }} else {{
                return {{ fillOpacity: 0, weight: 0 }};
            }}
        }}

        function updateMap() {{
            const threshold = parseInt(slider.value);
            pctLabel.innerText = threshold + '%';
            
            let tractsIncluded = 0;
            let maxPopIncluded = 0;
            
            if (geojsonLayer) {{
                map.removeLayer(geojsonLayer);
            }}
            
            geojsonLayer = L.geoJson(geojsonData, {{
                style: function(feature) {{
                    return getStyle(feature, threshold);
                }},
                onEachFeature: onEachFeature,
                filter: function(feature) {{
                    return feature.properties.church_pop > 0 || feature.properties.GEOID === churchTractId;
                }}
            }}).addTo(map);
            
            // Calculate stats
            geojsonData.features.forEach(f => {{
                if (f.properties.cumulative_pct <= threshold) {{
                    tractsIncluded++;
                    if (f.properties.cumulative_pop > maxPopIncluded) {{
                        maxPopIncluded = f.properties.cumulative_pop;
                    }}
                }}
            }});
            
            tractCountLabel.innerText = tractsIncluded;
            peopleCountLabel.innerText = maxPopIncluded;
        }}

        slider.addEventListener('input', updateMap);
        
        // Initial render
        updateMap();
    </script>
</body>
</html>
"""
    with open('contiguous_tracts.html', 'w') as f:
        f.write(html)
    print("Saved contiguous_tracts.html")

if __name__ == "__main__":
    main()
