with open("generate_tract_map.py", "r") as f:
    code = f.read()

agg_old = """            let agg = {{
                total_pop: 0, kids: 0, total_families: 0, single_parent_kids: 0,
                total_marital: 0, married: 0, divorced_separated: 0, white: 0,
                hispanic: 0, total_lang: 0, lep: 0, total_pov: 0, in_poverty: 0,
                total_housing: 0, renters: 0
            }};"""

agg_new = """            let agg = {{
                total_pop: 0, kids: 0, total_families: 0, single_parent_kids: 0,
                total_marital: 0, married: 0, divorced_separated: 0, white: 0,
                hispanic: 0, total_lang: 0, lep: 0, total_pov: 0, in_poverty: 0,
                total_housing: 0, renters: 0,
                age_0_17: 0, age_18_34: 0, age_35_49: 0, age_50_64: 0, age_65_plus: 0
            }};
            let c_agg = {{
                pop: 0, age_0_17: 0, age_18_34: 0, age_35_49: 0, age_50_64: 0, age_65_plus: 0
            }};"""
code = code.replace(agg_old, agg_new)

loop_old = """                    let tractStats = censusStats[f.properties.GEOID];
                    if (tractStats) {{
                        for (let key in agg) {{
                            agg[key] += (tractStats[key] || 0);
                        }}
                    }}
                }}
            }});"""

loop_new = """                    let tractStats = censusStats[f.properties.GEOID];
                    if (tractStats) {{
                        for (let key in agg) {{
                            agg[key] += (tractStats[key] || 0);
                        }}
                    }}
                    let cStats = churchStats[f.properties.GEOID];
                    if (cStats) {{
                        for (let key in c_agg) {{
                            c_agg[key] += (cStats[key] || 0);
                        }}
                    }}
                }}
            }});"""
code = code.replace(loop_old, loop_new)

with open("generate_tract_map.py", "w") as f:
    f.write(code)
print("Fixed c_agg definition")
