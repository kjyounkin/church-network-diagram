import osmnx as ox
import networkx as nx
import geopandas as gpd
from shapely.geometry import Point
import alphashape
import warnings
import json

warnings.filterwarnings("ignore")

CHURCH_LAT = 41.6371503
CHURCH_LON = -93.6860107
center_point = (CHURCH_LAT, CHURCH_LON)

graph_file = "/home/kyle/ad_hoc_analysis/graph_45k.graphml"

print("Loading street network from disk...")
G = ox.load_graphml(graph_file)

print("Projecting graph...")
G_proj = ox.project_graph(G)

center_node = ox.distance.nearest_nodes(G, center_point[1], center_point[0])

trip_times = [45, 40, 35, 30, 25, 20, 15, 10, 5]
colors = {
    45: '#444444',
    40: '#666666',
    35: '#888888',
    30: '#FF0000',
    25: '#FF8C00',
    20: '#FFD700',
    15: '#00FF00',
    10: '#00FFFF',
    5:  '#FF00FF'
}

print("Calculating isochrones using alphashape...")
node_gdf_proj = ox.graph_to_gdfs(G_proj, edges=False)
features = []

for trip_time in trip_times:
    travel_time_seconds = trip_time * 60
    subgraph = nx.ego_graph(G, center_node, radius=travel_time_seconds, distance='travel_time')
    
    node_ids = list(subgraph.nodes())
    if not node_ids:
        continue
        
    subgraph_nodes = node_gdf_proj.loc[node_ids]
    
    try:
        points = [(pt.x, pt.y) for pt in subgraph_nodes.geometry]
        poly = alphashape.alphashape(points, 0.0005)
        poly = poly.buffer(200)
    except Exception as e:
        poly = subgraph_nodes.geometry.buffer(1200).unary_union.simplify(200)
        
    # Project back to EPSG:4326 for GeoJSON
    poly_gdf = gpd.GeoSeries([poly], crs=node_gdf_proj.crs).to_crs("EPSG:4326")
    poly_4326 = poly_gdf.iloc[0]
    
    features.append({
        "type": "Feature",
        "geometry": poly_4326.__geo_interface__,
        "properties": {
            "time": trip_time,
            "color": colors.get(trip_time, '#000000')
        }
    })

geojson = {
    "type": "FeatureCollection",
    "features": features
}

with open("/home/kyle/church-network-diagram/church_isochrones.json", "w") as f:
    json.dump(geojson, f)

print("Saved church_isochrones.json")
