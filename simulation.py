import threading
import time
import random
from models import BusModel

# Dummy coordinates around a general city area for simulation
PATHS = {
    1: [(12.717849, 77.869604), (12.588317, 77.652120)],  # College ↔ Thalli
    2: [(12.717849, 77.869604), (12.666957, 78.014787)],  # College ↔ Shoolagiri
    3: [(12.717849, 77.869604), (12.806014, 77.969881)],  # College ↔ Berigai
    4: [(12.717849, 77.869604), (12.830309, 77.862998)],  # College ↔ Bagalur
    5: [(12.717849, 77.869604), (12.7560, 77.8365)],      # College ↔ Mathigiri
    6: [(12.717849, 77.869604), (12.7384, 77.8439)],      # College ↔ SIPCOT
    7: [(12.717849, 77.869604), (12.735158, 77.827399)],  # College ↔ Hosur Bus Stand
    8: [(12.717849, 77.869604), (12.718342, 77.822977)],  # College ↔ Hosur Railway
    9: [(12.717849, 77.869604), (12.717849, 77.869604)]   # College (static)
}


def simulate_buses():
    """
    Background thread that simulates buses moving along paths.
    """

    progress = {}  # track each bus movement index

    while True:
        buses = BusModel.get_all_buses()

        for bus in buses:
            bus_id = bus['id']

            # simulate only if path exists
            if bus_id in PATHS:
                path = PATHS[bus_id]

                # initialize progress for new bus
                if bus_id not in progress:
                    progress[bus_id] = 0

                idx = progress[bus_id]

                lat, lng = path[idx]

                # add small random movement for realism
                jitter_lat = random.uniform(-0.0001, 0.0001)
                jitter_lng = random.uniform(-0.0001, 0.0001)

                BusModel.update_location(
                    bus_id,
                    lat + jitter_lat,
                    lng + jitter_lng,
                    is_simulation=True
                )

                # move to next coordinate
                progress[bus_id] = (idx + 1) % len(path)

        # update every 5 seconds
        time.sleep(5)


def start_simulation():
    """
    Starts the simulation thread
    """
    thread = threading.Thread(target=simulate_buses, daemon=True)
    thread.start()
    print("🚌 Bus simulation started successfully.")