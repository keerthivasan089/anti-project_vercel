import math
import requests as req

def haversine(lat1, lon1, lat2, lon2):
    """Straight-line distance in km via Haversine formula."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def calculate_eta(distance, speed_kmh=40):
    """ETA in minutes given distance (km)."""
    if speed_kmh <= 0: return 0
    return round((distance / speed_kmh) * 60)

def get_road_eta(origin_lat, origin_lng, dest_lat, dest_lng):
    """
    Road-based ETA via free OSRM API.
    Returns dict: { 'distance_km': float, 'eta_minutes': int, 'via_road': True }
    Falls back to Haversine if OSRM is unreachable.
    """
    try:
        coords = f"{origin_lng},{origin_lat};{dest_lng},{dest_lat}"
        url = f"https://router.project-osrm.org/route/v1/driving/{coords}?overview=false"
        response = req.get(url, timeout=4)
        data = response.json()
        if data.get('code') == 'Ok' and data.get('routes'):
            route = data['routes'][0]
            dist_km = round(route['distance'] / 1000, 2)
            # 'duration' is in seconds (OSRM's estimated travel time)
            eta_mins = round(route['duration'] / 60)
            return {'distance_km': dist_km, 'eta_minutes': eta_mins, 'via_road': True}
    except Exception as e:
        print(f"⚠️ OSRM fallback to Haversine: {e}")

    # Fallback
    dist = haversine(origin_lat, origin_lng, dest_lat, dest_lng)
    return {
        'distance_km': round(dist, 2),
        'eta_minutes': calculate_eta(dist),
        'via_road': False
    }

def meters_between(lat1, lon1, lat2, lon2):
    """Distance in meters between two lat/lng points."""
    return haversine(lat1, lon1, lat2, lon2) * 1000
