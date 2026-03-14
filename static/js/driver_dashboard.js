document.addEventListener('DOMContentLoaded', () => {
    // ---- GPS TRACKING ----
    const latLongDisplay = document.getElementById('lat-long-display');
    let watchId = null;

    startTracking();

    function startTracking() {
        if ("geolocation" in navigator) {
            watchId = navigator.geolocation.watchPosition(
                positionSuccess,
                positionError,
                { enableHighAccuracy: true, maximumAge: 0, timeout: 5000 }
            );
        } else {
            alert("Geolocation is not supported by your browser.");
        }
    }

    function positionSuccess(position) {
        const lat = position.coords.latitude;
        const lng = position.coords.longitude;
        
        if (latLongDisplay) {
            latLongDisplay.textContent = `Lat: ${lat.toFixed(5)}, Lng: ${lng.toFixed(5)}`;
        }
        
        // Send to backend
        fetch('/api/location/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ latitude: lat, longitude: lng })
        }).catch(err => console.error("Failed to update location to server:", err));
    }

    function positionError(err) {
        console.warn(`ERROR(${err.code}): ${err.message}`);
        if (latLongDisplay) {
            latLongDisplay.textContent = "Waiting for GPS signal...";
        }
    }
});
