import re

with open("generate_tract_map.py", "r") as f:
    code = f.read()

# Update UI HTML
ui_old = """        <div class="stat-row"><span class="stat-label">Total Population</span><span class="stat-val" id="ms-pop">0</span></div>
        <h4 style="margin: 15px 0 5px 0; font-size: 13px; color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 5px;">Age Profile <span style="font-size: 10px; color:#888; float:right;">(Tracts vs Church)</span></h4>"""

ui_new = """        <h4 style="margin: 0 0 5px 0; font-size: 13px; color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 5px;">Population & Penetration</h4>
        <div class="stat-row"><span class="stat-label">Neighborhood Pop.</span><span class="stat-val" id="ms-pop">0</span></div>
        <div class="stat-row"><span class="stat-label">Church Pop.</span><span class="stat-val" id="ch-pop" style="color:#ffeb3b">0</span></div>
        <div class="stat-row"><span class="stat-label">Church Ratio</span><span class="stat-val" id="ms-ratio">0%</span></div>

        <h4 style="margin: 15px 0 5px 0; font-size: 13px; color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 5px;">Age Profile <span style="font-size: 10px; color:#888; float:right;">(Neighborhood vs Church)</span></h4>"""
code = code.replace(ui_old, ui_new)


# Add the Census Religion note at the bottom of the panel
panel_end_old = """        <div class="stat-row"><span class="stat-label">Renters</span><span class="stat-val" id="ms-renters">0%</span></div>
    </div>"""

panel_end_new = """        <div class="stat-row"><span class="stat-label">Renters</span><span class="stat-val" id="ms-renters">0%</span></div>
        <div style="font-size:10px; color:#888; margin-top:15px; font-style:italic; line-height: 1.3;">Note: The US Census Bureau is prohibited by law from collecting data on religious affiliation, so tract-level religious stats are unavailable.</div>
    </div>"""
code = code.replace(panel_end_old, panel_end_new)


# Update JS logic to populate these new fields
js_old = """            document.getElementById('ms-pop').innerText = agg.total_pop.toLocaleString();
            document.getElementById('ms-age-0-17').innerText = formatPct(agg.age_0_17, agg.total_pop);"""

js_new = """            document.getElementById('ms-pop').innerText = agg.total_pop.toLocaleString();
            document.getElementById('ch-pop').innerText = c_agg.pop.toLocaleString();
            
            if (agg.total_pop > 0 && c_agg.pop > 0) {
                let pct = (c_agg.pop / agg.total_pop * 100).toFixed(2);
                let ratio = Math.round(agg.total_pop / c_agg.pop);
                document.getElementById('ms-ratio').innerText = pct + "% (1 in " + ratio.toLocaleString() + ")";
            } else {
                document.getElementById('ms-ratio').innerText = "0%";
            }

            document.getElementById('ms-age-0-17').innerText = formatPct(agg.age_0_17, agg.total_pop);"""
code = code.replace(js_old, js_new)

with open("generate_tract_map.py", "w") as f:
    f.write(code)
print("Updated UI code.")
