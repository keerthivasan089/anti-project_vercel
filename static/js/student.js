document.addEventListener('DOMContentLoaded', () => {
    // ---- INITIALIZE LEAFLET MAP ----
    // Set view to Adhiyamaan College
    const map = L.map('map').setView([12.717849, 77.869604], 13);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
        maxZoom: 19
    }).addTo(map);

    // Custom Icons setup
    const busIcon = L.icon({
        iconUrl: 'https://cdn-icons-png.flaticon.com/512/3448/3448339.png',
        iconSize: [38, 38],
        iconAnchor: [19, 38],
        popupAnchor: [0, -38]
    });

    const stopIcon = L.icon({
        iconUrl: 'https://cdn-icons-png.flaticon.com/512/684/684908.png',
        iconSize: [30, 30],
        iconAnchor: [15, 30],
        popupAnchor: [0, -30]
    });

    // We will keep track of active bus markers here
    let busMarkers = {};

    // Base mock coordinates for buses to travel on (Looping)
    const route1_points = [
        [12.7416, 77.8252], // Hosur Bus Stand
        [12.7300, 77.8200], // Bagalur Road (via)
        [12.717849, 77.869604]  // Adhiyamaan
    ];
    
    const route2_points = [
        [12.7540, 77.8350], // Mathigiri
        [12.7425, 77.8231], // random via
        [12.717849, 77.869604]  // Adhiyamaan
    ];

    const route3_points = [
        [12.7365, 77.8450], // SIPCOT
        [12.7500, 77.8200], // Railway Station
        [12.717849, 77.869604]  // Adhiyamaan
    ];

    // Native OSRM Fetch to snap lines without breaking markers
    async function drawSnappedRoute(points, color) {
        try {
            // we will build a coordinates string for OSRM: lng1,lat1;lng2,lat2;...
            const coordsString = points.map(p => `${p[1]},${p[0]}`).join(';');
            const url = `https://router.project-osrm.org/route/v1/driving/${coordsString}?overview=full&geometries=geojson`;
            
            const res = await fetch(url);
            const data = await res.json();
            
            if (data.routes && data.routes.length > 0) {
                const geojson = data.routes[0].geometry;
                
                // GeoJSON uses [lng, lat], Leaflet wants [lat, lng]
                const latLngs = geojson.coordinates.map(coord => [coord[1], coord[0]]);
                
                L.polyline(latLngs, { color: color, weight: 4, opacity: 0.6 }).addTo(map);
            } else {
                L.polyline(points, { color: color, weight: 4, opacity: 0.6 }).addTo(map);
            }
        } catch (err) {
            console.error("OSRM Route Fetch Error:", err);
            L.polyline(points, { color: color, weight: 4, opacity: 0.6 }).addTo(map);
        }
    }

    drawSnappedRoute(route1_points, 'blue');
    drawSnappedRoute(route2_points, 'red');
    drawSnappedRoute(route3_points, 'green');

    // Plot Stops
    // Reading data embedded manually or we could fetch JSON API as well.
    // For now we'll plot them right away with fixed data for demo
    const stopsData = [
        { name: 'Hosur Bus Stand', lat: 12.7416, lng: 77.8252 },
        { name: 'Mathigiri', lat: 12.7540, lng: 77.8350 },
        { name: 'SIPCOT', lat: 12.7365, lng: 77.8450 },
        { name: 'Bagalur Road', lat: 12.7300, lng: 77.8200 },
        { name: 'Railway Station', lat: 12.7500, lng: 77.8200 },
        { name: 'Adhiyamaan College of Engineering', lat: 12.717849, lng: 77.869604 }
    ];

    stopsData.forEach(stop => {
        L.marker([stop.lat, stop.lng], {icon: stopIcon})
            .bindPopup(`<b>${stop.name}</b>`)
            .addTo(map);
    });

    // ---- LIVE BUS TRACKING ----
    async function fetchBusLocations() {
        try {
            const res = await fetch('/api/buses');
            const data = await res.json();
            
            // Loop through live locations
            data.buses.forEach(bus => {
                const { bus_number, latitude, longitude, driver_name } = bus;
                
                if (busMarkers[bus_number]) {
                    // Update existing marker position smoothly
                    busMarkers[bus_number].setLatLng([latitude, longitude]);
                } else {
                    // Create new marker
                    const marker = L.marker([latitude, longitude], { icon: busIcon })
                        .bindPopup(`<b>${bus_number}</b><br>Driver: ${driver_name}`)
                        .addTo(map);
                    busMarkers[bus_number] = marker;
                }
            });
        } catch (err) {
            console.error('Error fetching bus locations:', err);
        }
    }

    // Fetch immediately and set interval
    fetchBusLocations();
    setInterval(fetchBusLocations, 3000); // every 3 seconds

    // ---- ETA CALCULATION ----
    const calculateBtn = document.getElementById('calculate-eta-btn');
    const stopSelect = document.getElementById('stop-select');
    const etaContainer = document.getElementById('eta-container');
    const etaResults = document.getElementById('eta-results');
    const etaStopName = document.getElementById('eta-stop-name');

    calculateBtn.addEventListener('click', async () => {
        const stopId = stopSelect.value;
        if (!stopId) {
            alert('Please select a bus stop first.');
            return;
        }

        try {
            const res = await fetch(`/api/eta?stop_id=${stopId}`);
            const data = await res.json();

            if (data.success) {
                etaContainer.classList.remove('hidden');
                etaStopName.textContent = `Arriving at: ${data.stop_name}`;
                
                etaResults.innerHTML = ''; // clear previous
                
                if (data.etas.length === 0) {
                    etaResults.innerHTML = `<div class="eta-card"><p>No active buses found.</p></div>`;
                    return;
                }

                data.etas.forEach(eta => {
                    const card = document.createElement('div');
                    card.className = 'eta-card';
                    card.innerHTML = `
                        <div class="bus-info">
                            <span class="bus-id">${eta.bus_number}</span>
                            <div class="distance">${eta.distance_km} km away</div>
                        </div>
                        <div class="eta-time">${eta.eta_minutes} min</div>
                    `;
                    etaResults.appendChild(card);
                });
            } else {
                alert(data.message || 'Failed to calculate ETA.');
            }
        } catch (err) {
            console.error('Error calculating ETA:', err);
            alert('Error connecting to tracking server.');
        }
    });
});
