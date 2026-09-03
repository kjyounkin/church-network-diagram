import psycopg2
import json
import time
import requests
import os

DB_HOST = "postgres"
DB_PORT = "5432"
DB_USER = "meltano"
DB_PASS = "WEFC"
DB_NAME = "warehouse"

CHURCH_LAT = 41.6371503
CHURCH_LON = -93.6860107

STAFF_NAMES = {
    "Chuck Mullikin", "Haitao Cheng", "Michelle Van Wyngarden", "Kaurie Long",
    "Alysa Younkin", "Randyl Lynn Dicks", "Julius Williams"
}
ELDER_NAMES = {
    "Todd Troll", "Chris Mielke", "Scott Van Wyngarden", "Wayne Smith",
    "John Neal", "Thomas Avila", "Steve Getz"
}

def get_db_data():
    conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS, dbname=DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            p.person_id, p.full_name, p.primary_campus, p.membership, p.status, p.generation,
            a.attributes_street_line_1, a.attributes_city, a.attributes_state, a.attributes_zip
        FROM raw.v_people p
        JOIN raw.pco_addresses a ON p.person_id = a.relationships_person_data_id::INTEGER
        WHERE a.attributes_street_line_1 IS NOT NULL
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    people = []
    for row in rows:
        state = (row[8] or "").strip().upper()
        if state not in ('IA', 'IOWA'):
            continue

        membership = row[3] or ""
        if membership == 'Giver Only': continue
        
        name = row[1] or "Unknown"
        role = 'Regular'
        if name in STAFF_NAMES: role = 'Staff'
        elif name in ELDER_NAMES: role = 'Elder'
        elif membership == 'Member': role = 'Member'

        addr_str = f"{row[6]}, {row[7] or ''}, {row[8] or ''} {row[9] or ''}".strip(', ')
        
        people.append({
            "id": row[0],
            "name": name,
            "campus": row[2] or "Unknown Campus",
            "role": role,
            "generation": row[5] or "Unknown",
            "status": row[4] or "inactive",
            "address": addr_str,
            "street": row[6]
        })
    return people

def geocode_and_route(people):
    cache_file = 'geo_cache.json'
    cache = {}
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            cache = json.load(f)

    unique_addresses = list(set(p['address'] for p in people))
    
    for addr in unique_addresses:
        if addr not in cache:
            # We already ran the big batch, so any new ones are quick
            print(f"Geocoding: {addr}")
            try:
                res = requests.get('https://nominatim.openstreetmap.org/search', 
                                   params={'q': addr, 'format': 'json', 'limit': 1},
                                   headers={'User-Agent': 'ChurchNetworkMap/1.0 (local script)'})
                data = res.json()
                if data:
                    lat, lon = float(data[0]['lat']), float(data[0]['lon'])
                    
                    route_res = requests.get(f"http://router.project-osrm.org/route/v1/driving/{CHURCH_LON},{CHURCH_LAT};{lon},{lat}?overview=false")
                    route_data = route_res.json()
                    
                    drive_time_mins = 0
                    drive_dist_miles = 0
                    if route_data.get('code') == 'Ok':
                        drive_time_mins = round(route_data['routes'][0]['duration'] / 60, 1)
                        drive_dist_miles = round(route_data['routes'][0]['distance'] / 1609.34, 1)
                    
                    cache[addr] = {
                        "lat": lat, "lon": lon,
                        "drive_time": drive_time_mins,
                        "drive_dist": drive_dist_miles
                    }
                else:
                    cache[addr] = None
            except Exception as e:
                cache[addr] = None
            with open(cache_file, 'w') as f:
                json.dump(cache, f)
            time.sleep(1.5)

    for p in people:
        geo = cache.get(p['address'])
        if geo:
            p['lat'] = geo['lat']
            p['lon'] = geo['lon']
            p['drive_time'] = geo['drive_time']
            p['drive_dist'] = geo['drive_dist']
        else:
            p['lat'] = None
            p['lon'] = None

    return [p for p in people if p.get('lat') is not None and p.get('drive_dist', 0) <= 50]

