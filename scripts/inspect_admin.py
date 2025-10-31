import geopandas as gpd
import fiona
from pathlib import Path

# --- Paths ---
src_path = Path("data/el_salvador_admin_levels.gpkg")
data_dir = Path("data")

# --- List layers in source file ---
layers = fiona.listlayers(src_path)
print("📚 Layers found:", layers)

# --- Export each layer as its own .gpkg in data/ ---
for layer in layers:
    gdf = gpd.read_file(src_path, layer=layer)
    out_file = data_dir / f"el_salvador_{layer}.gpkg"
    gdf.to_file(out_file, driver="GPKG")
    print(f"✅ Saved {len(gdf)} features → {out_file}")
