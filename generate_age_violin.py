import psycopg2
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

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
    SELECT age, gender
    FROM raw.v_people
    WHERE age < 100 
      AND age IS NOT NULL
      AND membership IN ('Member', 'Regular Attender')
      AND status = 'active'
      AND primary_campus = 'Westchester EFC'
      AND gender IN ('Male', 'Female')
    """
    cur.execute(query)
    rows = cur.fetchall()
    
    # Load into pandas DataFrame
    df = pd.DataFrame(rows, columns=['age', 'gender'])
    
    cur.close()
    conn.close()
    
    # Configure styling to match dark theme loosely
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Plot violin chart
    # We can plot gender on x-axis and age on y-axis, or vice versa.
    # A single violin split by gender (using a dummy x variable) is often nice for comparing two distributions side-by-side.
    df['dummy'] = 'Overall'
    
    sns.violinplot(
        data=df, 
        x='dummy', 
        y='age', 
        hue='gender', 
        split=True, 
        inner='quartile', 
        palette={'Male': '#36a2eb', 'Female': '#ff6384'},
        ax=ax
    )
    
    ax.set_title('Age Distribution by Gender (Westchester EFC)', color='white')
    ax.set_xlabel('')
    ax.set_ylabel('Age')
    
    # Tweak legend and axes
    ax.legend(title='Gender')
    ax.grid(axis='y', color='#30363d', linestyle='-', linewidth=0.5)
    
    # Remove borders
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#8b949e')
    ax.spines['bottom'].set_visible(False)
    ax.tick_params(colors='#8b949e', bottom=False)
    
    fig.patch.set_facecolor('#0d1117')
    ax.set_facecolor('#0d1117')
    
    plt.tight_layout()
    plt.savefig('age_violin.png', dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    print("Saved age_violin.png")

if __name__ == "__main__":
    generate_image()
