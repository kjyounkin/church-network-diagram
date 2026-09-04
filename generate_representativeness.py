import json
import psycopg2
import matplotlib.pyplot as plt
import numpy as np

def generate_image():
    # 1. Fetch Census Data from local file
    with open('census.json', 'r') as f:
        resp = json.load(f)
    
    census_data = resp['data']['14000US19153000801']['B01001']['estimate']
    
    # Bucket definitions for Total Population
    buckets = [
        ("0-4", ['B01001003', 'B01001027']),
        ("5-9", ['B01001004', 'B01001028']),
        ("10-14", ['B01001005', 'B01001029']),
        ("15-17", ['B01001006', 'B01001030']),
        ("18-19", ['B01001007', 'B01001031']),
        ("20", ['B01001008', 'B01001032']),
        ("21", ['B01001009', 'B01001033']),
        ("22-24", ['B01001010', 'B01001034']),
        ("25-29", ['B01001011', 'B01001035']),
        ("30-34", ['B01001012', 'B01001036']),
        ("35-39", ['B01001013', 'B01001037']),
        ("40-44", ['B01001014', 'B01001038']),
        ("45-49", ['B01001015', 'B01001039']),
        ("50-54", ['B01001016', 'B01001040']),
        ("55-59", ['B01001017', 'B01001041']),
        ("60-61", ['B01001018', 'B01001042']),
        ("62-64", ['B01001019', 'B01001043']),
        ("65-66", ['B01001020', 'B01001044']),
        ("67-69", ['B01001021', 'B01001045']),
        ("70-74", ['B01001022', 'B01001046']),
        ("75-79", ['B01001023', 'B01001047']),
        ("80-84", ['B01001024', 'B01001048']),
        ("85+", ['B01001025', 'B01001049'])
    ]
    
    census_counts = []
    bucket_labels = []
    for label, keys in buckets:
        bucket_labels.append(label)
        census_counts.append(sum(int(census_data.get(k, 0)) for k in keys))
        
    total_census = sum(census_counts)
    census_pct = [c / total_census * 100 for c in census_counts]
    
    # 2. Fetch Church Data
    conn = psycopg2.connect(
        dbname="warehouse", user="meltano", password="WEFC", host="postgres", port="5432"
    )
    cur = conn.cursor()
    cur.execute("""
        SELECT age
        FROM raw.v_people
        WHERE age IS NOT NULL
          AND membership IN ('Member', 'Regular Attender')
          AND status = 'active'
          AND primary_campus = 'Westchester EFC'
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    church_counts = [0] * len(buckets)
    
    for row in rows:
        age = row[0]
        # Map age to bucket
        if age <= 4: idx = 0
        elif age <= 9: idx = 1
        elif age <= 14: idx = 2
        elif age <= 17: idx = 3
        elif age <= 19: idx = 4
        elif age == 20: idx = 5
        elif age == 21: idx = 6
        elif age <= 24: idx = 7
        elif age <= 29: idx = 8
        elif age <= 34: idx = 9
        elif age <= 39: idx = 10
        elif age <= 44: idx = 11
        elif age <= 49: idx = 12
        elif age <= 54: idx = 13
        elif age <= 59: idx = 14
        elif age <= 61: idx = 15
        elif age <= 64: idx = 16
        elif age <= 66: idx = 17
        elif age <= 69: idx = 18
        elif age <= 74: idx = 19
        elif age <= 79: idx = 20
        elif age <= 84: idx = 21
        else: idx = 22
        
        church_counts[idx] += 1
        
    total_church = sum(church_counts)
    church_pct = [c / total_church * 100 for c in church_counts]
    
    # 3. Plot Stacked/Overlapping Histograms (Subplots)
    plt.style.use('dark_background')
    
    # Create two subplots stacked on top of each other
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)
    
    x = np.arange(len(bucket_labels))
    width = 0.8
    
    # Top Plot: Church Profile
    ax1.bar(x, church_pct, width, color='#36a2eb', alpha=0.8, edgecolor='white')
    ax1.set_title('Westchester EFC Church Population by Age (%)', color='white', pad=10, fontsize=14)
    ax1.set_ylabel('% of Church', color='#c9d1d9', fontsize=12)
    ax1.grid(axis='y', color='#30363d', linestyle='-', linewidth=0.5, alpha=0.5)
    
    # Add values on top of bars
    for i, v in enumerate(church_pct):
        if v > 0:
            ax1.text(i, v + 0.5, f"{v:.1f}%", ha='center', color='#c9d1d9', fontsize=9)
            
    # Bottom Plot: Census Tract Profile
    ax2.bar(x, census_pct, width, color='#ff6384', alpha=0.8, edgecolor='white')
    ax2.set_title('Census Tract 19153000801 Population by Age (%)', color='white', pad=10, fontsize=14)
    ax2.set_ylabel('% of Neighborhood', color='#c9d1d9', fontsize=12)
    ax2.grid(axis='y', color='#30363d', linestyle='-', linewidth=0.5, alpha=0.5)
    
    for i, v in enumerate(census_pct):
        if v > 0:
            ax2.text(i, v + 0.5, f"{v:.1f}%", ha='center', color='#c9d1d9', fontsize=9)
    
    # Configure X-axis
    ax2.set_xticks(x)
    ax2.set_xticklabels(bucket_labels, rotation=45, ha='right')
    ax2.set_xlabel('Census Age Brackets', color='#c9d1d9', fontsize=12)
    
    # Match Y-axis limits so they are perfectly comparable visually
    max_y = max(max(church_pct), max(census_pct)) + 3
    ax1.set_ylim(0, max_y)
    ax2.set_ylim(0, max_y)
    
    # Remove borders
    for ax in [ax1, ax2]:
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#8b949e')
        ax.spines['bottom'].set_color('#8b949e')
        ax.tick_params(colors='#8b949e')
        ax.set_facecolor('#0d1117')
        
    fig.patch.set_facecolor('#0d1117')
    
    plt.tight_layout()
    plt.savefig('representativeness.png', dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    print("Saved representativeness.png")

if __name__ == "__main__":
    generate_image()
