TRANSLATIONS = {
    "es": {
        # ── Language selector ──
        "lang.label": "Idioma / Language",
        # ── Page titles ──
        "page.isochrone_title": "🗺️ Análisis de Isócronas",
        "page.raster_title": "📈 Análisis Iso-Ráster",
        # ── Main titles ──
        "main.title": "🗺️ Visualizador de Red",
        "main.subtitle": "Haz clic en cualquier parte del mapa para ver coordenadas",
        "raster.title": "📈 Análisis Iso-Ráster",
        "raster.caption": "Calcula estadísticas ráster dentro de isócronas y sus intersecciones.",
        # ── Sidebar: Isochrone Settings ──
        "sidebar.header": "⚙️ Parámetros",
        "sidebar.provider": "Modelo de Generación",
        "sidebar.provider_help": "Selecciona el motor de ruteo",
        "sidebar.time_unit": "Unidad de Tiempo",
        "sidebar.minutes": "Minutos",
        "sidebar.hours": "Horas",
        "sidebar.travel_time": "Tiempo de Viaje",
        "sidebar.travel_time_help_min": "Tiempo máximo de viaje desde el centro (minutos)",
        "sidebar.travel_time_help_hrs": "Tiempo máximo de viaje desde el centro (horas)",
        "sidebar.isoline_type": "Estimación de Frontera",
        "sidebar.isoline_type_help": "Calcular por tiempo de viaje (isócrona) o distancia (isodistancia)",
        "sidebar.travel_mode": "Modo de Transporte",
        "sidebar.speed_profile": "Perfil de Velocidad",
        "sidebar.max_speed": "Velocidad Máxima (km/h)",
        "sidebar.max_speed_help": "Opcional: velocidad máxima para isócronas Iso4App",
        "sidebar.color_scheme": "Esquema de Color",
        "sidebar.settings_label": "**Configuración:**",
        "sidebar.settings_provider": "Proveedor: {provider}",
        "sidebar.settings_time_min": "Tiempo de viaje: {value} min",
        "sidebar.settings_time_hrs": "Tiempo de viaje: {value}h",
        "sidebar.settings_type": "Tipo: {type}",
        "sidebar.settings_mobility": "Movilidad: {mobility}",
        "sidebar.settings_speed": "Velocidad: {speed}",
        "sidebar.settings_speed_limit": "Límite de velocidad: {limit} km/h",
        # ── Sidebar: Raster Settings ──
        "sidebar.raster_header": "⚙️ Configuración Iso-Ráster",
        "sidebar.travel_time_minutes": "Tiempo de Viaje (minutos)",
        "sidebar.travel_time_centroid_help": "Tiempo máximo de viaje para cada centroide.",
        "sidebar.upload_rasters": "📂 Subir Ráster(s) (.tif)",
        "sidebar.upload_boundary": "Subir archivo de límites (.gpkg, .geojson, .zip para shapefile)",
        # ── Upload Coordinates ──
        "upload.header": "📂 Subir Coordenadas",
        "upload.label": "Subir coordenadas (JSON, CSV, XLSX)",
        "upload.help": "Sube un archivo con coordenadas. CSV/XLSX debe incluir columnas: Categoria, Subcategoria, Nombre, Latitud, Longitud.",
        "upload.success": "✅ Se cargaron {count} coordenadas",
        "upload.remove_btn": "🗑️ Eliminar Coordenadas Subidas",
        "upload.removed": "✅ Coordenadas subidas eliminadas",
        # ── Map interaction ──
        "map.clicked": "📍 **Clic:** {lat}, {lng}",
        "map.latitude": "Latitud",
        "map.longitude": "Longitud",
        "map.add_center": "➕ Agregar Centro",
        "map.add_isochrone": "➕ Agregar Isócrona Aquí",
        "map.computing": "Calculando isócrona para {name}...",
        "map.click_hint": "👆 Hacer clic en el mapa para definir el vértice de la isócrona o isodistancia",
        # ── Isochrone processing ──
        "iso.band_missing": "band_hours no encontrado en las propiedades del feature",
        "iso.added": "✅ Se agregó {name} con {count} banda(s){cache}",
        "iso.no_band_data": "❌ No se encontraron datos de banda válidos para {name}",
        "iso.no_geojson": "❌ No se devolvieron datos geojson para {name}",
        "iso.failed": "❌ Error al calcular la isócrona para {name}",
        "iso.created": "✅ Isócrona creada para {name}",
        "iso.request_failed": "❌ La solicitud de isócrona falló.",
        # ── Center controls ──
        "centers.header": "📍 Centros Almacenados ({count})",
        "centers.undo": "↶ Deshacer",
        "centers.removed": "🗑️ Se eliminó {name}",
        "centers.clear_polygons": "🧹 Eliminar Polígonos",
        "centers.cleared_polygons": "🧹 Se eliminaron {count} polígonos",
        "centers.clear_all": "🗑️ Eliminar Todo",
        "centers.cleared_all": "🗑️ Se eliminaron {centers} centros y {polygons} polígonos",
        "centers.bands_info": " - {bands} banda(s) | {minutes}min @ {speed} km/h",
        "centers.max_prod_label": "Prod Máx:",
        "centers.color_label": "Color",
        # ── Tooltips / Popups ──
        "tooltip.time_band": "Banda de Tiempo",
        "tooltip.pois_covered": "POIs Cubiertos",
        "tooltip.coverage": "Cobertura",
        "tooltip.prod_sum": "Agg Prod",
        "tooltip.max_prod": "Prod Máx",
        "tooltip.viable_yes": "Viable: Sí",
        "tooltip.viable_no": "Viable: No",
        "tooltip.viable_yes_icon": "✅ Sí",
        "tooltip.viable_no_icon": "❌ No",
        "tooltip.lat": "Lat",
        "tooltip.lon": "Lon",
        "tooltip.region": "Región",
        "tooltip.municipality": "Municipio",
        "tooltip.na": "N/D",
        # ── Viable / Not Viable display ──
        "viable.yes": "Viable",
        "viable.no": "No Viable",
        # ── Spatial Analysis ──
        "analysis.header": "🧮 Análisis Espacial",
        "analysis.analyze_btn": "🔍 Analizar Cobertura",
        "analysis.computing": "Calculando análisis espacial...",
        "analysis.complete": "✅ ¡Análisis completado!",
        "analysis.failed_no_data": "❌ No se pudo completar el análisis — verifique que los centros tienen isócronas calculadas y que hay POIs cargados.",
        "analysis.failed": "❌ Error en el análisis: {error}",
        "analysis.caption": "Analizar {centers} centros contra {pois} POIs",
        # ── Analysis Summary ──
        "summary.header": "📊 Resumen del Análisis",
        "summary.total_pois": "Total POIs",
        "summary.total_pois_help": "Total de puntos de interés analizados",
        "summary.noi": "Índice de Optimización de Red",
        "summary.noi_help": "(X - Y - Z) / total_pois - mide la eficiencia de cobertura de la red",
        "summary.coverage": "Cobertura",
        "summary.coverage_help": "Porcentaje de POIs cubiertos por al menos una isócrona",
        "summary.intersections": "Intersecciones",
        "summary.intersections_help": "Número de áreas superpuestas entre diferentes centros",
        "summary.covered": "Cubiertos",
        "summary.covered_help": "POIs cubiertos por al menos una isócrona",
        "summary.uncovered": "No Cubiertos",
        "summary.uncovered_help": "POIs fuera de todas las áreas de cobertura",
        # ── Coverage Analysis ──
        "coverage.header": "🎯 Análisis de Cobertura",
        "coverage.col_center": "Centro",
        "coverage.col_time_band": "Banda de Tiempo",
        "coverage.col_pois_covered": "POIs Cubiertos",
        "coverage.col_coverage_pct": "Cobertura %",
        "coverage.col_prod_sum": "Agg Prod",
        "coverage.col_viable": "Viable",
        "coverage.viable_yes": "✅ Sí",
        "coverage.viable_no": "❌ No",
        "coverage.viable_na": "-",
        "coverage.total_centers": "Total Centros",
        "coverage.viable_count": "Viables",
        "coverage.not_viable_count": "No Viables",
        # ── Intersection Analysis ──
        "intersection.no_intersections": "ℹ️ No se encontraron intersecciones entre centros",
        "intersection.header": "🔄 Análisis de Intersecciones",
        "intersection.pairwise": "**Superposiciones de 2 vías:**",
        "intersection.pois_label": "{count} POIs",
        "intersection.more": "... y {count} intersecciones más",
        "intersection.multiway": "**Superposiciones múltiples:**",
        # ── Out-of-Band Analysis ──
        "oob.all_covered": "🎉 ¡Todos los POIs están cubiertos por al menos un centro!",
        "oob.header": "🚫 Áreas No Cubiertas",
        "oob.warning": "⚠️ {count} POIs ({pct}%) no están cubiertos por ningún centro",
        "oob.uncovered_pois": "**POIs No Cubiertos:**",
        "oob.and_more": "... y {count} más",
        # ── Export ──
        "export.btn": "📥 Exportar Datos de Cobertura",
        # ── Tabs ──
        "tab.coverage": "🎯 Cobertura",
        "tab.intersections": "🔄 Intersecciones",
        "tab.uncovered": "🚫 No Cubiertos",
        # ── Raster app specific ──
        "raster.loaded_rasters": "✅ Se cargaron {count} ráster(s)",
        "raster.loaded_boundary": "✅ Archivos de límites cargados: {names}",
        "raster.loaded_isochrones": "🗺️ Isócronas Cargadas",
        "raster.remove_btn": "❌ Eliminar",
        "raster.isochrone_removed": "Isócrona '{name}' eliminada.",
        "raster.clear_isochrones": "🗑️ Limpiar Isócronas",
        "raster.cleared_isochrones": "Se limpiaron {count} isócrona(s)",
        "raster.clear_boundary": "🗑️ Limpiar Límites",
        "raster.boundary_cleared": "Límites limpiados",
        "raster.clear_rasters": "🗑️ Limpiar Rásters",
        "raster.cleared_rasters": "Se limpiaron {count} ráster(s)",
        "raster.clear_all": "🗑️ Limpiar Todo",
        "raster.cleared_all": "Se limpió todo ({count} isócronas, límites, rásters)",
        "raster.compute_btn": "📊 Calcular Estadísticas Ráster",
        "raster.upload_raster_warning": "Sube al menos un archivo ráster.",
        "raster.upload_boundary_warning": "Sube un archivo de límites o agrega isócronas primero.",
        "raster.both_error": "❌ Por favor usa límites o isócronas, no ambos.",
        "raster.computing_stats": "Calculando estadísticas ráster...",
        "raster.stats_failed": "❌ La solicitud de estadísticas ráster falló.",
        "raster.stats_unexpected": "❌ Formato de respuesta API inesperado.",
        "raster.stats_done": "✅ ¡Estadísticas ráster calculadas!",
        "raster.stats_header": "📊 Estadísticas Ráster",
        "raster.warning_center": "⚠️ No se pudo leer el centro del ráster: {error}",
        "raster.unsupported_boundary": "Formato de límites no soportado.",
        "raster.no_geometries": "⚠️ El archivo de límites no contiene geometrías.",
        "raster.overlay_error": "⚠️ No se pudo renderizar la superposición del ráster: {error}",
        "raster.boundary_error": "⚠️ No se pudo renderizar la superposición de límites: {error}",
        # ── API error ──
        "api.error": "Error de API: {error}",
    },
    "en": {
        # ── Language selector ──
        "lang.label": "Language / Idioma",
        # ── Page titles ──
        "page.isochrone_title": "🗺️ Isochrone Analysis",
        "page.raster_title": "📈 Iso-Raster Analysis",
        # ── Main titles ──
        "main.title": "🗺️ Network Visualizer",
        "main.subtitle": "Click anywhere on the map to see coordinates",
        "raster.title": "📈 Iso-Raster Analysis",
        "raster.caption": "Compute raster statistics inside isochrones and their intersections.",
        # ── Sidebar: Isochrone Settings ──
        "sidebar.header": "⚙️ Isochrone Settings",
        "sidebar.provider": "Provider",
        "sidebar.provider_help": "Choose routing engine",
        "sidebar.time_unit": "Time Unit",
        "sidebar.minutes": "Minutes",
        "sidebar.hours": "Hours",
        "sidebar.travel_time": "Travel Time",
        "sidebar.travel_time_help_min": "Maximum travel time from center (minutes)",
        "sidebar.travel_time_help_hrs": "Maximum travel time from center (hours)",
        "sidebar.isoline_type": "Isoline Type",
        "sidebar.isoline_type_help": "Compute by travel time (isochrone) or distance (isodistance)",
        "sidebar.travel_mode": "Travel Mode",
        "sidebar.speed_profile": "Speed Profile",
        "sidebar.max_speed": "Maximum Speed (km/h)",
        "sidebar.max_speed_help": "Optional: maximum speed used for Iso4App isochrones",
        "sidebar.color_scheme": "Color Scheme",
        "sidebar.settings_label": "**Settings:**",
        "sidebar.settings_provider": "Provider: {provider}",
        "sidebar.settings_time_min": "Travel time: {value} min",
        "sidebar.settings_time_hrs": "Travel time: {value}h",
        "sidebar.settings_type": "Type: {type}",
        "sidebar.settings_mobility": "Mobility: {mobility}",
        "sidebar.settings_speed": "Speed: {speed}",
        "sidebar.settings_speed_limit": "Speed limit: {limit} km/h",
        # ── Sidebar: Raster Settings ──
        "sidebar.raster_header": "⚙️ Iso-Raster Settings",
        "sidebar.travel_time_minutes": "Travel Time (minutes)",
        "sidebar.travel_time_centroid_help": "Maximum travel time for each centroid.",
        "sidebar.upload_rasters": "📂 Upload Raster(s) (.tif)",
        "sidebar.upload_boundary": "Upload boundary file (.gpkg, .geojson, .zip for shapefile)",
        # ── Upload Coordinates ──
        "upload.header": "📂 Upload Coordinates",
        "upload.label": "Upload coordinates (JSON, CSV, XLSX)",
        "upload.help": "Upload a file with coordinates. CSV/XLSX must include columns: Categoria, Subcategoria, Nombre, Latitud, Longitud.",
        "upload.success": "✅ Loaded {count} coordinates",
        "upload.remove_btn": "🗑️ Remove Uploaded Coordinates",
        "upload.removed": "✅ Uploaded coordinates removed",
        # ── Map interaction ──
        "map.clicked": "📍 **Clicked:** {lat}, {lng}",
        "map.latitude": "Latitude",
        "map.longitude": "Longitude",
        "map.add_center": "➕ Add Center",
        "map.add_isochrone": "➕ Add Isochrone Here",
        "map.computing": "Computing isochrone for {name}...",
        "map.click_hint": "👆 Click on the map to define the vertex of the isochrone or isodistance",
        # ── Isochrone processing ──
        "iso.band_missing": "band_hours not found in feature properties",
        "iso.added": "✅ Added {name} with {count} band(s){cache}",
        "iso.no_band_data": "❌ No valid band data found for {name}",
        "iso.no_geojson": "❌ No geojson data returned for {name}",
        "iso.failed": "❌ Failed to compute isochrone for {name}",
        "iso.created": "✅ Isochrone created for {name}",
        "iso.request_failed": "❌ Isochrone request failed.",
        # ── Center controls ──
        "centers.header": "📍 Stored Centers ({count})",
        "centers.undo": "↶ Undo Last",
        "centers.removed": "🗑️ Removed {name}",
        "centers.clear_polygons": "🧹 Remove Polygons",
        "centers.cleared_polygons": "🧹 Removed {count} polygons",
        "centers.clear_all": "🗑️ Remove All",
        "centers.cleared_all": "🗑️ Removed {centers} centers & {polygons} polygons",
        "centers.bands_info": " - {bands} band(s) | {minutes}min @ {speed} km/h",
        "centers.max_prod_label": "Max Prod:",
        "centers.color_label": "Color",
        # ── Tooltips / Popups ──
        "tooltip.time_band": "Time Band",
        "tooltip.pois_covered": "POIs Covered",
        "tooltip.coverage": "Coverage",
        "tooltip.prod_sum": "Agg Prod",
        "tooltip.max_prod": "Max Prod",
        "tooltip.viable_yes": "Viable: Yes",
        "tooltip.viable_no": "Viable: No",
        "tooltip.viable_yes_icon": "✅ Yes",
        "tooltip.viable_no_icon": "❌ No",
        "tooltip.lat": "Lat",
        "tooltip.lon": "Lon",
        "tooltip.region": "Region",
        "tooltip.municipality": "Municipality",
        "tooltip.na": "N/A",
        # ── Viable / Not Viable display ──
        "viable.yes": "Viable",
        "viable.no": "Not Viable",
        # ── Spatial Analysis ──
        "analysis.header": "🧮 Spatial Analysis",
        "analysis.analyze_btn": "🔍 Analyze Coverage",
        "analysis.computing": "Computing spatial analysis...",
        "analysis.complete": "✅ Analysis complete!",
        "analysis.failed_no_data": "❌ Analysis could not complete — verify that centers have computed isochrones and that POIs are loaded.",
        "analysis.failed": "❌ Analysis error: {error}",
        "analysis.caption": "Analyze {centers} centers against {pois} POIs",
        # ── Analysis Summary ──
        "summary.header": "📊 Analysis Summary",
        "summary.total_pois": "Total POIs",
        "summary.total_pois_help": "Total points of interest analyzed",
        "summary.noi": "Network Optimization Index",
        "summary.noi_help": "(X - Y - Z) / total_pois - measures how efficiently the network covers POIs",
        "summary.coverage": "Coverage",
        "summary.coverage_help": "Percentage of POIs covered by at least one isochrone",
        "summary.intersections": "Intersections",
        "summary.intersections_help": "Number of overlapping areas between different centers",
        "summary.covered": "Covered",
        "summary.covered_help": "POIs covered by at least one isochrone",
        "summary.uncovered": "Uncovered",
        "summary.uncovered_help": "POIs outside all coverage areas",
        # ── Coverage Analysis ──
        "coverage.header": "🎯 Coverage Analysis",
        "coverage.col_center": "Center",
        "coverage.col_time_band": "Time Band",
        "coverage.col_pois_covered": "POIs Covered",
        "coverage.col_coverage_pct": "Coverage %",
        "coverage.col_prod_sum": "Agg Prod",
        "coverage.col_viable": "Viable",
        "coverage.viable_yes": "✅ Yes",
        "coverage.viable_no": "❌ No",
        "coverage.viable_na": "-",
        "coverage.total_centers": "Total Centers",
        "coverage.viable_count": "Viable",
        "coverage.not_viable_count": "Not Viable",
        # ── Intersection Analysis ──
        "intersection.no_intersections": "ℹ️ No intersections found between centers",
        "intersection.header": "🔄 Intersection Analysis",
        "intersection.pairwise": "**2-way Overlaps:**",
        "intersection.pois_label": "{count} POIs",
        "intersection.more": "... and {count} more intersections",
        "intersection.multiway": "**Multi-way Overlaps:**",
        # ── Out-of-Band Analysis ──
        "oob.all_covered": "🎉 All POIs are covered by at least one center!",
        "oob.header": "🚫 Uncovered Areas",
        "oob.warning": "⚠️ {count} POIs ({pct}%) are not covered by any center",
        "oob.uncovered_pois": "**Uncovered POIs:**",
        "oob.and_more": "... and {count} more",
        # ── Export ──
        "export.btn": "📥 Export Coverage Data",
        # ── Tabs ──
        "tab.coverage": "🎯 Coverage",
        "tab.intersections": "🔄 Intersections",
        "tab.uncovered": "🚫 Uncovered",
        # ── Raster app specific ──
        "raster.loaded_rasters": "✅ Loaded {count} raster(s)",
        "raster.loaded_boundary": "✅ Loaded boundary file(s): {names}",
        "raster.loaded_isochrones": "🗺️ Loaded Isochrones",
        "raster.remove_btn": "❌ Remove",
        "raster.isochrone_removed": "Isochrone '{name}' removed.",
        "raster.clear_isochrones": "🗑️ Clear Isochrones",
        "raster.cleared_isochrones": "Cleared {count} isochrone(s)",
        "raster.clear_boundary": "🗑️ Clear Boundary",
        "raster.boundary_cleared": "Boundary cleared",
        "raster.clear_rasters": "🗑️ Clear Rasters",
        "raster.cleared_rasters": "Cleared {count} raster(s)",
        "raster.clear_all": "🗑️ Clear All",
        "raster.cleared_all": "Cleared everything ({count} isochrones, boundary, rasters)",
        "raster.compute_btn": "📊 Compute Raster Stats",
        "raster.upload_raster_warning": "Upload at least one raster file.",
        "raster.upload_boundary_warning": "Upload a boundary file or add isochrones first.",
        "raster.both_error": "❌ Please use either boundary or isochrones, not both.",
        "raster.computing_stats": "Computing raster statistics...",
        "raster.stats_failed": "❌ Raster stats request failed.",
        "raster.stats_unexpected": "❌ Unexpected API response format.",
        "raster.stats_done": "✅ Raster stats computed!",
        "raster.stats_header": "📊 Raster Statistics",
        "raster.warning_center": "⚠️ Could not read raster center: {error}",
        "raster.unsupported_boundary": "Unsupported boundary format.",
        "raster.no_geometries": "⚠️ Boundary file contains no geometries.",
        "raster.overlay_error": "⚠️ Could not render raster overlay: {error}",
        "raster.boundary_error": "⚠️ Could not render boundary overlay: {error}",
        # ── API error ──
        "api.error": "API Error: {error}",
    },
}

