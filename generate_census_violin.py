import json
import psycopg2
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import random

def generate_image():
    # 1. Fetch Census Data from local file
    with open('census.json', 'r') as f:
        resp = json.load(f)
    
    census_data = resp['data']['14000US19153000801']['B01001']['estimate']
    
    # Bucket definitions: (start_age, end_age)
    male_buckets = {
        'B01001003': (0, 4), 'B01001004': (5, 9), 'B01001005': (10, 14), 'B01001006': (15, 17),
        'B01001007': (18, 19), 'B01001008': (20, 20), 'B01001009': (21, 21), 'B01001010': (22, 24),
        'B01001011': (25, 29), 'B01001012': (30, 34), 'B01001013': (35, 39), 'B01001014': (40, 44),
        'B01001015': (45, 49), 'B01001016': (50, 54), 'B01001017': (55, 59), 'B01001018': (60, 61),
        'B01001019': (62, 64), 'B01001020': (65, 66), 'B01001021': (67, 69), 'B01001022': (70, 74),
        'B01001023': (75, 79), 'B01001024': (80, 84), 'B01001025': (85, 95)
    }
    
    female_buckets = {
        'B01001027': (0, 4), 'B01001028': (5, 9), 'B01001029': (10, 14), 'B01001030': (15, 17),
        'B01001031': (18, 19), 'B01001032': (20, 20), 'B01001033': (21, 21), 'B01001034': (22, 24),
        'B01001035': (25, 29), 'B01001036': (30, 34), 'B01001037': (35, 39), 'B01001038': (40, 44),
        'B01001039': (45, 49), 'B01001040': (50, 54), 'B01001041': (55, 59), 'B01001042': (60, 61),
        'B01001043': (62, 64), 'B01001044': (65, 66), 'B01001045': (67, 69), 'B01001046': (70, 74),
        'B01001047': (75, 79), 'B01001048': (80, 84), 'B01001049': (85, 95)
    }
    
    data = []
    
    # Generate synthetic census data points
    for k, (start, end) in male_buckets.items():
        count = int(census_data.get(k, 0))
        for _ in range(count):
            data.append({'age': random.uniform(start, end+0.99), 'gender': 'Male', 'group': 'Census Tract'})
            
    for k, (start, end) in female_buckets.items():
        count = int(census_data.get(k, 0))
        for _ in range(count):
            data.append({'age': random.uniform(start, end+0.99), 'gender': 'Female', 'group': 'Census Tract'})
            
    # 2. Fetch Church Data
    conn = psycopg2.connect(
        dbname="warehouse", user="meltano", password="WEFC", host="postgres", port="5432"
    )
    cur = conn.cursor()
    cur.execute("""
        SELECT age, gender
        FROM raw.v_people
        WHERE age < 100 
          AND age IS NOT NULL
          AND membership IN ('Member', 'Regular Attender')
          AND status = 'active'
          AND primary_campus = 'Westchester EFC'
          AND gender IN ('Male', 'Female')
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    for row in rows:
        data.append({'age': row[0], 'gender': row[1], 'group': 'Westchester EFC'})
        
    df = pd.DataFrame(data)
    
    # 3. Plot
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # Check seaborn version for scale/density_norm param change
    import pkg_resources
    sns_version = pkg_resources.get_distribution("seaborn").version
    kwargs = {}
    if sns_version >= '0.13.0':
        kwargs['density_norm'] = 'area'
    else:
        kwargs['scale'] = 'area'
        
    sns.violinplot(
        data=df, 
        x='group', 
        y='age', 
        hue='gender', 
        split=True, 
        inner='quartile', 
        palette={'Male': '#36a2eb', 'Female': '#ff6384'},
        ax=ax,
        bw_adjust=0.8,
        **kwargs
    )
    
    ax.set_title('Age & Gender Distribution: Church vs Census Tract 19153000801', color='white', pad=20, fontsize=14)
    ax.set_xlabel('')
    ax.set_ylabel('Age (Years)', color='#c9d1d9', fontsize=12)
    ax.legend(title='Gender', loc='upper right', facecolor='#161b22', edgecolor='#30363d')
    ax.grid(axis='y', color='#30363d', linestyle='-', linewidth=0.5, alpha=0.5)
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#8b949e')
    ax.spines['bottom'].set_visible(False)
    ax.tick_params(colors='#8b949e', bottom=False)
    
    fig.patch.set_facecolor('#0d1117')
    ax.set_facecolor('#0d1117')
    
    plt.tight_layout()
    plt.savefig('census_violin.png', dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    print("Saved census_violin.png")

if __name__ == "__main__":
    generate_image()
