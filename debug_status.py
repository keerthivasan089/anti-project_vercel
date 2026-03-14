import requests

def test_status():
    try:
        url = "http://127.0.0.1:5000/api/check_status?roll=REG123"
        print(f"Testing {url}...")
        resp = requests.get(url)
        print(f"Status Code: {resp.status_code}")
        print(f"Response: {resp.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_status()
