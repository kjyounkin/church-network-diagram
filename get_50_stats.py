import json
import re

with open("generate_tract_map.py", "r") as f:
    code = f.read()

# Extract geojson and censusStats from the python script globals
import geopandas as gpd

gdf = gpd.read_file('iowa_tracts.geojson')
# wait, easiest way is to just run a subset of generate_tract_map.py or parse the html.
# Let's just execute generate_tract_map.py up to the sequence building, then aggregate.
