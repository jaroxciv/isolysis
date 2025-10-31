### don't use update later

import osmnx as ox
import geopandas as gpd

place_name = "El Salvador"
admin_level = "6"  # 4 = departments, 6 = municipalities

# Directly query by place name rather than polygon
gdf_admins = ox.features_from_place(
    place_name,
    tags={"boundary": "administrative", "admin_level": admin_level},
)

# Filter & save
gdf_admins = gdf_admins[gdf_admins.geometry.type.isin(["Polygon", "MultiPolygon"])]
gdf_admins = gdf_admins[["name", "admin_level", "geometry"]].reset_index(drop=True)

out = f"data/el_salvador_admin_level_{admin_level}.gpkg"
gdf_admins.to_file(out, driver="GPKG")
print(f"✅ Saved {len(gdf_admins)} features to {out}")
