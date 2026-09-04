import psycopg2
import json
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from scipy import stats

def generate_image():
    try:
        with open('geo_cache.json', 'r') as f:
            geo_cache = json.load(f)
    except:
        geo_cache = {}

    conn = psycopg2.connect(
        dbname="warehouse", user="meltano", password="WEFC", host="postgres", port="5432"
    )
    cur = conn.cursor()
    
    cur.execute("""
        SELECT 
            p.age, p.status, p.membership,
            a.attributes_street_line_1, a.attributes_city, a.attributes_state, a.attributes_zip
        FROM raw.v_people p
        JOIN raw.pco_addresses a ON p.person_id = a.relationships_person_data_id::INTEGER
        WHERE a.attributes_street_line_1 IS NOT NULL
          AND p.age > 18 AND p.age < 100
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    data = []
    for row in rows:
        age, status, membership, street, city, state, zip_code = row
        
        street = (street or "").replace("\n", " ").strip()
        city = (city or "").strip()
        state = (state or "").strip()
        zip_code = (zip_code or "").strip()
        addr_str = f"{street}, {city}, {state} {zip_code}"
        
        geo = geo_cache.get(addr_str)
        if geo and geo.get('lat') is not None:
            dist = geo.get('drive_dist', 0)
            time_mins = geo.get('drive_time', 0)
            
            if dist > 0 and dist < 50:
                data.append({
                    'age': age,
                    'drive_time': time_mins,
                    'drive_dist': dist
                })
                
    df = pd.DataFrame(data)
    
    if len(df) == 0:
        print("No data matched filters!")
        return
        
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(10, 6))
    
    sns.scatterplot(data=df, x='age', y='drive_time', alpha=0.5, color='#58a6ff', s=40, ax=ax, edgecolor='none')
    
    median_age = df['age'].median()
    median_time = df['drive_time'].median()
    
    ax.axvline(median_age, color='#ff6384', linestyle='--', linewidth=2, label=f'Median Age ({median_age:.1f} y)')
    ax.axhline(median_time, color='#3cb44b', linestyle='--', linewidth=2, label=f'Median Time ({median_time:.1f} m)')
    
    slope, intercept, r_value, p_value, std_err = stats.linregress(df['age'], df['drive_time'])
    
    x_vals = np.array(ax.get_xlim())
    y_vals = intercept + slope * x_vals
    ax.plot(x_vals, y_vals, color='#ffe119', linewidth=2.5, label=f'Trend Line')
    
    stats_text = (f"Regression Stats:\n"
                  f"Slope: {slope:.3f} min/yr\n"
                  f"r: {r_value:.3f}\n"
                  f"R²: {r_value**2:.3f}")
    
    props = dict(boxstyle='round,pad=0.5', facecolor='#161b22', alpha=0.9, edgecolor='#30363d')
    ax.text(0.03, 0.95, stats_text, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', bbox=props, color='#c9d1d9')
            
    ax.set_title('Age vs Drive Time from Church (Ages 19-99, >0 to <50 miles)', color='white', pad=20, fontsize=14)
    ax.set_xlabel('Age (Years)', color='#c9d1d9', fontsize=12)
    ax.set_ylabel('Drive Time (Minutes)', color='#c9d1d9', fontsize=12)
    ax.legend(loc='upper right', facecolor='#161b22', edgecolor='#30363d')
    ax.grid(color='#30363d', linestyle='-', linewidth=0.5, alpha=0.5)
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#8b949e')
    ax.spines['bottom'].set_color('#8b949e')
    ax.tick_params(colors='#8b949e')
    
    fig.patch.set_facecolor('#0d1117')
    ax.set_facecolor('#0d1117')
    
    plt.tight_layout()
    plt.savefig('scatter_chart.png', dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    print("Saved scatter_chart.png")

if __name__ == "__main__":
    generate_image()
