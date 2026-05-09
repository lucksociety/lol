import sqlite3
import os
from .config import DB_PATH

def initialize_db():
    # Ensure data directory exists
    db_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Table for matches (series)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS raw_matches (
            MatchId TEXT PRIMARY KEY,
            League TEXT,
            Tournament TEXT,
            Date TEXT,
            Team1 TEXT,
            Team2 TEXT,
            Team1Score INTEGER,
            Team2Score INTEGER,
            Winner TEXT,
            BestOf INTEGER,
            Patch TEXT
        )
    """)

    # Table for individual games
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS raw_game_details (
            GameId TEXT PRIMARY KEY,
            MatchId TEXT,
            GameNumber INTEGER,
            Winner TEXT,
            Duration TEXT,
            Team1Bans TEXT,
            Team2Bans TEXT,
            Team1Picks TEXT,
            Team2Picks TEXT,
            Side1 TEXT,
            Side2 TEXT
        )
    """)

    # Table for player stats in each game
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS raw_player_game_stats (
            GameId TEXT,
            PlayerName TEXT,
            TeamName TEXT,
            Champion TEXT,
            Role TEXT,
            Kills INTEGER,
            Deaths INTEGER,
            Assists INTEGER,
            Gold INTEGER,
            CS INTEGER,
            DamageToChampions INTEGER,
            VisionScore INTEGER,
            PRIMARY KEY (GameId, PlayerName)
        )
    """)

    # Table for rosters
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS raw_rosters (
            Tournament TEXT,
            TeamName TEXT,
            PlayerName TEXT,
            Role TEXT,
            PRIMARY KEY (Tournament, TeamName, PlayerName)
        )
    """)

    # Table for Riot API timelines (simplified for SQLite)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS raw_timelines (
            GameId TEXT,
            Minute INTEGER,
            Team1Gold INTEGER,
            Team2Gold INTEGER,
            Team1XP INTEGER,
            Team2XP INTEGER,
            Events TEXT,
            PRIMARY KEY (GameId, Minute)
        )
    """)

    # Ingestion checkpoints for incremental runs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ingestion_checkpoints (
            League TEXT PRIMARY KEY,
            LastIngestedDate TEXT
        )
    """)

    # Audit log for pipeline runs (simplified RunId)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_runs (
            RunId INTEGER PRIMARY KEY AUTOINCREMENT,
            StartTime TEXT,
            EndTime TEXT,
            LeaguesProcessed TEXT,
            Status TEXT,
            ErrorMessage TEXT
        )
    """)
    
    conn.commit()
    conn.close()
