import os

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "lol_predictions.db")
LOG_DIR = os.path.join(BASE_DIR, "logs")

# Leaguepedia API
LEAGUEPEDIA_DOMAIN = "lol.fandom.com"

# Default leagues to fetch (2023-2024 seasons)
DEFAULT_LEAGUES = [
    "LCK/2023 Season/Spring Season", "LCK/2023 Season/Spring Play-offs",
    "LCK/2023 Season/Summer Season", "LCK/2023 Season/Summer Play-offs",
    "LCK/2024 Season/Spring Season", "LCK/2024 Season/Spring Play-offs",
    "LCK/2024 Season/Summer Season",
    "LPL/2023 Season/Spring Season", "LPL/2023 Season/Spring Play-offs",
    "LPL/2023 Season/Summer Season", "LPL/2023 Season/Summer Play-offs",
    "LPL/2024 Season/Spring Season", "LPL/2024 Season/Spring Play-offs",
    "LEC/2023 Season/Winter Season", "LEC/2023 Season/Spring Season", "LEC/2023 Season/Summer Season", "LEC/2023 Season/Finals",
    "LEC/2024 Season/Winter Season", "LEC/2024 Season/Spring Season", "LEC/2024 Season/Summer Season",
    "LCS/2023 Season/Spring Season", "LCS/2023 Season/Spring Play-offs",
    "LCS/2023 Season/Summer Season", "LCS/2023 Season/Championship",
    "LCS/2024 Season/Spring Season", "LCS/2024 Season/Spring Play-offs",
    "LCS/2024 Season/Summer Season",
]

# Riot API (Optional)
def load_env_key():
    env_path = os.path.join(BASE_DIR, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if line.startswith("RIOT_API_KEY="):
                    return line.strip().split("=")[1]
    return os.environ.get("RIOT_API_KEY")

RIOT_API_KEY = load_env_key()
