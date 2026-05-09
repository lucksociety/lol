import sqlite3
import json
import os
from lol_pipeline.config import DB_PATH
from lol_pipeline.schema import initialize_db

def seed_database():
    initialize_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Seed some LPL 2026 Split 1 data from our research
    # We'll mock the Match and Game IDs for the demonstration
    lpl_data = [
        ("LPL26S1_GF", "LPL/2026 Season/Split 1", "Split 1 Playoffs", "2026-03-08T18:00:00", "Bilibili Gaming", "JD Gaming", 3, 1, "Bilibili Gaming", 5, "16.4"),
        ("LPL26S1_LBSF", "LPL/2026 Season/Split 1", "Split 1 Playoffs", "2026-03-05T18:00:00", "Weibo Gaming", "Anyone's Legend", 3, 2, "Weibo Gaming", 5, "16.4"),
        ("LPL26S1_UBF", "LPL/2026 Season/Split 1", "Split 1 Playoffs", "2026-03-04T18:00:00", "Bilibili Gaming", "JD Gaming", 3, 0, "Bilibili Gaming", 5, "16.4"),
    ]

    for match in lpl_data:
        cursor.execute("""
            INSERT OR REPLACE INTO raw_matches (MatchId, League, Tournament, Date, Team1, Team2, Team1Score, Team2Score, Winner, BestOf, Patch)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, match)

    # Seed some team stats (we can put these in a custom table or use the existing ones)
    # For now, let's just mark the ingestion as complete for this league
    cursor.execute("INSERT OR REPLACE INTO ingestion_checkpoints (League, LastIngestedDate) VALUES (?, ?)", ("LPL/2026 Season/Split 1", "2026-03-08T23:59:59"))

    conn.commit()
    conn.close()
    print("Database seeded with LPL 2026 Split 1 research data.")

if __name__ == "__main__":
    seed_database()