def generate_leaflet_map(people):
    import os
    isochrone_json = '{"type": "FeatureCollection", "features": []}'
    if os.path.exists('church_isochrones.json'):
        with open('church_isochrones.json', 'r') as f:
            isochrone_json = f.read()

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Church Geographic Map & Contours</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>
    <!-- Turf.js for contour generation -->
    <script src="https://cdn.jsdelivr.net/npm/@turf/turf@6/turf.min.js"></script>
    
    <style>
        body {{ padding: 0; margin: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0d1117; }}
        #map {{ width: 100vw; height: 100vh; }}
        
        .panel {{ 
            position: absolute; 
            background: rgba(22, 27, 34, 0.95); 
            padding: 15px; 
            border-radius: 8px; 
            box-shadow: 0 4px 6px rgba(0,0,0,0.5); 
            border: 1px solid #30363d; 
            z-index: 1000; 
            color: #c9d1d9;
            max-height: 85vh; 
            overflow-y: auto;
        }}
        .controls {{ top: 20px; left: 20px; width: 300px; }}
        .stats-panel {{ bottom: 30px; left: 20px; width: 300px; }}
        
        h3, h4 {{ margin-top: 0; margin-bottom: 10px; color: #58a6ff; font-weight: 600; }}
        .filter-section {{ margin-bottom: 15px; }}
        .filter-title {{ font-weight: bold; font-size: 12px; text-transform: uppercase; margin-bottom: 5px; color: #8b949e; border-bottom: 1px solid #30363d; padding-bottom: 4px;}}
        label {{ display: flex; align-items: center; margin-bottom: 6px; cursor: pointer; font-size: 13px; }}
        input[type="checkbox"] {{ margin-right: 8px; cursor: pointer; accent-color: #58a6ff; }}
        
        .hh-label {{ background: rgba(13, 17, 23, 0.8); border: 1px solid #30363d; color: #c9d1d9; font-weight: bold; font-size: 11px; padding: 2px 5px; box-shadow: none; white-space: nowrap;}}
        .leaflet-tooltip-bottom:before {{ border-bottom-color: #30363d; }}
        
        .color-key {{ display: inline-block; width: 12px; height: 12px; border-radius: 50%; margin-right: 6px; }}
    </style>
</head>
<body>
    <div id="map"></div>
    
    <div class="panel controls">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
            <h3 style="margin:0;">Map Filters</h3>
            <div>
                <a href="index.html" style="color:#58a6ff; font-size:12px; text-decoration:none; border:1px solid #58a6ff; padding:3px 8px; border-radius:4px; margin-right:4px;">&larr; Network</a>
                <a href="age_histogram.html" style="color:#58a6ff; font-size:12px; text-decoration:none; border:1px solid #58a6ff; padding:3px 8px; border-radius:4px; margin-right:8px;">Demographics &rarr;</a>
                <a href="contiguous_tracts.html" style="color:#58a6ff; font-size:12px; text-decoration:none; border:1px solid #58a6ff; padding:3px 8px; border-radius:4px; margin-right:8px;">Core Tracts &rarr;</a>
                <button onclick="togglePanel('controls-content', this)" style="background:none; border:none; color:#58a6ff; font-size:18px; cursor:pointer; padding:0; line-height:1;">&minus;</button>
            </div>
        </div>
        <div id="controls-content">
            <div class="filter-section">
                <div class="filter-title">Display Options</div>
                <label><input type="checkbox" id="show-labels" checked> Show Household Labels</label>
                <label><input type="checkbox" id="show-contours" checked> Show Drive Time Contours</label>
            </div>
            
            <div class="filter-section">
                <div class="filter-title">K-Means Grouping</div>
                <div style="display:flex; gap:10px; margin-bottom:10px;">
                    <input type="number" id="k-clusters" value="5" min="1" max="50" style="width: 50px; background:#0d1117; color:#c9d1d9; border:1px solid #30363d; border-radius:4px; padding:2px 5px;">
                    <button onclick="calculateKMeans()" style="background:#238636; color:white; border:none; padding:4px 10px; border-radius:4px; cursor:pointer; font-weight:bold;">Cluster</button>
                    <button onclick="clearKMeans()" style="background:#da3633; color:white; border:none; padding:4px 10px; border-radius:4px; cursor:pointer; font-weight:bold;">Clear</button>
                </div>
            </div>

            <div id="filter-container"></div>
        </div>
    </div>
    
    <div class="panel stats-panel">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
            <h4 style="margin:0;">Drive Time Distribution</h4>
            <button onclick="togglePanel('stats-content-wrapper', this)" style="background:none; border:none; color:#58a6ff; font-size:18px; cursor:pointer; padding:0; line-height:1;">&minus;</button>
        </div>
        <div id="stats-content-wrapper">
            <div id="stats-content" style="font-size:13px; line-height: 1.6;"></div>
        </div>
    </div>

    <script>
        function togglePanel(id, btn) {{
            const el = document.getElementById(id);
            if (el.style.display === 'none') {{
                el.style.display = 'block';
                btn.innerHTML = '&minus;';
            }} else {{
                el.style.display = 'none';
                btn.innerHTML = '&#43;';
            }}
        }}
        
        const rawPeople = {json.dumps(people)};
        let filteredPeople = rawPeople;
        const churchIsochrones = {isochrone_json};
        
        // Define map and base layer
        const map = L.map('map').setView([{CHURCH_LAT}, {CHURCH_LON}], 11);
        L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '&copy; OpenStreetMap contributors',
            maxZoom: 19
        }}).addTo(map);

        // Layers
        let markersCluster = L.markerClusterGroup({{ maxClusterRadius: 40 }});
        let contourLayer = L.layerGroup();
        let kmeansLayer = L.layerGroup();
        
        map.addLayer(markersCluster);
        map.addLayer(contourLayer);
        map.addLayer(kmeansLayer);
        
        let activeKMeans = null;

        // Drive Time Buckets
        function getBucket(time) {{
            if (time <= 5) return '0-5 mins';
            if (time <= 10) return '5-10 mins';
            if (time <= 15) return '10-15 mins';
            if (time <= 20) return '15-20 mins';
            return '20+ mins';
        }}
        const buckets = ['0-5 mins', '5-10 mins', '10-15 mins', '15-20 mins', '20+ mins'];
        const bucketColors = {{
            '0-5 mins': '#3fb950',
            '5-10 mins': '#2f81f7',
            '10-15 mins': '#a371f7',
            '15-20 mins': '#d29922',
            '20+ mins': '#f85149'
        }};

        // Build Filters
        const uniqueRoles = ['Elder', 'Staff', 'Member', 'Regular'];
        const uniqueCampuses = [...new Set(rawPeople.map(p => p.campus))].sort();
        const uniqueGens = [...new Set(rawPeople.map(p => p.generation))].sort();
        const uniqueStatuses = [...new Set(rawPeople.map(p => p.status))].sort();

        const filterContainer = document.getElementById('filter-container');
        
        function createCheckboxes(title, items, className, defaultCheckedFn = (item) => true) {{
            const div = document.createElement('div');
            div.className = 'filter-section';
            div.innerHTML = `<div class="filter-title">${{title}}</div>`;
            items.forEach(item => {{
                if(!item) return;
                const isChecked = defaultCheckedFn(item) ? 'checked' : '';
                const label = document.createElement('label');
                label.innerHTML = `<input type="checkbox" class="${{className}}" value="${{item}}" ${{isChecked}}> ${{item}}`;
                div.appendChild(label);
            }});
            filterContainer.appendChild(div);
        }}
        
        createCheckboxes('Drive Time', buckets, 'filter-time');
        createCheckboxes('Status', uniqueStatuses, 'filter-status', s => s === 'active');
        createCheckboxes('Role', uniqueRoles, 'filter-role');
        createCheckboxes('Campus', uniqueCampuses, 'filter-campus');
        createCheckboxes('Generation', uniqueGens, 'filter-gen');

        // Add event listeners
        document.querySelectorAll('input[type="checkbox"]').forEach(cb => {{
            cb.addEventListener('change', updateMap);
        }});

        function getColor(role) {{
            if (role === 'Elder') return '#ffd700';
            if (role === 'Staff') return '#a371f7';
            if (role === 'Member') return '#3fb950';
            return '#8b949e';
        }}
        
        function calculateKMeans() {{
            const k = parseInt(document.getElementById('k-clusters').value);
            if (!k || k < 1) return;
            
            const validPeople = filteredPeople.filter(p => p.lat && p.lon);
            if (validPeople.length === 0) return;
            
            // 1. Extract unique coordinates to prevent Turf.js K-Means bugs with duplicates
            const uniqueCoordsMap = new Map();
            validPeople.forEach(p => {{
                uniqueCoordsMap.set(p.lat + ',' + p.lon, [p.lon, p.lat]);
            }});
            
            const actualK = Math.min(k, uniqueCoordsMap.size);
            
            const uniqueFeatures = Array.from(uniqueCoordsMap.entries()).map(([key, coords]) => {{
                return turf.point(coords, {{coordKey: key}});
            }});
            const uniquePoints = turf.featureCollection(uniqueFeatures);
            
            try {{
                // 2. Run K-Means on purely unique locations
                const clusteredUnique = turf.clustersKmeans(uniquePoints, {{numberOfClusters: actualK}});
                
                // 3. Map cluster IDs back to all valid people
                const clusterLookup = {{}};
                turf.featureEach(clusteredUnique, function(f) {{
                    clusterLookup[f.properties.coordKey] = f.properties.cluster;
                }});
                
                const allFeatures = validPeople.map(p => {{
                    const key = p.lat + ',' + p.lon;
                    return turf.point([p.lon, p.lat], {{ person: p, cluster: clusterLookup[key] }});
                }});
                
                activeKMeans = turf.featureCollection(allFeatures);
                
                document.getElementById('show-contours').checked = false;
                updateMap();
            }} catch (e) {{
                console.error(e);
            }}
        }}
        
        function clearKMeans() {{
            activeKMeans = null;
            updateMap();
        }}

        function updateMap() {{
            const showLabels = document.getElementById('show-labels').checked;
            const showContours = document.getElementById('show-contours').checked;
            
            const activeTimes = new Set(Array.from(document.querySelectorAll('.filter-time:checked')).map(cb => cb.value));
            const activeRoles = new Set(Array.from(document.querySelectorAll('.filter-role:checked')).map(cb => cb.value));
            const activeCampuses = new Set(Array.from(document.querySelectorAll('.filter-campus:checked')).map(cb => cb.value));
            const activeGens = new Set(Array.from(document.querySelectorAll('.filter-gen:checked')).map(cb => cb.value));
            const activeStatuses = new Set(Array.from(document.querySelectorAll('.filter-status:checked')).map(cb => cb.value));

            filteredPeople = rawPeople.filter(p => {{
                return activeTimes.has(getBucket(p.drive_time)) &&
                       activeRoles.has(p.role) &&
                       activeCampuses.has(p.campus) &&
                       activeGens.has(p.generation) &&
                       activeStatuses.has(p.status);
            }});

            // 1. Update Markers
            markersCluster.clearLayers();
            filteredPeople.forEach(p => {{
                const markerHtml = `<div style="
                    background-color: ${{getColor(p.role)}}; 
                    width: 14px; height: 14px; border-radius: 50%; 
                    border: 2px solid #fff; box-shadow: 0 0 4px #000;
                "></div>`;
                
                const customIcon = L.divIcon({{
                    html: markerHtml, className: '', iconSize: [18, 18], iconAnchor: [9, 9]
                }});
                
                let zIndex = 0;
                if (p.role === 'Staff') zIndex = 1000;
                else if (p.role === 'Elder') zIndex = 500;
                else if (p.role === 'Member') zIndex = 100;
                
                const marker = L.marker([p.lat, p.lon], {{icon: customIcon, zIndexOffset: zIndex}});
                
                marker.bindPopup(`
                    <div style="color:black;">
                        <b>${{p.name}}</b><br/>
                        ${{p.role}} &middot; ${{p.campus}}<br/>
                        ${{p.generation}}<br/>
                        Drive: <b>${{p.drive_time}} mins</b> (${{p.drive_dist}} mi)
                    </div>
                `);

                if (showLabels) {{
                    marker.bindTooltip(p.name, {{ permanent: true, direction: 'bottom', className: 'hh-label', offset: [0, 5] }});
                }}
                
                markersCluster.addLayer(marker);
            }});

            // 2. Update Stats Panel
            let statsHtml = '';
            let total = filteredPeople.length;
            buckets.forEach(b => {{
                const count = filteredPeople.filter(p => getBucket(p.drive_time) === b).length;
                statsHtml += `<div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                    <span><span class="color-key" style="background:${{bucketColors[b]}};"></span> ${{b}}</span>
                    <strong>${{count}}</strong>
                </div>`;
            }});
            statsHtml += `<div style="border-top:1px solid #30363d; margin-top:8px; padding-top:8px; display:flex; justify-content:space-between;">
                <span>Total People</span><strong>${{total}}</strong>
            </div>`;
            document.getElementById('stats-content').innerHTML = statsHtml;

            // 3. Draw Drive Time Contours (Isochrones)
            contourLayer.clearLayers();
            if (showContours && churchIsochrones && churchIsochrones.features) {{
                const sortedFeatures = churchIsochrones.features.slice().sort((a,b) => b.properties.time - a.properties.time);
                
                L.geoJSON(sortedFeatures, {{
                    filter: function(feature) {{
                        const b = getBucket(feature.properties.time);
                        return activeTimes.has(b);
                    }},
                    style: function(feature) {{
                        return {{
                            color: feature.properties.color || '#FF0000',
                            weight: 3.5,
                            fillOpacity: 0.05
                        }};
                    }},
                    onEachFeature: function(feature, layer) {{
                        layer.bindTooltip(feature.properties.time + ' mins', {{
                            sticky: true,
                            className: 'hh-label'
                        }});
                    }}
                }}).addTo(contourLayer);
            }}
            
            // 4. Draw K-Means Clusters
            kmeansLayer.clearLayers();
            if (activeKMeans) {{
                const clusterGroups = {{}};
                turf.featureEach(activeKMeans, function (currentFeature) {{
                    const clusterId = currentFeature.properties.cluster;
                    if (clusterId === undefined || clusterId === null) return;
                    if (!clusterGroups[clusterId]) clusterGroups[clusterId] = [];
                    clusterGroups[clusterId].push(currentFeature);
                }});
                
                const palette = ['#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#911eb4', '#46f0f0', '#f032e6', '#bcf60c', '#fabebe', '#008080', '#e6beff', '#9a6324', '#fffac8', '#800000', '#aaffc3', '#808000', '#ffd8b1', '#000075', '#808080'];
                
                for (const [cId, feats] of Object.entries(clusterGroups)) {{
                    const color = palette[parseInt(cId) % palette.length];
                    
                    // Extract purely unique physical locations for geometry generation
                    const uniqueLocMap = new Map();
                    feats.forEach(f => {{
                        const coords = f.geometry.coordinates;
                        uniqueLocMap.set(coords[0] + ',' + coords[1], coords);
                    }});
                    const uniqueLocs = Array.from(uniqueLocMap.values());
                    
                    try {{
                        let shape;
                        if (uniqueLocs.length === 1) {{
                            shape = turf.buffer(turf.point(uniqueLocs[0]), 0.5, {{units: 'miles'}});
                        }} else if (uniqueLocs.length === 2) {{
                            const line = turf.lineString(uniqueLocs);
                            shape = turf.buffer(line, 0.5, {{units: 'miles'}});
                        }} else {{
                            const fc = turf.featureCollection(uniqueLocs.map(c => turf.point(c)));
                            const hull = turf.convex(fc);
                            if (hull) {{
                                shape = turf.buffer(hull, 0.5, {{units: 'miles'}});
                            }} else {{
                                // Fallback for collinear points
                                const line = turf.lineString(uniqueLocs);
                                shape = turf.buffer(line, 0.5, {{units: 'miles'}});
                            }}
                        }}
                        
                        if (shape) {{
                            L.geoJSON(shape, {{
                                style: {{ color: color, weight: 3, opacity: 0.9, fillColor: color, fillOpacity: 0.2 }}
                            }}).addTo(kmeansLayer);
                        }}
                    }} catch (e) {{
                        console.error("Error drawing cluster " + cId, e);
                    }}
                }}
            }}
        }}

        // Add Church
        L.marker([{CHURCH_LAT}, {CHURCH_LON}]).addTo(map).bindTooltip("Westchester EFC", {{permanent: true, direction: "top", className: "hh-label"}});

        // Initial render
        updateMap();

    </script>
</body>
</html>
"""
    with open('geo_map.html', 'w') as f:
        f.write(html)
    print("Created advanced geo_map.html!")

if __name__ == "__main__":
    raw_people = get_db_data()
    geocoded_people = geocode_and_route(raw_people)
    generate_leaflet_map(geocoded_people)
