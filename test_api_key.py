import urllib.request
import os

def load_env_key():
    env_path = ".env"
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if line.startswith("RIOT_API_KEY="):
                    return line.strip().split("=")[1]
    return os.environ.get("RIOT_API_KEY")

api_key = load_env_key()
if not api_key:
    print("API Key not found in .env or environment")
    exit(1)

# Test with NA1 status
url = "https://na1.api.riotgames.com/lol/status/v4/platform-data"
headers = {"X-Riot-Token": api_key}

try:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as response:
        print(f"Status Code: {response.getcode()}")
        print("API Key is VALID")
except Exception as e:
    print(f"Error: {e}")
    print("API Key might be INVALID or rate limited")