# ── Selectbox option mappings ──
# Maps display labels to API values per language
SELECTBOX_OPTIONS = {
    "isoline_type": {
        "es": {
            "labels": ["Isócrona", "Isodistancia"],
            "values": ["isochrone", "isodistance"],
        },
        "en": {
            "labels": ["Isochrone", "Isodistance"],
            "values": ["isochrone", "isodistance"],
        },
    },
    "travel_mode": {
        "es": {
            "labels": ["Vehículo motorizado", "Bicicleta", "Peatón"],
            "values": ["motor_vehicle", "bicycle", "pedestrian"],
        },
        "en": {
            "labels": ["Motor Vehicle", "Bicycle", "Pedestrian"],
            "values": ["motor_vehicle", "bicycle", "pedestrian"],
        },
    },
    "speed_profile": {
        "es": {
            "labels": ["Muy baja", "Baja", "Normal", "Rápida"],
            "values": ["very_low", "low", "normal", "fast"],
        },
        "en": {
            "labels": ["Very Low", "Low", "Normal", "Fast"],
            "values": ["very_low", "low", "normal", "fast"],
        },
    },
}


def t(key: str, lang: str | None = None, **kwargs) -> str:
    """Get translated string for the given or current language.

    If lang is not provided, reads st.session_state.lang (default: "es").
    Falls back to English, then to [key] if the key is missing entirely.
    """
    if lang is None:
        try:
            import streamlit as st

            lang = st.session_state.get("lang", "es")
        except Exception:
            lang = "es"
    assert lang is not None
    text = TRANSLATIONS.get(lang, {}).get(key)
    if text is None:
        text = TRANSLATIONS.get("en", {}).get(key)
    if text is None:
        return f"[{key}]"
    if kwargs:
        try:
            return text.format(**kwargs)
        except KeyError:
            return text
    return text


def get_selectbox_options(key: str, lang: str | None = None):
    """Return (display_labels, api_values) for a selectbox based on current language."""
    if lang is None:
        try:
            import streamlit as st

            lang = st.session_state.get("lang", "es")
        except Exception:
            lang = "es"
    assert lang is not None
    opts = SELECTBOX_OPTIONS.get(key, {}).get(lang)
    if opts is None:
        opts = SELECTBOX_OPTIONS.get(key, {}).get("en", {"labels": [], "values": []})
    return opts["labels"], opts["values"]
