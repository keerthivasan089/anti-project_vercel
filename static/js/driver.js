document.addEventListener('DOMContentLoaded', () => {
    // ---- DRIVER AUTHENTICATION ----
    const loginForm = document.getElementById('login-form');
    const otpForm = document.getElementById('otp-form');
    
    const loginSection = document.getElementById('login-section');
    const otpSection = document.getElementById('otp-section');
    const trackingSection = document.getElementById('tracking-section');
    
    const loginError = document.getElementById('login-error');
    const otpError = document.getElementById('otp-error');
    const latLongDisplay = document.getElementById('lat-long-display');

    let watchId = null;

    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const busNumber = document.getElementById('bus-number').value.trim();
            const driverPhone = document.getElementById('phone-number').value.trim();
            
            try {
                const res = await fetch('/api/driver/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ bus_id: busNumber, driver_phone: driverPhone })
                });
                const data = await res.json();
                
                if (data.success) {
                    loginSection.classList.add('hidden');
                    otpSection.classList.remove('hidden');
                    loginError.style.display = 'none';
                } else {
                    loginError.textContent = data.message;
                    loginError.style.display = 'block';
                }
            } catch (err) {
                loginError.textContent = 'Network error. Please try again.';
                loginError.style.display = 'block';
            }
        });
    }

    if (otpForm) {
        otpForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const otpCode = document.getElementById('otp-code').value.trim();
            
            try {
                const res = await fetch('/api/driver/verify_otp', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ otp: otpCode })
                });
                const data = await res.json();
                
                if (data.success) {
                    otpSection.classList.add('hidden');
                    trackingSection.classList.remove('hidden');
                    otpError.style.display = 'none';
                    
                    // Start GPS Tracking
                    startTracking();
                } else {
                    otpError.textContent = data.message;
                    otpError.style.display = 'block';
                }
            } catch (err) {
                otpError.textContent = 'Network error. Please try again.';
                otpError.style.display = 'block';
            }
        });
    }

    // ---- GPS TRACKING ----
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
        
        latLongDisplay.textContent = `Lat: ${lat.toFixed(5)}, Lng: ${lng.toFixed(5)}`;
        
        // Send to backend
        fetch('/api/location/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ latitude: lat, longitude: lng })
        }).catch(err => console.error("Failed to update location to server:", err));
    }

    function positionError(err) {
        console.warn(`ERROR(${err.code}): ${err.message}`);
        latLongDisplay.textContent = "Waiting for GPS signal...";
    }
});
