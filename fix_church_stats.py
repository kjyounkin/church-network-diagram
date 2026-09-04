import json

with open("generate_tract_map.py", "r") as f:
    code = f.read()

# 1. Update the SQL query to include age and status, and only select those with age
sql_old = """    cur.execute(\"\"\"
        SELECT a.attributes_street_line_1, a.attributes_city, a.attributes_state, a.attributes_zip
        FROM raw.v_people p
        JOIN raw.pco_addresses a ON p.person_id = a.relationships_person_data_id::INTEGER
        WHERE a.attributes_street_line_1 IS NOT NULL
          AND p.membership IN ('Member', 'Regular Attender')
          AND p.status = 'active'
          AND p.primary_campus = 'Westchester EFC'
    \"\"\")
    rows = cur.fetchall()"""

sql_new = """    cur.execute(\"\"\"
        SELECT a.attributes_street_line_1, a.attributes_city, a.attributes_state, a.attributes_zip, p.age
        FROM raw.v_people p
        JOIN raw.pco_addresses a ON p.person_id = a.relationships_person_data_id::INTEGER
        WHERE a.attributes_street_line_1 IS NOT NULL
          AND p.membership IN ('Member', 'Regular Attender')
          AND p.status = 'active'
          AND p.primary_campus = 'Westchester EFC'
    \"\"\")
    rows = cur.fetchall()"""
code = code.replace(sql_old, sql_new)

# 2. Extract ages and associate with coordinates
coord_old = """    coords = []
    for row in rows:
        street, city, state, zip_code = row
        street = (street or "").replace("\\n", " ").strip()
        city = (city or "").strip()
        state = (state or "").strip()
        zip_code = (zip_code or "").strip()
        addr_str = f"{street}, {city}, {state} {zip_code}"
        
        geo = geo_cache.get(addr_str)
        if geo and geo.get('lat') is not None:
            coords.append(Point(geo['lon'], geo['lat']))

    gdf_people = gpd.GeoDataFrame(geometry=coords, crs="EPSG:4326")"""

coord_new = """    coords = []
    ages = []
    for row in rows:
        street, city, state, zip_code, age = row
        street = (street or "").replace("\\n", " ").strip()
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

    gdf_people = gpd.GeoDataFrame({'age_bucket': ages}, geometry=coords, crs="EPSG:4326")"""
code = code.replace(coord_old, coord_new)

# 3. Aggregate church demographics per tract
join_old = """    print("Spatial joining...")
    joined = gpd.sjoin(gdf_people, gdf_tracts, how="inner", predicate="intersects")
    tract_counts = joined['GEOID'].value_counts().to_dict()
    total_people = sum(tract_counts.values())

    gdf_tracts['church_pop'] = gdf_tracts['GEOID'].map(tract_counts).fillna(0)"""

join_new = """    print("Spatial joining...")
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

    gdf_tracts['church_pop'] = gdf_tracts['GEOID'].map(tract_counts).fillna(0)"""
code = code.replace(join_old, join_new)


# 4. Update Census Data parsing for Age Buckets
stats_old = """        stats = {}
        stats['total_pop'] = get_est(tract_data, 'B01001', 1)
        stats['kids'] = sum(get_est(tract_data, 'B01001', i) for i in [3,4,5,6, 27,28,29,30])
        stats['total_families'] = get_est(tract_data, 'B11003', 1)"""

stats_new = """        stats = {}
        stats['total_pop'] = get_est(tract_data, 'B01001', 1)
        stats['kids'] = sum(get_est(tract_data, 'B01001', i) for i in [3,4,5,6, 27,28,29,30])
        stats['age_0_17'] = stats['kids']
        stats['age_18_34'] = sum(get_est(tract_data, 'B01001', i) for i in [7,8,9,10,11,12, 31,32,33,34,35,36])
        stats['age_35_49'] = sum(get_est(tract_data, 'B01001', i) for i in [13,14,15, 37,38,39])
        stats['age_50_64'] = sum(get_est(tract_data, 'B01001', i) for i in [16,17,18,19, 40,41,42,43])
        stats['age_65_plus'] = sum(get_est(tract_data, 'B01001', i) for i in [20,21,22,23,24,25, 44,45,46,47,48,49])
        stats['total_families'] = get_est(tract_data, 'B11003', 1)"""
code = code.replace(stats_old, stats_new)

# 5. Inject churchStats into JS
inject_old = """    geojson_str = active_tracts[['GEOID', 'church_pop', 'cumulative_pct', 'cumulative_pop', 'geometry']].to_json()
    census_stats_json = json.dumps(census_stats)

    html = f\"\"\"<!DOCTYPE html>"""

inject_new = """    geojson_str = active_tracts[['GEOID', 'church_pop', 'cumulative_pct', 'cumulative_pop', 'geometry']].to_json()
    census_stats_json = json.dumps(census_stats)
    church_stats_json = json.dumps(church_stats)

    html = f\"\"\"<!DOCTYPE html>"""
code = code.replace(inject_old, inject_new)

