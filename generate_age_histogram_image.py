import psycopg2
import matplotlib.pyplot as plt
import numpy as np

def generate_image():
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
    
    ages = list(range(0, 100))
    male_counts = np.array([data["Male"].get(a, 0) for a in ages])
    female_counts = np.array([data["Female"].get(a, 0) for a in ages])
    
    # Configure styling to match dark theme loosely
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Create stacked bar chart
    ax.bar(ages, male_counts, label='Men', color='#36a2eb', alpha=0.8)
    ax.bar(ages, female_counts, bottom=male_counts, label='Women', color='#ff6384', alpha=0.8)
    
    ax.set_title('Age Distribution (Active Members/Regulars at Westchester EFC)', color='white')
    ax.set_xlabel('Age')
    ax.set_ylabel('Count')
    ax.legend()
    ax.grid(axis='y', color='#30363d', linestyle='-', linewidth=0.5)
    
    # Remove borders
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#8b949e')
    ax.spines['bottom'].set_color('#8b949e')
    ax.tick_params(colors='#8b949e')
    
    fig.patch.set_facecolor('#0d1117')
    ax.set_facecolor('#0d1117')
    
    plt.tight_layout()
    plt.savefig('age_histogram.png', dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    print("Saved age_histogram.png")

if __name__ == "__main__":
    generate_image()
