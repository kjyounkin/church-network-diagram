import os

# 1. Fix CARTO error in generate_geo_map.py
with open("generate_geo_map.py", "r") as f:
    geo_map_code = f.read()

geo_map_code = geo_map_code.replace(
    "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}"
)
geo_map_code = geo_map_code.replace(
    "&copy; <a href=\"https://www.openstreetmap.org/copyright\">OpenStreetMap</a> contributors &copy; <a href=\"https://carto.com/attributions\">CARTO</a>",
    "Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ"
)

with open("generate_geo_map.py", "w") as f:
    f.write(geo_map_code)


# 2. Fix generate_tract_map.py
with open("generate_tract_map.py", "r") as f:
    tract_map_code = f.read()

tract_map_code = tract_map_code.replace(
    "https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png",
    "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}"
)
tract_map_code = tract_map_code.replace(
    "&copy; OpenStreetMap &copy; CARTO",
    "Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ"
)

# Inject dynamic filtering logic by replacing the JS
js_old = """        function formatPct(val, total) {
            if (total === 0 || !total) return "0%";
            return (val / total * 100).toFixed(1) + "%";
        }

        function updateMap() {"""

js_new = """        function formatPct(val, total) {
            if (total === 0 || !total) return "0%";
            return (val / total * 100).toFixed(1) + "%";
        }
        
        let selectedTractIds = new Set();
        let userOverrodeSlider = false;

        function toggleTract(e) {
            const geoid = e.target.feature.properties.GEOID;
            if (selectedTractIds.has(geoid)) {
                selectedTractIds.delete(geoid);
            } else {
                selectedTractIds.add(geoid);
            }
            userOverrodeSlider = true;
            renderState();
        }

        function updateMap() {"""
tract_map_code = tract_map_code.replace(js_old, js_new)


js_old2 = """            if (geojsonLayer) {
                map.removeLayer(geojsonLayer);
            }
            
            geojsonLayer = L.geoJson(geojsonData, {
                style: function(feature) {
                    return getStyle(feature, threshold);
                },
                onEachFeature: onEachFeature,
                filter: function(feature) {
                    return feature.properties.church_pop > 0 || feature.properties.GEOID === churchTractId;
                }
            }).addTo(map);"""

js_new2 = """            // Calculate base selection from slider
            selectedTractIds.clear();
            geojsonData.features.forEach(f => {
                if (f.properties.cumulative_pct <= threshold) {
                    selectedTractIds.add(f.properties.GEOID);
                }
            });
            userOverrodeSlider = false;
            
            renderState();
        }
        
        // Define geojsonLayer once
        geojsonLayer = L.geoJson(geojsonData, {
            style: function(feature) {
                return getStyle(feature, parseInt(slider.value));
            },
            onEachFeature: function(feature, layer) {
                layer.on({ 
                    mouseover: highlightFeature, 
                    mouseout: resetHighlight,
                    click: toggleTract 
                });
            },
            filter: function(feature) {
                return feature.properties.church_pop > 0 || feature.properties.GEOID === churchTractId;
            }
        }).addTo(map);

        function renderState() {"""
tract_map_code = tract_map_code.replace(js_old2, js_new2)

# Fix getStyle to use selectedTractIds
style_old = """        function getStyle(feature, threshold) {
            const props = feature.properties;
            if (props.GEOID === churchTractId) {
                return props.cumulative_pct <= threshold ? 
                    { fillColor: '#ffeb3b', color: '#ffffff', weight: 2, fillOpacity: 0.8 } :
                    { fillColor: '#ffeb3b', color: '#888888', weight: 1, fillOpacity: 0.2 };
            }
            
            if (props.cumulative_pct <= threshold) {
                return { fillColor: '#9c27b0', color: '#ffffff', weight: 1.5, fillOpacity: 0.6 };
            } else if (props.church_pop > 0) {
                return { fillColor: '#2196f3', color: '#2196f3', weight: 1, fillOpacity: 0.15 };
            } else {
                return { fillOpacity: 0, weight: 0 };
            }
        }"""
        
style_new = """        function getStyle(feature) {
            const props = feature.properties;
            const isSelected = selectedTractIds.has(props.GEOID);
            
            if (props.GEOID === churchTractId) {
                return isSelected ? 
                    { fillColor: '#ffeb3b', color: '#ffffff', weight: 3, fillOpacity: 0.8 } :
                    { fillColor: '#ffeb3b', color: '#888888', weight: 1, fillOpacity: 0.2 };
            }
            
            if (isSelected) {
                return { fillColor: '#9c27b0', color: '#ffffff', weight: 2, fillOpacity: 0.6 };
            } else if (props.church_pop > 0) {
                return { fillColor: '#2196f3', color: '#2196f3', weight: 1, fillOpacity: 0.15 };
            } else {
                return { fillOpacity: 0, weight: 0 };
            }
        }"""
tract_map_code = tract_map_code.replace(style_old, style_new)

# Fix resetHighlight
reset_old = """        function resetHighlight(e) {
            geojsonLayer.resetStyle(e.target);
            info.update();
        }"""
reset_new = """        function resetHighlight(e) {
            geojsonLayer.resetStyle(e.target);
            // Ensure style reflects current selection state
            e.target.setStyle(getStyle(e.target.feature));
            info.update();
        }"""
tract_map_code = tract_map_code.replace(reset_old, reset_new)

# Fix logic loop
loop_old = """            geojsonData.features.forEach(f => {
                if (f.properties.cumulative_pct <= threshold) {
                    tractsIncluded++;
                    if (f.properties.cumulative_pop > maxPopIncluded) {
                        maxPopIncluded = f.properties.cumulative_pop;
                    }
                    
                    let tractStats = censusStats[f.properties.GEOID];
                    if (tractStats) {
                        for (let key in agg) {
                            agg[key] += (tractStats[key] || 0);
                        }
                    }
                }
            });"""

loop_new = """            geojsonLayer.eachLayer(function(layer) {
                layer.setStyle(getStyle(layer.feature));
            });
            
            // If user clicked, update label to Custom
            if (userOverrodeSlider) {
                pctLabel.innerText = "Custom";
            }
            
            geojsonData.features.forEach(f => {
                if (selectedTractIds.has(f.properties.GEOID)) {
                    tractsIncluded++;
                    // recalculate maxPopIncluded from actual church pop for custom selections
                    maxPopIncluded += (f.properties.church_pop || 0);
                    
                    let tractStats = censusStats[f.properties.GEOID];
                    if (tractStats) {
                        for (let key in agg) {
                            agg[key] += (tractStats[key] || 0);
                        }
                    }
                }
            });"""
tract_map_code = tract_map_code.replace(loop_old, loop_new)

with open("generate_tract_map.py", "w") as f:
    f.write(tract_map_code)

print("Updated both scripts.")
