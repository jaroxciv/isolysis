# isolysis/plot.py

import os
import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as ctx
from loguru import logger


def plot_isochrones(
    gpkg_path: str = "outputs/isochrones.gpkg",
    layer: str = "isochrones",
    color_by: str = "band_hours",
    out_png: str = "outputs/isochrones_plot.png",
    figsize=(10, 10),
    cmap="plasma",
    alpha=0.5,
    edgecolor="k",
    linewidth=0.8,
):
    """
    Plot banded isochrones from a GeoPackage file over a basemap, save to PNG.
    """
    if not os.path.exists(gpkg_path):
        logger.error(f"GeoPackage not found: {gpkg_path}")
        return

    gdf = gpd.read_file(gpkg_path, layer=layer)
    if gdf.empty:
        logger.error(f"No features found in {gpkg_path} (layer: {layer})")
        return

    # Reproject to Web Mercator for contextily
    gdf_web = gdf.to_crs(epsg=3857)
    gdf_web = gdf_web.sort_values(color_by, ascending=False)

    fig, ax = plt.subplots(figsize=figsize)
    gdf_web.plot(
        ax=ax,
        column=color_by,
        cmap=cmap,
        legend=True,
        alpha=alpha,
        edgecolor=edgecolor,
        linewidth=linewidth,
        legend_kwds={"label": "Travel time (hours)"},
    )

    ctx.add_basemap(
        ax,
        source=ctx.providers.CartoDB.Positron,
        attribution_size=8,
    )
    ax.set_axis_off()
    plt.tight_layout()

    # Save to PNG
    fig.savefig(out_png, dpi=180)
    logger.success(f"Saved isochrone plot as {out_png}")
    plt.show()


if __name__ == "__main__":
    plot_isochrones()
