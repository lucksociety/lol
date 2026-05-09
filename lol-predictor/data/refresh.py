import argparse
import json
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from schema import Base, Match, Participant, Team, TournamentMatch
from riot_api import RiotAPIClient
from leaguepedia import LeaguepediaClient
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "lol_predictions.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def fetch_and_store_riot_match(match_id: str, riot_client: RiotAPIClient, session):
    existing = session.query(Match).filter_by(match_id=match_id).first()
    if existing:
        print(f"Match {match_id} already exists.")
        return
        
    print(f"Fetching match {match_id}...")
    try:
        match_data = riot_client.get_match_by_id(match_id)
    except Exception as e:
        print(f"Error fetching match {match_id}: {e}")
        return

    info = match_data['info']
    metadata = match_data['metadata']

    db_match = Match(
        match_id=match_id,
        platform_id=info.get('platformId', ''),
        game_creation=datetime.fromtimestamp(info.get('gameCreation', 0) / 1000.0),
        game_duration=info.get('gameDuration', 0),
        game_version=info.get('gameVersion', ''),
        map_id=info.get('mapId', 0),
        game_mode=info.get('gameMode', ''),
        game_type=info.get('gameType', ''),
        queue_id=info.get('queueId', 0)
    )
    session.add(db_match)

    for p in info.get('participants', []):
        db_participant = Participant(
            match_id=match_id,
            puuid=p.get('puuid', ''),
            summoner_id=p.get('summonerId', ''),
            summoner_name=p.get('summonerName', ''),
            team_id=p.get('teamId', 0),
            champion_id=p.get('championId', 0),
            champion_name=p.get('championName', ''),
            team_position=p.get('teamPosition', ''),
            summoner1_id=p.get('summoner1Id', 0),
            summoner2_id=p.get('summoner2Id', 0),
            perks=p.get('perks', {}),
            kills=p.get('kills', 0),
            deaths=p.get('deaths', 0),
            assists=p.get('assists', 0),
            gold_earned=p.get('goldEarned', 0),
            total_minions_killed=p.get('totalMinionsKilled', 0),
            neutral_minions_killed=p.get('neutralMinionsKilled', 0),
            vision_score=p.get('visionScore', 0),
            win=p.get('win', False)
        )
        session.add(db_participant)

    for t in info.get('teams', []):
        obj = t.get('objectives', {})
        db_team = Team(
            match_id=match_id,
            team_id=t.get('teamId', 0),
            win=t.get('win', False),
            baron_kills=obj.get('baron', {}).get('kills', 0),
            champion_kills=obj.get('champion', {}).get('kills', 0),
            dragon_kills=obj.get('dragon', {}).get('kills', 0),
            inhibitor_kills=obj.get('inhibitor', {}).get('kills', 0),
            tower_kills=obj.get('tower', {}).get('kills', 0),
            first_blood=obj.get('champion', {}).get('first', False),
            first_tower=obj.get('tower', {}).get('first', False),
            first_baron=obj.get('baron', {}).get('first', False),
            first_dragon=obj.get('dragon', {}).get('first', False),
            bans=[b.get('championId') for b in t.get('bans', [])]
        )
        session.add(db_team)

    session.commit()

def fetch_and_store_leaguepedia(tournament: str, limit: int, session):
    lp_client = LeaguepediaClient()
    print(f"Fetching {limit} games for {tournament}...")
    games = lp_client.fetch_recent_games(tournament=tournament, limit=limit)
    for g in games:
        game_id = g.get('GameId')
        existing = session.query(TournamentMatch).filter_by(game_id=game_id).first()
        if not existing:
            dt_str = g.get('DateTime UTC')
            try:
                dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S') if dt_str else datetime.utcnow()
            except ValueError:
                dt = datetime.utcnow()
            
            db_tourney = TournamentMatch(
                game_id=game_id,
                match_id=g.get('MatchId', ''),
                tournament=g.get('Tournament', ''),
                date_time_utc=dt,
                team1=g.get('Team1', ''),
                team2=g.get('Team2', ''),
                win_team=g.get('WinTeam', ''),
                duration=g.get('Duration', ''),
                patch=g.get('Patch', ''),
                team1_picks=g.get('Team1Picks', ''),
                team2_picks=g.get('Team2Picks', '')
            )
            session.add(db_tourney)
    session.commit()
    print(f"Stored {len(games)} pro games.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--puuid", type=str, help="Seed PUUID to fetch matches for (Riot API)")
    parser.add_argument("--count", type=int, default=10, help="Number of matches to fetch")
    parser.add_argument("--tournament", type=str, help="Leaguepedia tournament to fetch (e.g. 'LCK 2024')")
    args = parser.parse_args()

    session = SessionLocal()

    if args.puuid:
        riot_client = RiotAPIClient()
        match_ids = riot_client.get_match_ids_by_puuid(args.puuid, count=args.count)
        print(f"Found {len(match_ids)} matches for PUUID {args.puuid}")
        for mid in match_ids:
            fetch_and_store_riot_match(mid, riot_client, session)

    if args.tournament:
        fetch_and_store_leaguepedia(args.tournament, args.count, session)
        
    session.close()
