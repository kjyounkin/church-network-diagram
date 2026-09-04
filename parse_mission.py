import json

with open('mission_census.json', 'r') as f:
    resp = json.load(f)

data = resp['data']['14000US19153000801']

def get_est(table, var_id):
    try:
        return data[table]['estimate'][f"{table}{str(var_id).zfill(3)}"]
    except KeyError:
        return 0

# Age
total_pop = get_est('B01001', 1)
kids = sum(get_est('B01001', i) for i in [3,4,5,6, 27,28,29,30])
young_adults = sum(get_est('B01001', i) for i in [7,8,9,10,11,12, 31,32,33,34,35,36])
middle_age = sum(get_est('B01001', i) for i in [13,14,15,16,17, 37,38,39,40,41])
seniors = sum(get_est('B01001', i) for i in range(18,26)) + sum(get_est('B01001', i) for i in range(42,50))

# Marital Status
total_marital = get_est('B12001', 1)
never_married = get_est('B12001', 3) + get_est('B12001', 12)
separated = get_est('B12001', 7) + get_est('B12001', 16)
married_total = get_est('B12001', 4) + get_est('B12001', 13)
married = married_total - separated
divorced = get_est('B12001', 10) + get_est('B12001', 19)
divorced_separated = divorced + separated
widowed = get_est('B12001', 9) + get_est('B12001', 18)

# Ethnicity
white = get_est('B03002', 3)
black = get_est('B03002', 4)
asian = get_est('B03002', 6)
hispanic = get_est('B03002', 12)
other_race = total_pop - (white + black + asian + hispanic)

# Language
total_lang = get_est('C16001', 1)
english_only = get_est('C16001', 2)
lep = sum(get_est('C16001', i) for i in [5, 8, 11, 14, 17, 20, 23, 26, 29, 32, 35, 38])

# Income
total_hh = get_est('B19001', 1)
inc_under_25k = sum(get_est('B19001', i) for i in range(2, 6))
inc_25_50k = sum(get_est('B19001', i) for i in range(6, 11))
inc_50_100k = sum(get_est('B19001', i) for i in range(11, 14))
inc_over_100k = sum(get_est('B19001', i) for i in range(14, 18))

# Children at home
total_families = get_est('B11003', 1)
families_with_kids = get_est('B11003', 3) + get_est('B11003', 10) + get_est('B11003', 16)
single_parent_kids = get_est('B11003', 10) + get_est('B11003', 16)

# Poverty & Housing
total_pov = get_est('B17001', 1)
in_poverty = get_est('B17001', 2)

total_housing = get_est('B25003', 1)
owners = get_est('B25003', 2)
renters = get_est('B25003', 3)

def pct(val, total):
    if total == 0: return 0
    return round((val / total) * 100, 1)

md = f"""# 🏙️ Neighborhood Mission Profile
**Census Tract 19153000801 ("Dogpatch to Donut Hut")**

This profile provides a data-driven snapshot of the community immediately surrounding Westchester EFC, based on the latest US Census Bureau American Community Survey (ACS) 5-Year Estimates. This data is structured to help identify ministry opportunities, demographic realities, and community needs.

---

### 👥 1. Population Overview
**Total Population:** {total_pop:,.0f} residents

* **Children & Youth (0-17):** {pct(kids, total_pop)}%
* **Young Adults (18-34):** {pct(young_adults, total_pop)}%
* **Middle Age (35-59):** {pct(middle_age, total_pop)}%
* **Seniors (60+):** {pct(seniors, total_pop)}%

*Ministry Insight: Compare these brackets to your current children's, youth, and young adult ministries to see where community engagement has room to grow.*

---

### 👨‍👩‍👧‍👦 2. Family & Household Status
**Total Households:** {total_hh:,.0f} | **Total Families:** {total_families:,.0f}

* **Families with Children at Home:** {pct(families_with_kids, total_families)}% of all families.
* **Single-Parent Families:** {pct(single_parent_kids, total_families)}% of all families (or {pct(single_parent_kids, families_with_kids)}% of families with children).
* **Marital Status (15+):** 
  * Married: {pct(married, total_marital)}%
  * Never Married: {pct(never_married, total_marital)}%
  * Divorced or Separated: {pct(divorced_separated, total_marital)}%
  * Widowed: {pct(widowed, total_marital)}%

*Ministry Insight: A high percentage of single-parent households or divorced individuals often highlights a need for childcare support, single-parent ministries, and counseling/support groups.*

---

### 🌍 3. Culture & Ethnicity
* **White:** {pct(white, total_pop)}%
* **Black:** {pct(black, total_pop)}%
* **Hispanic or Latino:** {pct(hispanic, total_pop)}%
* **Asian:** {pct(asian, total_pop)}%
* **Other / Multi-racial:** {pct(other_race, total_pop)}%

**Language Proficiency:**
* **English Only:** {pct(english_only, total_lang)}%
* **Limited English Proficiency (LEP):** {pct(lep, total_lang)}% of the neighborhood struggles with English.

*Ministry Insight: If LEP or Hispanic populations are significant, consider bilingual signage, ESL (English as a Second Language) classes, or translating service materials.*

---

### 💵 4. Economics & Housing
**Poverty Rate:** {pct(in_poverty, total_pov)}% of residents live below the poverty line.

**Household Income Distribution:**
* **Under $25k:** {pct(inc_under_25k, total_hh)}%
* **$25k - $50k:** {pct(inc_25_50k, total_hh)}%
* **$50k - $100k:** {pct(inc_50_100k, total_hh)}%
* **Over $100k:** {pct(inc_over_100k, total_hh)}%

**Housing Tenure:**
* **Homeowners:** {pct(owners, total_housing)}%
* **Renters:** {pct(renters, total_housing)}%

*Ministry Insight: High renter populations indicate higher transiency (people moving frequently), requiring faster assimilation tracks. High poverty or low-income percentages highlight opportunities for food pantries, financial peace classes, and benevolence ministries.*
"""

with open('mission_summary.md', 'w') as f:
    f.write(md)
print("Markdown generated successfully!")
