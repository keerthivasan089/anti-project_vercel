import math

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Radius of earth in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = math.sin(dlat / 2) * math.sin(dlat / 2) + \
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
        math.sin(dlon / 2) * math.sin(dlon / 2)
        
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    return distance

def calculate_eta(distance, speed_kmh=40):
    """
    Calculate ETA given distance in km and average speed in km/h.
    Returns ETA in minutes.
    """
    if speed_kmh <= 0: return 0
    time_hours = distance / speed_kmh
    time_minutes = time_hours * 60
    return round(time_minutes)
