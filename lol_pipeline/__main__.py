import argparse
import sqlite3
import json
import datetime
import logging
import os
from .config import DB_PATH, DEFAULT_LEAGUES, LOG_DIR
from .schema import initialize_db
from .leaguepedia import LeaguepediaClient

def setup_logging():
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    log_file = os.path.join(LOG_DIR, f"pipeline_{datetime.datetime.now().strftime('%Y%m%d')}.log")
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

def run_pipeline(leagues=None, incremental=False):
    setup_logging()
    logging.info("Starting LoL data pipeline (SQLite mode)...")
    initialize_db()
    
    client = LeaguepediaClient()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if not leagues:
        leagues = DEFAULT_LEAGUES

    # Start run audit
    run_start = datetime.datetime.now().isoformat()
    cursor.execute("INSERT INTO pipeline_runs (StartTime, Status) VALUES (?, 'IN_PROGRESS')", (run_start,))
    run_id = cursor.lastrowid
    conn.commit()

    processed_leagues = []

    try:
        for league in leagues:
            logging.info(f"Processing league: {league}")
            
            start_date = None
            if incremental:
                cursor.execute("SELECT LastIngestedDate FROM ingestion_checkpoints WHERE League = ?", (league,))
                checkpoint = cursor.fetchone()
                if checkpoint:
                    start_date = checkpoint[0]
            
            games = client.fetch_games_for_league(league, start_date)
            if not games:
                logging.info(f"No new games found for {league}.")
                continue

            # 1. Store games in raw_game_details
            game_ids = []
            for g in games:
                gid = g['GameId']
                game_ids.append(gid)
                
                # Check if game exists to avoid primary key conflict
                cursor.execute("SELECT 1 FROM raw_game_details WHERE GameId = ?", (gid,))
                exists = cursor.fetchone()
                if exists:
                    continue

                cursor.execute("""
                    INSERT INTO raw_game_details (GameId, MatchId, GameNumber, Winner, Duration, Team1Bans, Team2Bans, Team1Picks, Team2Picks, Side1, Side2)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    gid, g['MatchId'], 0, g['WinTeam'], str(g['Duration']), 
                    g['Team1Bans'] if g['Team1Bans'] else "", 
                    g['Team2Bans'] if g['Team2Bans'] else "", 
                    g['Team1Picks'] if g['Team1Picks'] else "", 
                    g['Team2Picks'] if g['Team2Picks'] else "", 
                    g['Team1Side'], g['Team2Side']
                ))

                # Also insert into raw_matches
                cursor.execute("SELECT 1 FROM raw_matches WHERE MatchId = ?", (g['MatchId'],))
                match_exists = cursor.fetchone()
                if not match_exists:
                    cursor.execute("""
                        INSERT INTO raw_matches (MatchId, League, Tournament, Date, Team1, Team2, Team1Score, Team2Score, Winner, BestOf, Patch)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        g['MatchId'], league, g['Tournament'], g['DateTime UTC'], 
                        g['Team1'], g['Team2'], 0, 0, g['WinTeam'], 0, g['Patch']
                    ))

            # 2. Fetch and store player stats
            logging.info(f"Fetching player stats for {len(game_ids)} games...")
            player_stats = client.fetch_player_stats(game_ids)
            for ps in player_stats:
                cursor.execute("SELECT 1 FROM raw_player_game_stats WHERE GameId = ? AND PlayerName = ?", (ps['GameId'], ps['Name']))
                exists = cursor.fetchone()
                if exists:
                    continue
                    
                cursor.execute("""
                    INSERT INTO raw_player_game_stats (GameId, PlayerName, TeamName, Champion, Role, Kills, Deaths, Assists, Gold, CS, DamageToChampions, VisionScore)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ps['GameId'], ps['Name'], ps['Team'], ps['Champion'], ps['Role'],
                    int(ps['Kills']) if ps['Kills'] else 0, 
                    int(ps['Deaths']) if ps['Deaths'] else 0, 
                    int(ps['Assists']) if ps['Assists'] else 0,
                    int(ps['Gold']) if ps['Gold'] else 0,
                    int(ps['CS']) if ps['CS'] else 0,
                    int(ps['DamageToChampions']) if ps['DamageToChampions'] else 0,
                    int(ps['VisionScore']) if ps['VisionScore'] else 0
                ))

            # 3. Update checkpoint
            latest_date = max([g['DateTime UTC'] for g in games])
            cursor.execute("INSERT OR REPLACE INTO ingestion_checkpoints (League, LastIngestedDate) VALUES (?, ?)", (league, latest_date))
            
            processed_leagues.append(league)
            logging.info(f"Successfully processed {league}.")
            conn.commit()

        # End run audit
        cursor.execute("UPDATE pipeline_runs SET EndTime = ?, Status = 'SUCCESS', LeaguesProcessed = ? WHERE RunId = ?", (datetime.datetime.now().isoformat(), json.dumps(processed_leagues), run_id))
        conn.commit()

    except Exception as e:
        logging.error(f"Pipeline failed: {str(e)}")
        if run_id:
            cursor.execute("UPDATE pipeline_runs SET EndTime = ?, Status = 'FAILED', ErrorMessage = ? WHERE RunId = ?", (datetime.datetime.now().isoformat(), str(e), run_id))
            conn.commit()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LoL Pro Match Data Pipeline")
    parser.add_argument("--incremental", action="store_true", help="Only fetch new data")
    parser.add_argument("--league", type=str, help="Fetch data for a specific league")
    args = parser.parse_args()

    leagues = [args.league] if args.league else DEFAULT_LEAGUES
    run_pipeline(leagues=leagues, incremental=args.incremental)
