import psycopg2
import json
import sys

def get_db_data():
    conn = psycopg2.connect(
        dbname="warehouse",
        user="meltano",
        password="WEFC",
        host="postgres",
        port="5432"
    )
    cur = conn.cursor()
    
    query = """
    SELECT age, gender, COUNT(*) as count
    FROM raw.v_people
    WHERE age < 100 
      AND age IS NOT NULL
      AND membership IN ('Member', 'Regular Attender')
      AND status = 'active'
      AND primary_campus = 'Westchester EFC'
      AND gender IN ('Male', 'Female')
    GROUP BY age, gender
    ORDER BY age;
    """
    cur.execute(query)
    rows = cur.fetchall()
    
    data = {"Male": {}, "Female": {}}
    for row in rows:
        age, gender, count = row
        data[gender][age] = count
        
    cur.close()
    conn.close()
    return data

def generate_html(data):
    # Ensure all ages from 0 to 99 are represented
    ages = list(range(0, 100))
    male_counts = [data["Male"].get(a, 0) for a in ages]
    female_counts = [data["Female"].get(a, 0) for a in ages]
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Age Histogram</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0d1117; color: #c9d1d9; padding: 20px; }}
        .chart-container {{ position: relative; height: 80vh; width: 90vw; margin: auto; }}
        h2 {{ text-align: center; color: #58a6ff; }}
        .nav {{ position: absolute; top: 20px; left: 20px; }}
        .nav a {{ color: #58a6ff; text-decoration: none; border: 1px solid #58a6ff; padding: 5px 10px; border-radius: 4px; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="nav">
        <a href="index.html">&larr; Network</a>
        <a href="geo_map.html" style="margin-left: 10px;">Geo Map &rarr;</a>
    </div>
    <h2>Age Distribution (Active Members/Regulars at Westchester EFC)</h2>
    <div class="chart-container">
        <canvas id="ageChart"></canvas>
    </div>
    
    <script>
        const ctx = document.getElementById('ageChart').getContext('2d');
        const ageChart = new Chart(ctx, {{
            type: 'bar',
            data: {{
                labels: {json.dumps(ages)},
                datasets: [
                    {{
                        label: 'Men',
                        data: {json.dumps(male_counts)},
                        backgroundColor: 'rgba(54, 162, 235, 0.7)',
                        borderColor: 'rgba(54, 162, 235, 1)',
                        borderWidth: 1
                    }},
                    {{
                        label: 'Women',
                        data: {json.dumps(female_counts)},
                        backgroundColor: 'rgba(255, 99, 132, 0.7)',
                        borderColor: 'rgba(255, 99, 132, 1)',
                        borderWidth: 1
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    x: {{
                        stacked: true,
                        title: {{ display: true, text: 'Age', color: '#8b949e' }},
                        ticks: {{ color: '#8b949e' }},
                        grid: {{ color: '#30363d' }}
                    }},
                    y: {{
                        stacked: true,
                        title: {{ display: true, text: 'Count', color: '#8b949e' }},
                        ticks: {{ color: '#8b949e' }},
                        grid: {{ color: '#30363d' }}
                    }}
                }},
                plugins: {{
                    legend: {{
                        labels: {{ color: '#c9d1d9' }}
                    }},
                    tooltip: {{
                        mode: 'index',
                        intersect: false
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""
    with open("age_histogram.html", "w") as f:
        f.write(html)
    print("Created age_histogram.html")

if __name__ == "__main__":
    data = get_db_data()
    generate_html(data)
