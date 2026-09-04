import psycopg2
import json
import os
import re

DB_HOST = "postgres"
DB_PORT = "5432"
DB_USER = "meltano"
DB_PASS = "WEFC"
DB_NAME = "warehouse"

STAFF_NAMES = {
    "Chuck Mullikin", "Haitao Cheng", "Michelle Van Wyngarden", "Kaurie Long",
    "Alysa Younkin", "Randyl Lynn Dicks", "Julius Williams"
}
ELDER_NAMES = {
    "Todd Troll", "Chris Mielke", "Scott Van Wyngarden", "Wayne Smith",
    "John Neal", "Thomas Avila", "Steve Getz"
}

def get_data():
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        dbname=DB_NAME
    )
    cur = conn.cursor()

    # People Nodes
    cur.execute("""
        SELECT person_id, full_name, primary_campus, membership, status
        FROM raw.v_people
    """)
    people_rows = cur.fetchall()

    nodes = []
    people_ids = set()
    for row in people_rows:
        pid = row[0]
        name = row[1] or "Unknown"
        campus = row[2] or "Unknown Campus"
        membership = row[3] or ""
        status = row[4] or "inactive"
        
        if membership == 'Giver Only':
            continue
            
        role = 'Regular'
        if name in STAFF_NAMES:
            role = 'Staff'
        elif name in ELDER_NAMES:
            role = 'Elder'
        elif membership == 'Member':
            role = 'Member'
            
        nodes.append({
            "id": pid,
            "name": name,
            "group": campus,
            "val": 3,
            "nodeType": "person",
            "role": role,
            "status": status
        })
        people_ids.add(pid)

    # Address Nodes
    cur.execute("""
        SELECT DISTINCT
            attributes_street_line_1 || ', ' || COALESCE(attributes_city, '') || ', ' || COALESCE(attributes_state, '') || ' ' || COALESCE(attributes_zip, '') AS full_address,
            attributes_street_line_1,
            attributes_city
        FROM raw.pco_addresses
        WHERE attributes_street_line_1 IS NOT NULL
    """)
    address_rows = cur.fetchall()

    for row in address_rows:
        addr_id = row[0]
        nodes.append({
            "id": addr_id,
            "name": row[1] or "Unknown Street",
            "group": row[2] or "Unknown City",
            "val": 8,
            "nodeType": "entity",
            "role": "Regular"
        })

    # Links
    cur.execute("""
        SELECT 
            relationships_person_data_id::INTEGER AS source_id,
            attributes_street_line_1 || ', ' || COALESCE(attributes_city, '') || ', ' || COALESCE(attributes_state, '') || ' ' || COALESCE(attributes_zip, '') AS target_id,
            COALESCE(attributes_location, 'Address') AS type
        FROM raw.pco_addresses
        WHERE attributes_street_line_1 IS NOT NULL AND relationships_person_data_id IS NOT NULL
    """)
    link_rows = cur.fetchall()

    links = []
    for row in link_rows:
        source_id = row[0]
        target_id = row[1]
        link_type = row[2]
        
        if source_id in people_ids:
            links.append({
                "source": source_id,
                "target": target_id,
                "type": link_type,
                "weight": 2
            })

    cur.close()
    conn.close()
    return {"nodes": nodes, "links": links}

def generate_html(graph_data):
    with open('anchor_map.html', 'r') as f:
        html = f.read()

    start_str = 'const rawData = '
    start_idx = html.find(start_str)
    end_idx = html.find(';', start_idx)
    new_html = html[:start_idx] + f"const rawData = {json.dumps(graph_data)}" + html[end_idx:]
    
    # Change Title and Header
    new_html = new_html.replace('Connection Network Diagram', 'Address Network Diagram')
    new_html = new_html.replace('<h3>Connection Filters</h3>', '<h3>Address Filters</h3>')
    
    # Fix filters logic to grab ALL types instead of specifically Service/Group/Event
    filter_logic_replace = """
        const section = document.createElement('div');
        section.className = 'filter-section';
        section.innerHTML = `<div class="filter-title">Location Type</div>`;
        uniqueTypes.forEach(type => {
            const color = colorScale(type);
            const label = document.createElement('label');
            label.innerHTML = `<input type="checkbox" value="${type}" checked> <span class="color-key" style="background: ${color};"></span> ${type}`;
            section.appendChild(label);
        });
        filtersDiv.appendChild(section);
"""
    # Use regex to replace the complex group logic with simple types logic
    new_html = re.sub(r'const groups = \{.*?(?=let hoverNode = null;)', filter_logic_replace + '\n        ', new_html, flags=re.DOTALL)
    
    # Add stroke drawing code to nodeCanvasObject
    draw_stroke_code = """
                if (node.role && node.role !== 'Regular' && node.nodeType !== 'entity') {
                    ctx.lineWidth = size * 0.3;
                    if (node.role === 'Elder') ctx.strokeStyle = '#ffd700';
                    else if (node.role === 'Staff') ctx.strokeStyle = '#a371f7';
                    else if (node.role === 'Member') ctx.strokeStyle = '#3fb950';
                    ctx.stroke();
                }
"""
    # Insert stroke drawing before text drawing (if it's not an entity)
    # The canvas fill is done with ctx.fill();
    new_html = new_html.replace('ctx.fill();', 'ctx.fill();' + draw_stroke_code)
    
    # Also we want to ensure role colors are represented in legend, but for now stroke is enough
    
    with open('address_map.html', 'w') as f:
        f.write(new_html)

if __name__ == "__main__":
    data = get_data()
    generate_html(data)
