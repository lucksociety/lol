import duckdb
import os
from lol_pipeline.config import DB_PATH

def validate():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file not found at {DB_PATH}")
        return

    conn = duckdb.connect(DB_PATH)
    
    print("--- Ingestion Statistics ---")
    tables = ["raw_matches", "raw_game_details", "raw_player_game_stats", "ingestion_checkpoints"]
    for table in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table:25}: {count} rows")

    print("\n--- Latest Matches Sample ---")
    sample = conn.execute("SELECT Date, Tournament, Team1, Team2, Winner FROM raw_matches ORDER BY Date DESC LIMIT 5").fetchall()
    for row in sample:
        print(row)

    print("\n--- Checkpoints ---")
    checkpoints = conn.execute("SELECT League, LastIngestedDate FROM ingestion_checkpoints").fetchall()
    for cp in checkpoints:
        print(f"{cp[0]}: {cp[1]}")

    conn.close()

if __name__ == "__main__":
    validate()
