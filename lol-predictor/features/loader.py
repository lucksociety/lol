import pandas as pd
from sqlalchemy import create_engine
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "lol_predictions.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

def load_raw_matches() -> pd.DataFrame:
    engine = create_engine(DATABASE_URL)
    query = """
    SELECT m.match_id, m.game_version, m.game_duration, m.game_creation,
           t.team_id, t.win, t.first_blood, t.first_tower, t.first_dragon, t.first_baron
    FROM matches m
    JOIN teams t ON m.match_id = t.match_id
    """
    try:
        df = pd.read_sql(query, engine)
        df['patch'] = df['game_version'].apply(lambda x: '.'.join(str(x).split('.')[:2]) if pd.notnull(x) else '0.0')
        return df
    except Exception as e:
        print(f"Error loading matches: {e}")
        return pd.DataFrame()

def load_participants() -> pd.DataFrame:
    engine = create_engine(DATABASE_URL)
    query = """
    SELECT match_id, puuid, summoner_name, team_id, champion_id, champion_name, 
           team_position, kills, deaths, assists, gold_earned, vision_score, win
    FROM participants
    """
    try:
        return pd.read_sql(query, engine)
    except Exception as e:
        print(f"Error loading participants: {e}")
        return pd.DataFrame()
