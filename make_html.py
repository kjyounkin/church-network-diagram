html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Core 50% Mission Summary</title>
    <style>
        body { margin: 0; padding: 20px; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0d1117; color: #c9d1d9; line-height: 1.6; }
        .container { max-width: 900px; margin: 0 auto; background: rgba(13, 17, 23, 0.95); padding: 40px; border-radius: 8px; border: 1px solid #30363d; box-shadow: 0 4px 6px rgba(0,0,0,0.5); }
        .nav { margin-bottom: 20px; }
        .nav a { color: #58a6ff; text-decoration: none; border: 1px solid #58a6ff; padding: 5px 10px; border-radius: 4px; font-size: 14px; margin-right: 10px; }
        h1 { color: #58a6ff; border-bottom: 2px solid #30363d; padding-bottom: 10px; }
        h2 { color: #ffeb3b; margin-top: 30px; border-bottom: 1px solid #30363d; padding-bottom: 5px; }
        h3 { color: #c9d1d9; margin-top: 25px; }
        .alert { padding: 15px; border-radius: 6px; margin: 20px 0; border-left: 4px solid; background: rgba(255,255,255,0.05); }
        .alert-note { border-left-color: #58a6ff; }
        .alert-tip { border-left-color: #3fb950; }
        .alert-important { border-left-color: #a371f7; }
        .alert-caution { border-left-color: #f85149; }
        .alert strong { color: #fff; display: block; margin-bottom: 5px; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { border: 1px solid #30363d; padding: 10px; text-align: left; }
        th { background: #161b22; color: #8b949e; }
        ul { margin-top: 5px; }
        .mermaid { background: transparent; padding: 20px; display: flex; justify-content: center; }
        hr { border: 0; border-top: 1px solid #30363d; margin: 40px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="nav">
            <a href="index.html">&larr; Network Index</a>
            <a href="contiguous_tracts.html">Interactive Map &rarr;</a>
        </div>
        
        <h1>Core Neighborhood Mission Summary</h1>
        <p><strong>Target Area:</strong> 50% Contiguous Church Footprint (21 Census Tracts)</p>

        <div class="alert alert-note">
            <strong>What is this area?</strong>
            This profile represents the 21 geographically contiguous census tracts immediately surrounding Westchester EFC that encompass exactly 50% of the active church congregation. It represents the immediate "Jerusalem" of the church's neighborhood footprint.
        </div>

        <hr>

        <h2>📊 Demographic Snapshot</h2>
        <p><strong>Total Population:</strong> 90,105</p>

        <h3>Age Distribution</h3>
        <div class="mermaid">
        pie title Age Breakdown
            "0-17 (Kids/Youth)" : 22.6
            "18-34 (Young Adults)" : 23.5
            "35-49 (Mid Adults)" : 20.8
            "50-64 (Older Adults)" : 16.9
            "65+ (Seniors)" : 16.2
        </div>

        <h3>Household & Economic Status</h3>
        <table>
            <thead>
                <tr>
                    <th>Metric</th>
                    <th>Percentage</th>
                    <th>Count</th>
                    <th>Insight</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><strong>Married Adults</strong></td>
                    <td>51.3%</td>
                    <td>37,466</td>
                    <td>Represents a strong, stable family baseline.</td>
                </tr>
                <tr>
                    <td><strong>Single-Parent Families</strong></td>
                    <td>13.8%</td>
                    <td>3,215</td>
                    <td>Significant block requiring wrap-around support.</td>
                </tr>
                <tr>
                    <td><strong>Divorced/Separated</strong></td>
                    <td>12.4%</td>
                    <td>9,073</td>
                    <td>Highlights a need for recovery and care ministries.</td>
                </tr>
                <tr>
                    <td><strong>Renters</strong></td>
                    <td>32.8%</td>
                    <td>12,620</td>
                    <td>1 in 3 households are mobile/transient.</td>
                </tr>
                <tr>
                    <td><strong>Below Poverty Line</strong></td>
                    <td>9.6%</td>
                    <td>8,496</td>
                    <td>Solidly middle-class area, but with distinct pockets of need.</td>
                </tr>
            </tbody>
        </table>

        <h3>Diversity & Language</h3>
        <ul>
            <li><strong>White Population:</strong> 75.2%</li>
            <li><strong>Hispanic Population:</strong> 8.3%</li>
            <li><strong>Limited English Proficiency (LEP):</strong> 6.0% (Over 5,000 individuals)</li>
        </ul>

        <hr>

        <h2>👥 Ministry Personas</h2>
        <p>Based on the exact metrics of this 50% core, here are 3 "average" personas representing distinct segments of these neighborhoods, and what it takes to effectively minister to them:</p>

        <h3>1. The "Settled Millennial" Family</h3>
        <p><strong>The Data Behind Them:</strong> 51.3% married, 22.6% children, 67% homeowners.</p>
        <p><strong>The Persona:</strong> Married, in their mid-30s to early 40s, with two kids in local schools. They are financially stable but incredibly time-crunched due to dual incomes and kids' sports/activities.</p>
        <div class="alert alert-tip">
            <strong>Ministry Strategy</strong>
            <ul>
                <li><strong>Don't add to their calendar:</strong> They are exhausted. If you ask them to attend 3 events a week, they will burn out. Emphasize <em>equipping</em> them to do discipleship in their own home.</li>
                <li><strong>NextGen Excellence:</strong> Their primary motivator for engaging a church is often, <em>"Is this a safe, morally grounding community for my kids?"</em></li>
                <li><strong>Marital Support:</strong> Provide marriage enrichment and parenting classes as highly accessible entry points for unchurched families in this demographic.</li>
            </ul>
        </div>

        <h3>2. The "Transient Young Adult" Renter</h3>
        <p><strong>The Data Behind Them:</strong> 23.5% of the population is 18-34 (the largest single age block), and 32.8% of the footprint rents.</p>
        <p><strong>The Persona:</strong> In their 20s, unmarried, renting an apartment. They are highly mobile (might move across town or out of state in 2 years) and suffer from the highest rates of loneliness of any generation. They are highly skeptical of institutional religion but crave spirituality.</p>
        <div class="alert alert-important">
            <strong>Ministry Strategy</strong>
            <ul>
                <li><strong>Third Spaces:</strong> They aren't looking for a flashy Sunday service; they are looking for a living room. Small groups, hospitality, and shared meals are non-negotiable.</li>
                <li><strong>Fast On-Ramps:</strong> Because they are transient, if your discipleship pathway requires 2 years of rootedness to get involved, you will lose them. Get them serving and integrated within weeks.</li>
                <li><strong>Apologetics & Vocation:</strong> They are asking deep questions about meaning, sexuality, and how to integrate their faith into their secular workplaces.</li>
            </ul>
        </div>

        <h3>3. The "On-the-Margins" Neighbor</h3>
        <p><strong>The Data Behind Them:</strong> 13.8% of families are single-parent households, 9.6% live below the poverty line, and a massive 6.0% have Limited English Proficiency.</p>
        <p><strong>The Persona:</strong> A single mother working two jobs to make ends meet, or a first-generation immigrant/refugee family navigating a new culture and language barriers.</p>
        <div class="alert alert-caution">
            <strong>Ministry Strategy</strong>
            <ul>
                <li><strong>Incarnational over Attractional:</strong> They cannot and will not simply "show up" to a Sunday service. The church must go to them.</li>
                <li><strong>Practical Wraparound Support:</strong> Ministry here looks like ESL classes hosted at the church, free after-school tutoring programs, or a robust single-mom support ministry (oil changes, childcare, financial counseling).</li>
                <li><strong>Language Integration:</strong> With over 5,000 limited-English speakers in just your closest 21 tracts, offering translation headsets or planting a bilingual congregation could be a massive avenue for gospel expansion.</li>
            </ul>
        </div>

    </div>

    <!-- Mermaid Initialization -->
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        mermaid.initialize({ startOnLoad: true, theme: 'dark' });
    </script>
</body>
</html>
"""

with open("core_50_mission_summary.html", "w") as f:
    f.write(html_content)
