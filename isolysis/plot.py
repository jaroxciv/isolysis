import os
import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as ctx
from loguru import logger


def plot_isochrones(
    gpkg_path: str,
    layer: str = "isochrones",
    color_by: str = "band_hours",
    out_png: str = None,
    provider: str = None,
    figsize=(10, 10),
    cmap="plasma",
    alpha=0.5,
    edgecolor="k",
    linewidth=0.8,
):
    """
    Plot banded isochrones from a GeoPackage file over a basemap, and save to PNG.
    If provider is specified, use it for the title and PNG filename.
    """
    if not os.path.exists(gpkg_path):
        logger.error(f"GeoPackage not found: {gpkg_path}")
        return

    gdf = gpd.read_file(gpkg_path, layer=layer)
    if gdf.empty:
        logger.error(f"No features found in {gpkg_path} (layer: {layer})")
        return

    # Always ensure CRS is set for transformation and plotting
    if gdf.crs is None:
        gdf.set_crs("EPSG:4326", inplace=True)
    gdf_web = gdf.to_crs(epsg=3857)

    # Correct order: plot largest bands first (bottom), smallest last (top)
    gdf_web = gdf_web.sort_values(color_by, ascending=False)

    fig, ax = plt.subplots(figsize=figsize)

    # logger.debug(gdf_web[[color_by, 'geometry']].assign(area_km2 = gdf_web['geometry'].area / 1e6))

    # Plotting: smallest bands will be on top, colors will be correct
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

    # Title: use provider if specified
    if provider:
        ax.set_title(f"{provider.title()} Isochrones")
    else:
        ax.set_title("Isochrones")
    plt.tight_layout()

    # Output filename: use provider prefix if available
    if out_png is None and provider:
        out_png = f"outputs/{provider}_isochrones_plot.png"
    elif out_png is None:
        out_png = "outputs/isochrones_plot.png"

    if out_png:
        fig.savefig(out_png, dpi=180)
        logger.success(f"Saved isochrone plot as {out_png}")

    plt.show()
