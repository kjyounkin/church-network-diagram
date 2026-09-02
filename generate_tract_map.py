import json
import psycopg2
import geopandas as gpd
from shapely.geometry import Point
import requests
import warnings
from shapely.errors import ShapelyDeprecationWarning

warnings.filterwarnings("ignore", category=ShapelyDeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

def get_est(tract_data, table, var_id):
    try:
        return tract_data[table]['estimate'][f"{table}{str(var_id).zfill(3)}"]
    except KeyError:
        return 0

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
        SELECT a.attributes_street_line_1, a.attributes_city, a.attributes_state, a.attributes_zip, p.age
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
    ages = []
    for row in rows:
        street, city, state, zip_code, age = row
        street = (street or "").replace("\n", " ").strip()
        city = (city or "").strip()
        state = (state or "").strip()
        zip_code = (zip_code or "").strip()
        addr_str = f"{street}, {city}, {state} {zip_code}"
        
        geo = geo_cache.get(addr_str)
        if geo and geo.get('lat') is not None:
            coords.append(Point(geo['lon'], geo['lat']))
            
            # Map age to bucket
            if age is None:
                b = "unknown"
            elif age <= 17:
                b = "age_0_17"
            elif age <= 34:
                b = "age_18_34"
            elif age <= 49:
                b = "age_35_49"
            elif age <= 64:
                b = "age_50_64"
            else:
                b = "age_65_plus"
            ages.append(b)

    gdf_people = gpd.GeoDataFrame({'age_bucket': ages}, geometry=coords, crs="EPSG:4326")
    if gdf_tracts.crs != "EPSG:4326":
        gdf_tracts = gdf_tracts.to_crs("EPSG:4326")

    print("Spatial joining...")
    joined = gpd.sjoin(gdf_people, gdf_tracts, how="inner", predicate="intersects")
    tract_counts = joined['GEOID'].value_counts().to_dict()
    total_people = sum(tract_counts.values())
    
    church_stats = {}
    for geoid, group in joined.groupby('GEOID'):
        counts = group['age_bucket'].value_counts().to_dict()
        church_stats[geoid] = {
            'pop': len(group),
            'age_0_17': counts.get('age_0_17', 0),
            'age_18_34': counts.get('age_18_34', 0),
            'age_35_49': counts.get('age_35_49', 0),
            'age_50_64': counts.get('age_50_64', 0),
            'age_65_plus': counts.get('age_65_plus', 0),
        }

    gdf_tracts['church_pop'] = gdf_tracts['GEOID'].map(tract_counts).fillna(0)

    church_tract_id = "19153000801"
    active_tracts = gdf_tracts[(gdf_tracts['church_pop'] > 0) | (gdf_tracts['GEOID'] == church_tract_id)].copy()

    print("Fetching Census Data for Mission Summary...")
    geoids_list = list(active_tracts['GEOID'].unique())
    geo_ids_param = ",".join([f"14000US{gid}" for gid in geoids_list])
    
    tables = "B01001,B11003,B12001,B03002,C16001,B19001,B17001,B25003"
    url = f"http://api.censusreporter.org/1.0/data/show/latest?table_ids={tables}&geo_ids={geo_ids_param}"
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print('CENSUS API ERROR:', resp.status_code, resp.text)
    census_raw = resp.json().get('data', {})
    
    census_stats = {}
    for gid in geoids_list:
        full_gid = f"14000US{gid}"
        tract_data = census_raw.get(full_gid, {})
        if not tract_data:
            continue
        stats = {}
        stats['total_pop'] = get_est(tract_data, 'B01001', 1)
        stats['kids'] = sum(get_est(tract_data, 'B01001', i) for i in [3,4,5,6, 27,28,29,30])
        stats['age_0_17'] = stats['kids']
        stats['age_18_34'] = sum(get_est(tract_data, 'B01001', i) for i in [7,8,9,10,11,12, 31,32,33,34,35,36])
        stats['age_35_49'] = sum(get_est(tract_data, 'B01001', i) for i in [13,14,15, 37,38,39])
        stats['age_50_64'] = sum(get_est(tract_data, 'B01001', i) for i in [16,17,18,19, 40,41,42,43])
        stats['age_65_plus'] = sum(get_est(tract_data, 'B01001', i) for i in [20,21,22,23,24,25, 44,45,46,47,48,49])
        stats['total_families'] = get_est(tract_data, 'B11003', 1)
        stats['single_parent_kids'] = get_est(tract_data, 'B11003', 10) + get_est(tract_data, 'B11003', 16)
        stats['total_marital'] = get_est(tract_data, 'B12001', 1)
        separated = get_est(tract_data, 'B12001', 7) + get_est(tract_data, 'B12001', 16)
        stats['married'] = get_est(tract_data, 'B12001', 4) + get_est(tract_data, 'B12001', 13) - separated
        divorced = get_est(tract_data, 'B12001', 10) + get_est(tract_data, 'B12001', 19)
        stats['divorced_separated'] = divorced + separated
        stats['white'] = get_est(tract_data, 'B03002', 3)
        stats['hispanic'] = get_est(tract_data, 'B03002', 12)
        stats['total_lang'] = get_est(tract_data, 'C16001', 1)
        stats['lep'] = sum(get_est(tract_data, 'C16001', i) for i in [5, 8, 11, 14, 17, 20, 23, 26, 29, 32, 35, 38])
        stats['total_pov'] = get_est(tract_data, 'B17001', 1)
        stats['in_poverty'] = get_est(tract_data, 'B17001', 2)
        stats['total_housing'] = get_est(tract_data, 'B25003', 1)
        stats['renters'] = get_est(tract_data, 'B25003', 3)
        census_stats[gid] = stats

    print("Building full contiguous sequence...")
    selected_set = set()
    sequence = []
    current_pop = 0

    if church_tract_id in active_tracts['GEOID'].values:
        selected_set.add(church_tract_id)
        current_pop += tract_counts.get(church_tract_id, 0)
        sequence.append({'GEOID': church_tract_id, 'cumulative_pct': (current_pop / total_people) * 100, 'cumulative_pop': current_pop})

    while len(selected_set) < len(active_tracts):
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

    geojson_str = active_tracts[['GEOID', 'church_pop', 'cumulative_pct', 'cumulative_pop', 'geometry']].to_json()
    census_stats_json = json.dumps(census_stats)
    church_stats_json = json.dumps(church_stats)

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Interactive Core Tracts</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        body {{ margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0d1117; color: #c9d1d9; overflow: hidden; }}
        #map {{ width: 100vw; height: 100vh; }}
        .nav {{ position: absolute; top: 20px; left: 60px; z-index: 1000; background: rgba(13, 17, 23, 0.8); padding: 10px; border-radius: 8px; border: 1px solid #30363d; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }}
        .nav a {{ color: #58a6ff; text-decoration: none; border: 1px solid #58a6ff; padding: 5px 10px; border-radius: 4px; font-size: 14px; margin-right: 10px; }}
        .controls {{ position: absolute; top: 80px; left: 60px; z-index: 1000; background: rgba(13, 17, 23, 0.95); padding: 20px; border-radius: 8px; border: 1px solid #30363d; width: 320px; box-shadow: 0 4px 6px rgba(0,0,0,0.5); }}
        
        .mission-panel {{ position: absolute; top: 20px; right: 20px; z-index: 1000; background: rgba(13, 17, 23, 0.95); padding: 20px; border-radius: 8px; border: 1px solid #30363d; width: 300px; box-shadow: 0 4px 6px rgba(0,0,0,0.5); max-height: 90vh; overflow-y: auto; }}
        .mission-panel h3 {{ color: #ffeb3b; margin-top: 0; border-bottom: 1px solid #30363d; padding-bottom: 10px; }}
        .stat-row {{ display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 14px; border-bottom: 1px dotted #30363d; padding-bottom: 4px; }}
        .stat-label {{ color: #8b949e; }}
        .stat-val {{ color: #c9d1d9; font-weight: bold; }}
        
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
        <a href="core_50_mission_summary.html">Mission Summary &rarr;</a>
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
    
    <div class="mission-panel">
        <h3>Who is my Neighbor?</h3>
        <p style="font-size: 12px; color: #8b949e; margin-top:-5px; margin-bottom: 15px;">Combined census profile of the highlighted purple footprint.</p>
        
        <h4 style="margin: 0 0 5px 0; font-size: 13px; color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 5px;">Population & Penetration</h4>
        <div class="stat-row"><span class="stat-label">Neighborhood Pop.</span><span class="stat-val" id="ms-pop">0</span></div>
        <div class="stat-row"><span class="stat-label">Church Pop.</span><span class="stat-val" id="ch-pop" style="color:#ffeb3b">0</span></div>
        <div class="stat-row"><span class="stat-label">Church Ratio</span><span class="stat-val" id="ms-ratio">0%</span></div>

        <h4 style="margin: 15px 0 5px 0; font-size: 13px; color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 5px;">Age Profile <span style="font-size: 10px; color:#888; float:right;">(Neighborhood vs Church)</span></h4>
        <div class="stat-row"><span class="stat-label">Ages 0-17</span><span class="stat-val"><span id="ms-age-0-17">0%</span> <span style="color:#888;font-size:11px;margin:0 4px;">vs</span> <span id="ch-age-0-17" style="color:#ffeb3b">0%</span></span></div>
        <div class="stat-row"><span class="stat-label">Ages 18-34</span><span class="stat-val"><span id="ms-age-18-34">0%</span> <span style="color:#888;font-size:11px;margin:0 4px;">vs</span> <span id="ch-age-18-34" style="color:#ffeb3b">0%</span></span></div>
        <div class="stat-row"><span class="stat-label">Ages 35-49</span><span class="stat-val"><span id="ms-age-35-49">0%</span> <span style="color:#888;font-size:11px;margin:0 4px;">vs</span> <span id="ch-age-35-49" style="color:#ffeb3b">0%</span></span></div>
        <div class="stat-row"><span class="stat-label">Ages 50-64</span><span class="stat-val"><span id="ms-age-50-64">0%</span> <span style="color:#888;font-size:11px;margin:0 4px;">vs</span> <span id="ch-age-50-64" style="color:#ffeb3b">0%</span></span></div>
        <div class="stat-row"><span class="stat-label">Ages 65+</span><span class="stat-val"><span id="ms-age-65-plus">0%</span> <span style="color:#888;font-size:11px;margin:0 4px;">vs</span> <span id="ch-age-65-plus" style="color:#ffeb3b">0%</span></span></div>
        
        <h4 style="margin: 15px 0 5px 0; font-size: 13px; color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 5px;">Neighborhood Status</h4>
        <div class="stat-row"><span class="stat-label">Poverty Rate</span><span class="stat-val" id="ms-poverty">0%</span></div>
        <div class="stat-row"><span class="stat-label">Single-Parent Families</span><span class="stat-val" id="ms-singleparent">0%</span></div>
        <div class="stat-row"><span class="stat-label">Married Adults</span><span class="stat-val" id="ms-married">0%</span></div>
        <div class="stat-row"><span class="stat-label">Divorced/Separated</span><span class="stat-val" id="ms-divorced">0%</span></div>
        <div class="stat-row"><span class="stat-label">White Pop.</span><span class="stat-val" id="ms-white">0%</span></div>
        <div class="stat-row"><span class="stat-label">Hispanic Pop.</span><span class="stat-val" id="ms-hispanic">0%</span></div>
        <div class="stat-row"><span class="stat-label">Limited English</span><span class="stat-val" id="ms-lep">0%</span></div>
        <div class="stat-row"><span class="stat-label">Renters</span><span class="stat-val" id="ms-renters">0%</span></div>
        <div style="font-size:10px; color:#888; margin-top:15px; font-style:italic; line-height: 1.3;">Note: The US Census Bureau is prohibited by law from collecting data on religious affiliation, so tract-level religious stats are unavailable.</div>
    </div>

    <div id="map"></div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>

        const map = L.map('map').setView([41.637, -93.686], 11);
        
        L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
            attribution: 'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ',
            subdomains: 'abcd',
            maxZoom: 20
        }}).addTo(map);
        
        const geojsonData = {geojson_str};
        const censusStats = {census_stats_json};
        const churchStats = {church_stats_json};
        const churchTractId = "{church_tract_id}";
        let geojsonLayer;
        
        L.marker([41.6371503, -93.6860107]).addTo(map).bindPopup("<b>Westchester EFC</b>");

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
                '<b>Tract: ' + props.GEOID + '</b><br />' + props.church_pop + ' Core People<br/><span style="font-size:11px;color:#888;">Click to toggle</span>'
                : 'Hover over a tract';
        }};
        info.addTo(map);

        let selectedTractIds = new Set();
        let userOverrodeSlider = false;

        function toggleTract(e) {{
            const geoid = e.target.feature.properties.GEOID;
            if (selectedTractIds.has(geoid)) {{
                selectedTractIds.delete(geoid);
            }} else {{
                selectedTractIds.add(geoid);
            }}
            userOverrodeSlider = true;
            renderState();
        }}

        function highlightFeature(e) {{
            var layer = e.target;
            layer.setStyle({{ weight: 3, color: '#fff', dashArray: '', fillOpacity: 0.8 }});
            layer.bringToFront();
            info.update(layer.feature.properties);
        }}

        function resetHighlight(e) {{
            e.target.setStyle(getStyle(e.target.feature));
            info.update();
        }}

        function formatPct(val, total) {{
            if (total === 0 || !total) return "0%";
            return (val / total * 100).toFixed(1) + "%";
        }}

        function getStyle(feature) {{
            const props = feature.properties;
            const isSelected = selectedTractIds.has(props.GEOID);
            
            if (props.GEOID === churchTractId) {{
                return isSelected ? 
                    {{ fillColor: '#ffeb3b', color: '#ffffff', weight: 3, fillOpacity: 0.8 }} :
                    {{ fillColor: '#ffeb3b', color: '#888888', weight: 1, fillOpacity: 0.2 }};
            }}
            
            if (isSelected) {{
                return {{ fillColor: '#9c27b0', color: '#ffffff', weight: 2, fillOpacity: 0.6 }};
            }} else if (props.church_pop > 0) {{
                return {{ fillColor: '#2196f3', color: '#2196f3', weight: 1, fillOpacity: 0.15 }};
            }} else {{
                return {{ fillOpacity: 0, weight: 0 }};
            }}
        }}

        geojsonLayer = L.geoJson(geojsonData, {{
            style: function(feature) {{ return getStyle(feature); }},
            onEachFeature: function(feature, layer) {{
                layer.on({{ mouseover: highlightFeature, mouseout: resetHighlight, click: toggleTract }});
            }},
            filter: function(feature) {{
                return feature.properties.church_pop > 0 || feature.properties.GEOID === churchTractId;
            }}
        }}).addTo(map);

        function updateMap() {{
            const threshold = parseInt(slider.value);
            
            selectedTractIds.clear();
            geojsonData.features.forEach(f => {{
                if (f.properties.cumulative_pct <= threshold) {{
                    selectedTractIds.add(f.properties.GEOID);
                }}
            }});
            userOverrodeSlider = false;
            
            renderState();
        }}

        function renderState() {{
            let tractsIncluded = 0;
            let maxPopIncluded = 0;
            
            let agg = {{
                total_pop: 0, kids: 0, total_families: 0, single_parent_kids: 0,
                total_marital: 0, married: 0, divorced_separated: 0, white: 0,
                hispanic: 0, total_lang: 0, lep: 0, total_pov: 0, in_poverty: 0,
                total_housing: 0, renters: 0,
                age_0_17: 0, age_18_34: 0, age_35_49: 0, age_50_64: 0, age_65_plus: 0
            }};
            let c_agg = {{
                pop: 0, age_0_17: 0, age_18_34: 0, age_35_49: 0, age_50_64: 0, age_65_plus: 0
            }};
            
            geojsonLayer.eachLayer(function(layer) {{
                layer.setStyle(getStyle(layer.feature));
            }});
            
            if (userOverrodeSlider) {{
                pctLabel.innerText = "Custom";
            }} else {{
                pctLabel.innerText = slider.value + '%';
            }}
            
            geojsonData.features.forEach(f => {{
                if (selectedTractIds.has(f.properties.GEOID)) {{
                    tractsIncluded++;
                    maxPopIncluded += (f.properties.church_pop || 0);
                    
                    let tractStats = censusStats[f.properties.GEOID];
                    if (tractStats) {{
                        for (let key in agg) {{
                            agg[key] += (tractStats[key] || 0);
                        }}
                    }}
                    let cStats = churchStats[f.properties.GEOID];
                    if (cStats) {{
                        for (let key in c_agg) {{
                            c_agg[key] += (cStats[key] || 0);
                        }}
                    }}
                }}
            }});
            
            tractCountLabel.innerText = tractsIncluded;
            peopleCountLabel.innerText = maxPopIncluded;
            
            document.getElementById('ms-pop').innerText = agg.total_pop.toLocaleString();
            document.getElementById('ch-pop').innerText = c_agg.pop.toLocaleString();
            
            if (agg.total_pop > 0 && c_agg.pop > 0) {{
                let pct = (c_agg.pop / agg.total_pop * 100).toFixed(2);
                let ratio = Math.round(agg.total_pop / c_agg.pop);
                document.getElementById('ms-ratio').innerText = pct + "% (1 in " + ratio.toLocaleString() + ")";
            }} else {{
                document.getElementById('ms-ratio').innerText = "0%";
            }}

            document.getElementById('ms-age-0-17').innerText = formatPct(agg.age_0_17, agg.total_pop);
            document.getElementById('ms-age-18-34').innerText = formatPct(agg.age_18_34, agg.total_pop);
            document.getElementById('ms-age-35-49').innerText = formatPct(agg.age_35_49, agg.total_pop);
            document.getElementById('ms-age-50-64').innerText = formatPct(agg.age_50_64, agg.total_pop);
            document.getElementById('ms-age-65-plus').innerText = formatPct(agg.age_65_plus, agg.total_pop);
            
            document.getElementById('ch-age-0-17').innerText = formatPct(c_agg.age_0_17, c_agg.pop);
            document.getElementById('ch-age-18-34').innerText = formatPct(c_agg.age_18_34, c_agg.pop);
            document.getElementById('ch-age-35-49').innerText = formatPct(c_agg.age_35_49, c_agg.pop);
            document.getElementById('ch-age-50-64').innerText = formatPct(c_agg.age_50_64, c_agg.pop);
            document.getElementById('ch-age-65-plus').innerText = formatPct(c_agg.age_65_plus, c_agg.pop);

            document.getElementById('ms-poverty').innerText = formatPct(agg.in_poverty, agg.total_pov);
            document.getElementById('ms-singleparent').innerText = formatPct(agg.single_parent_kids, agg.total_families);
            document.getElementById('ms-married').innerText = formatPct(agg.married, agg.total_marital);
            document.getElementById('ms-divorced').innerText = formatPct(agg.divorced_separated, agg.total_marital);
            document.getElementById('ms-white').innerText = formatPct(agg.white, agg.total_pop);
            document.getElementById('ms-hispanic').innerText = formatPct(agg.hispanic, agg.total_pop);
            document.getElementById('ms-lep').innerText = formatPct(agg.lep, agg.total_lang);
            document.getElementById('ms-renters').innerText = formatPct(agg.renters, agg.total_housing);
        }}

        slider.addEventListener('input', updateMap);
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
