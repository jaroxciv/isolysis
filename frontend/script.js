document.addEventListener("DOMContentLoaded", () => {
  // --- Leaflet Map Initialization ---
  const map = L.map("map").setView([40.7128, -74.006], 13); // Default to NYC
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(map);

  // --- DOM Element References ---
  const providerSelect = document.getElementById("provider");
  const rhoInput = document.getElementById("rho");
  const coordinatesFileInput = document.getElementById("coordinates-file");
  const computeBtn = document.getElementById("compute");
  const clearCentroidsBtn = document.getElementById("clear-centroids");
  const clearIsochronesBtn = document.getElementById("clear-isochrones");
  const summaryContent = document.getElementById("summary-content");

  // --- State Management ---
  let centroids = [];
  let centroidMarkers = [];
  let isochroneLayers = [];
  let uploadedCoordinates = null;

  // --- Event Listener for Map Clicks ---
  map.on("click", (e) => {
    const { lat, lng } = e.latlng;
    const rho = parseFloat(rhoInput.value);
    const id = `centroid-${centroids.length + 1}`;

    const newCentroid = {
      id,
      lon: lng,
      lat,
      rho,
    };
    centroids.push(newCentroid);

    const marker = L.marker([lat, lng])
      .addTo(map)
      .bindPopup(`Centroid ${id}<br>Rho: ${rho}h`);
    centroidMarkers.push(marker);
  });

  // --- Event Listener for File Input ---
  coordinatesFileInput.addEventListener("change", (event) => {
    const file = event.target.files[0];
    if (!file) {
      uploadedCoordinates = null;
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        // Simple CSV parsing (lon,lat)
        if (file.name.endsWith(".csv")) {
          const lines = e.target.result.split("
          uploadedCoordinates = lines
            .map((line) => {
              const [lon, lat] = line.split(",").map(parseFloat);
              if (!isNaN(lon) && !isNaN(lat)) {
                return { lon, lat };
              }
              return null;
            })
            .filter(Boolean);
        } else {
          // Assume GeoJSON or JSON
          const data = JSON.parse(e.target.result);
          if (data.type === "FeatureCollection") {
            uploadedCoordinates = data.features.map((f) => {
              const [lon, lat] = f.geometry.coordinates;
              return { lon, lat };
            });
          } else {
            // Simple array of {lon, lat}
            uploadedCoordinates = data;
          }
        }
        console.log("Parsed coordinates:", uploadedCoordinates);
      } catch (error) {
        console.error("Error parsing file:", error);
        alert("Failed to parse coordinates file.");
        uploadedCoordinates = null;
      }
    };
    reader.readAsText(file);
  });

  // --- Event Listener for "Compute Isochrones" Button ---
  computeBtn.addEventListener("click", async () => {
    if (centroids.length === 0) {
      alert("Please add at least one centroid by clicking on the map.");
      return;
    }

    const payload = {
      isorequest: {
        centroids: centroids,
        coordinates: uploadedCoordinates,
      },
      options: {
        provider: providerSelect.value,
        // Interval is handled by the backend if null
      },
    };

    try {
      const response = await fetch("http://localhost:8000/isochrones", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "API request failed");
      }

      const result = await response.json();

      // Clear previous isochrones
      clearIsochrones();

      // Add new isochrones to the map
      const geojsonLayer = L.geoJSON(result.polygons_geojson, {
        style: (feature) => ({
          color: "#3388ff",
          weight: 2,
          opacity: 0.8,
          fillColor: "#3388ff",
          fillOpacity: 0.3,
        }),
        onEachFeature: (feature, layer) => {
          layer.bindPopup(
            `Centroid: ${feature.properties.id}<br>Band: ${feature.properties.band_hours}h`
          );
        },
      }).addTo(map);
      isochroneLayers.push(geojsonLayer);

      // Display coverage summary
      if (result.coverage) {
        summaryContent.textContent = JSON.stringify(result.coverage, null, 2);
      } else {
        summaryContent.textContent = "No coordinates provided for coverage analysis.";
      }
    } catch (error) {
      console.error("Error computing isochrones:", error);
      alert(`Error: ${error.message}`);
    }
  });

  // --- Event Listener for "Clear Centroids" Button ---
  clearCentroidsBtn.addEventListener("click", () => {
    centroids = [];
    centroidMarkers.forEach((marker) => marker.remove());
    centroidMarkers = [];
  });

  // --- Event Listener for "Clear Isochrones" Button ---
  const clearIsochrones = () => {
    isochroneLayers.forEach((layer) => layer.remove());
    isochroneLayers = [];
    summaryContent.textContent = "";
  };
  clearIsochronesBtn.addEventListener("click", clearIsochrones);
});