# 6. HTML layout for comparison
ui_old = """        <div class="stat-row"><span class="stat-label">Total Population</span><span class="stat-val" id="ms-pop">0</span></div>
        <div class="stat-row"><span class="stat-label">Children (0-17)</span><span class="stat-val" id="ms-kids">0%</span></div>
        <div class="stat-row"><span class="stat-label">Poverty Rate</span><span class="stat-val" id="ms-poverty">0%</span></div>
        <div class="stat-row"><span class="stat-label">Single-Parent Families</span><span class="stat-val" id="ms-singleparent">0%</span></div>
        <div class="stat-row"><span class="stat-label">Married Adults</span><span class="stat-val" id="ms-married">0%</span></div>
        <div class="stat-row"><span class="stat-label">Divorced/Separated</span><span class="stat-val" id="ms-divorced">0%</span></div>
        <div class="stat-row"><span class="stat-label">White Pop.</span><span class="stat-val" id="ms-white">0%</span></div>
        <div class="stat-row"><span class="stat-label">Hispanic Pop.</span><span class="stat-val" id="ms-hispanic">0%</span></div>
        <div class="stat-row"><span class="stat-label">Limited English</span><span class="stat-val" id="ms-lep">0%</span></div>
        <div class="stat-row"><span class="stat-label">Renters</span><span class="stat-val" id="ms-renters">0%</span></div>"""

ui_new = """        <div class="stat-row"><span class="stat-label">Total Population</span><span class="stat-val" id="ms-pop">0</span></div>
        <h4 style="margin: 15px 0 5px 0; font-size: 13px; color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 5px;">Age Profile <span style="font-size: 10px; color:#888; float:right;">(Tracts vs Church)</span></h4>
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
        <div class="stat-row"><span class="stat-label">Renters</span><span class="stat-val" id="ms-renters">0%</span></div>"""
code = code.replace(ui_old, ui_new)

js_vars_old = """        const geojsonData = {geojson_str};
        const censusStats = {census_stats_json};
        const churchTractId = "{church_tract_id}";"""

js_vars_new = """        const geojsonData = {geojson_str};
        const censusStats = {census_stats_json};
        const churchStats = {church_stats_json};
        const churchTractId = "{church_tract_id}";"""
code = code.replace(js_vars_old, js_vars_new)

# JS Aggregation updates
agg_old = """            let agg = {
                total_pop: 0, kids: 0, total_families: 0, single_parent_kids: 0,
                total_marital: 0, married: 0, divorced_separated: 0, white: 0,
                hispanic: 0, total_lang: 0, lep: 0, total_pov: 0, in_poverty: 0,
                total_housing: 0, renters: 0
            };"""

agg_new = """            let agg = {
                total_pop: 0, kids: 0, total_families: 0, single_parent_kids: 0,
                total_marital: 0, married: 0, divorced_separated: 0, white: 0,
                hispanic: 0, total_lang: 0, lep: 0, total_pov: 0, in_poverty: 0,
                total_housing: 0, renters: 0,
                age_0_17: 0, age_18_34: 0, age_35_49: 0, age_50_64: 0, age_65_plus: 0
            };
            let c_agg = {
                pop: 0, age_0_17: 0, age_18_34: 0, age_35_49: 0, age_50_64: 0, age_65_plus: 0
            };"""
code = code.replace(agg_old, agg_new)

loop_old = """                    let tractStats = censusStats[f.properties.GEOID];
                    if (tractStats) {
                        for (let key in agg) {
                            agg[key] += (tractStats[key] || 0);
                        }
                    }
                }
            });"""

loop_new = """                    let tractStats = censusStats[f.properties.GEOID];
                    if (tractStats) {
                        for (let key in agg) {
                            agg[key] += (tractStats[key] || 0);
                        }
                    }
                    let cStats = churchStats[f.properties.GEOID];
                    if (cStats) {
                        for (let key in c_agg) {
                            c_agg[key] += (cStats[key] || 0);
                        }
                    }
                }
            });"""
code = code.replace(loop_old, loop_new)

# JS UI update replacements
update_old = """            document.getElementById('ms-pop').innerText = agg.total_pop.toLocaleString();
            document.getElementById('ms-kids').innerText = formatPct(agg.kids, agg.total_pop);
            document.getElementById('ms-poverty').innerText = formatPct(agg.in_poverty, agg.total_pov);
            document.getElementById('ms-singleparent').innerText = formatPct(agg.single_parent_kids, agg.total_families);
            document.getElementById('ms-married').innerText = formatPct(agg.married, agg.total_marital);
            document.getElementById('ms-divorced').innerText = formatPct(agg.divorced_separated, agg.total_marital);
            document.getElementById('ms-white').innerText = formatPct(agg.white, agg.total_pop);
            document.getElementById('ms-hispanic').innerText = formatPct(agg.hispanic, agg.total_pop);
            document.getElementById('ms-lep').innerText = formatPct(agg.lep, agg.total_lang);
            document.getElementById('ms-renters').innerText = formatPct(agg.renters, agg.total_housing);
        }"""

update_new = """            document.getElementById('ms-pop').innerText = agg.total_pop.toLocaleString();
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
        }"""
code = code.replace(update_old, update_new)

with open("generate_tract_map.py", "w") as f:
    f.write(code)
print("Fixes applied successfully")
