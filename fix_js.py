import re
with open("generate_tract_map.py", "r") as f:
    code = f.read()

# Fix the CARTO tile layers again just to be sure (handling {{ }})
code = code.replace(
    "https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png",
    "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{{z}}/{{y}}/{{x}}"
)
code = code.replace(
    "&copy; OpenStreetMap &copy; CARTO",
    "Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ"
)

# New JS logic
new_js = """
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
        
        function updateMap() {{
            const threshold = parseInt(slider.value);
            
            // Build base selection from slider
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
"""

code = re.sub(r"function getStyle\(feature, threshold\) \{.*\}", "", code, flags=re.DOTALL)
code = re.sub(r"function formatPct\(val, total\) \{\{.*?\}\}", new_js, code, flags=re.DOTALL)
# Remove the old updateMap completely
code = re.sub(r"function updateMap\(\) \{\{.*slider\.addEventListener\('input', updateMap\);", "slider.addEventListener('input', updateMap);", code, flags=re.DOTALL)

# Re-define the geojsonLayer correctly so it handles clicks
init_layer = """
        // Define geojsonLayer once
        geojsonLayer = L.geoJson(geojsonData, {{
            style: function(feature) {{
                return getStyle(feature);
            }},
            onEachFeature: function(feature, layer) {{
                layer.on({{ 
                    mouseover: highlightFeature, 
                    mouseout: resetHighlight,
                    click: toggleTract 
                }});
            }},
            filter: function(feature) {{
                return feature.properties.church_pop > 0 || feature.properties.GEOID === churchTractId;
            }}
        }}).addTo(map);
        
        slider.addEventListener('input', updateMap);
"""
code = code.replace("slider.addEventListener('input', updateMap);", init_layer)

# Also fix resetHighlight to use getStyle() without threshold
code = code.replace("""function resetHighlight(e) {{
            geojsonLayer.resetStyle(e.target);
            info.update();
        }}""", """function resetHighlight(e) {{
            e.target.setStyle(getStyle(e.target.feature));
            info.update();
        }}""")

with open("generate_tract_map.py", "w") as f:
    f.write(code)
print("done")
