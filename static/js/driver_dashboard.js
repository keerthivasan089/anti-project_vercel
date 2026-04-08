let watchId = null;
let wakeLock = null;
let latLongDisplay = document.getElementById('lat-long-display');

document.addEventListener('DOMContentLoaded', () => {
    requestWakeLock();
    startTracking();
    
    // Start Trip API on load to init geofencing
    fetch('/api/trip/start', { method: 'POST' }).catch(() => {});
});

async function requestWakeLock() {
    try {
        if ('wakeLock' in navigator) {
            wakeLock = await navigator.wakeLock.request('screen');
            console.log('Screen Wake Lock is active for background GPS tracking.');
            wakeLock.addEventListener('release', () => {
                console.log('Screen Wake Lock was released');
                // Could retry requesting it here if visibility changes back
            });
            
            document.addEventListener('visibilitychange', async () => {
                if (wakeLock !== null && document.visibilityState === 'visible') {
                    wakeLock = await navigator.wakeLock.request('screen');
                }
            });
        }
    } catch (err) {
        console.error(`Wake Lock error: ${err.name}, ${err.message}`);
    }
}

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
    
    // 1. Send location update for tracking
    fetch('/api/location/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ latitude: lat, longitude: lng })
    }).catch(err => console.error("Failed to update location:", err));

    // 2. Check geofence for auto-trip complete
    checkGeofence(lat, lng);
}

function positionError(err) {
    console.warn(`ERROR(${err.code}): ${err.message}`);
    if (latLongDisplay) {
        latLongDisplay.textContent = "Waiting for GPS signal...";
    }
}

function checkGeofence(lat, lng) {
    fetch('/api/geofence/check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ latitude: lat, longitude: lng })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success && data.arrived) {
            // Show Trip Complete Banner
            const banner = document.getElementById('trip-complete-banner');
            if (banner && !banner.classList.contains('show')) {
                banner.classList.add('show');
                // Stop tracking slightly after arrival
                setTimeout(() => {
                    if (watchId) navigator.geolocation.clearWatch(watchId);
                }, 10000);
            }
        }
    }).catch(() => {});
}

// ============== SOS / EMERGENCY LOGIC ============== //
let mediaRecorder = null, audioChunks = [], recordingTimer = null, recordingSeconds = 0;
let voiceNoteB64 = null, voiceNoteType = 'audio/webm';

window.openSOSModal = function() { document.getElementById('sosModal').classList.add('show'); }
window.closeSOSModal = function() {
    document.getElementById('sosModal').classList.remove('show');
    if (mediaRecorder && mediaRecorder.state === 'recording') window.stopRecording();
    resetRecorder();
}

function resetRecorder() {
    voiceNoteB64 = null;
    recordingSeconds = 0;
    clearInterval(recordingTimer);
    document.getElementById('recorder-timer').style.display = 'none';
    document.getElementById('recorder-waveform').style.display = 'none';
    document.getElementById('rec-start-btn').style.display = '';
    document.getElementById('rec-stop-btn').classList.remove('show');
    const preview = document.getElementById('audio-preview');
    preview.style.display = 'none';
    preview.src = '';
}

window.startRecording = function() {
    navigator.mediaDevices.getUserMedia({ audio: true })
    .then(stream => {
        audioChunks = [];
        mediaRecorder = new MediaRecorder(stream);
        mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
        mediaRecorder.onstop = () => {
            const blob = new Blob(audioChunks, { type: voiceNoteType });
            const reader = new FileReader();
            reader.onload = () => { voiceNoteB64 = reader.result.split(',')[1]; };
            reader.readAsDataURL(blob);
            const url = URL.createObjectURL(blob);
            const preview = document.getElementById('audio-preview');
            preview.src = url;
            preview.style.display = 'block';
            stream.getTracks().forEach(t => t.stop());
        };
        mediaRecorder.start();

        document.getElementById('rec-start-btn').style.display = 'none';
        document.getElementById('rec-stop-btn').classList.add('show');
        document.getElementById('recorder-waveform').style.display = 'flex';
        document.getElementById('recorder-timer').style.display = 'block';
        recordingSeconds = 0;

        recordingTimer = setInterval(() => {
            recordingSeconds++;
            const m = Math.floor(recordingSeconds / 60);
            const s = recordingSeconds % 60;
            document.getElementById('recorder-timer').textContent = `${m}:${s.toString().padStart(2,'0')}`;
            if (recordingSeconds >= 60) window.stopRecording();
        }, 1000);
    })
    .catch(() => {
        document.getElementById('sos-error').textContent = '🎙️ Microphone access denied.';
        document.getElementById('sos-error').style.display = 'block';
    });
}

window.stopRecording = function() {
    clearInterval(recordingTimer);
    if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop();
    document.getElementById('recorder-waveform').style.display = 'none';
    document.getElementById('rec-stop-btn').classList.remove('show');
}

window.submitSOS = async function() {
    const description = document.getElementById('sos-description').value.trim();
    const problemType = document.getElementById('sos-problem-type').value;

    if (!problemType) {
        document.getElementById('sos-error').textContent = 'Please select a problem type.';
        document.getElementById('sos-error').style.display = 'block';
        return;
    }

    if (!description && !voiceNoteB64) {
        document.getElementById('sos-error').textContent = 'Please describe the issue or record a voice note.';
        document.getElementById('sos-error').style.display = 'block';
        return;
    }
    
    document.getElementById('sos-error').style.display = 'none';
    const btn = document.getElementById('sos-submit-btn');
    btn.disabled = true;
    btn.textContent = 'Sending...';

    const payload = {
        problem_type: problemType,
        description,
        voice_note_b64: voiceNoteB64,
        voice_note_type: voiceNoteType
    };

    try {
        const res  = await fetch('/api/emergency/alert', { 
            method: 'POST', 
            headers: {'Content-Type': 'application/json'}, 
            body: JSON.stringify(payload) 
        });
        const data = await res.json();

        if (data.success) {
            window.closeSOSModal();
            btn.disabled = false;
            btn.textContent = '🚨 Send Alert';
            document.getElementById('sos-description').value = '';
            document.getElementById('sos-problem-type').value = '';
            resetRecorder();
            alert('Emergency alert sent to Admin. If this is a breakdown/accident, the bus tracking session has been paused.');
        }
    } catch(e) {
        btn.disabled = false;
        btn.textContent = '🚨 Send Alert';
    }
}
