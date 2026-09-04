import re

with open("generate_tract_map.py", "r") as f:
    code = f.read()

new_script = """
        const map = L.map('map').setView([41.637, -93.686], 11);
        
        L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}', {{
            attribution: 'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ',
            subdomains: 'abcd',
            maxZoom: 20
        }}).addTo(map);
        
        const geojsonData = {geojson_str};
        const censusStats = {census_stats_json};
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
                total_housing: 0, renters: 0
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
                }}
            }});
            
            tractCountLabel.innerText = tractsIncluded;
            peopleCountLabel.innerText = maxPopIncluded;
            
            document.getElementById('ms-pop').innerText = agg.total_pop.toLocaleString();
            document.getElementById('ms-kids').innerText = formatPct(agg.kids, agg.total_pop);
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
"""

code = re.sub(r"<script>\s*const map = L\.map.*updateMap\(\);\s*</script>", "<script>\n" + new_script + "\n    </script>", code, flags=re.DOTALL)
# Also fix '{z}/{y}/{x}' to '{{z}}/{{y}}/{{x}}' inside the new script
code = code.replace("tile/{z}/{y}/{x}", "tile/{{z}}/{{y}}/{{x}}")

with open("generate_tract_map.py", "w") as f:
    f.write(code)
