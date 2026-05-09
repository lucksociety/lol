from typing import Optional, List
from datetime import datetime
from sqlalchemy import String, Integer, Float, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class Match(Base):
    __tablename__ = "matches"
    
    match_id: Mapped[str] = mapped_column(String, primary_key=True)
    platform_id: Mapped[str] = mapped_column(String)
    game_creation: Mapped[datetime] = mapped_column(DateTime)
    game_duration: Mapped[int] = mapped_column(Integer)
    game_version: Mapped[str] = mapped_column(String)
    map_id: Mapped[int] = mapped_column(Integer)
    game_mode: Mapped[str] = mapped_column(String)
    game_type: Mapped[str] = mapped_column(String)
    queue_id: Mapped[int] = mapped_column(Integer)
    
    participants: Mapped[List["Participant"]] = relationship(back_populates="match")
    teams: Mapped[List["Team"]] = relationship(back_populates="match")

class Participant(Base):
    __tablename__ = "participants"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[str] = mapped_column(ForeignKey("matches.match_id"))
    puuid: Mapped[str] = mapped_column(String, index=True)
    summoner_id: Mapped[Optional[str]] = mapped_column(String)
    summoner_name: Mapped[Optional[str]] = mapped_column(String)
    team_id: Mapped[int] = mapped_column(Integer)
    champion_id: Mapped[int] = mapped_column(Integer)
    champion_name: Mapped[str] = mapped_column(String)
    team_position: Mapped[str] = mapped_column(String)
    
    # Pre-game choices
    summoner1_id: Mapped[int] = mapped_column(Integer)
    summoner2_id: Mapped[int] = mapped_column(Integer)
    perks: Mapped[dict] = mapped_column(JSON)
    
    # In-game stats
    kills: Mapped[int] = mapped_column(Integer)
    deaths: Mapped[int] = mapped_column(Integer)
    assists: Mapped[int] = mapped_column(Integer)
    gold_earned: Mapped[int] = mapped_column(Integer)
    total_minions_killed: Mapped[int] = mapped_column(Integer)
    neutral_minions_killed: Mapped[int] = mapped_column(Integer)
    vision_score: Mapped[int] = mapped_column(Integer)
    win: Mapped[bool] = mapped_column(Boolean)
    
    # Timeline features (extracted from timeline API)
    timeline_data: Mapped[Optional[dict]] = mapped_column(JSON)
    
    match: Mapped["Match"] = relationship(back_populates="participants")

class Team(Base):
    __tablename__ = "teams"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[str] = mapped_column(ForeignKey("matches.match_id"))
    team_id: Mapped[int] = mapped_column(Integer)
    win: Mapped[bool] = mapped_column(Boolean)
    
    # Objectives
    baron_kills: Mapped[int] = mapped_column(Integer)
    champion_kills: Mapped[int] = mapped_column(Integer)
    dragon_kills: Mapped[int] = mapped_column(Integer)
    inhibitor_kills: Mapped[int] = mapped_column(Integer)
    tower_kills: Mapped[int] = mapped_column(Integer)
    first_blood: Mapped[bool] = mapped_column(Boolean)
    first_tower: Mapped[bool] = mapped_column(Boolean)
    first_baron: Mapped[bool] = mapped_column(Boolean)
    first_dragon: Mapped[bool] = mapped_column(Boolean)
    
    bans: Mapped[list] = mapped_column(JSON)
    
    match: Mapped["Match"] = relationship(back_populates="teams")

class TournamentMatch(Base):
    __tablename__ = "tournament_matches"
    
    game_id: Mapped[str] = mapped_column(String, primary_key=True)
    match_id: Mapped[str] = mapped_column(String)
    tournament: Mapped[str] = mapped_column(String)
    date_time_utc: Mapped[datetime] = mapped_column(DateTime)
    team1: Mapped[str] = mapped_column(String)
    team2: Mapped[str] = mapped_column(String)
    win_team: Mapped[str] = mapped_column(String)
    duration: Mapped[str] = mapped_column(String)
    patch: Mapped[str] = mapped_column(String)
    team1_picks: Mapped[str] = mapped_column(String)
    team2_picks: Mapped[str] = mapped_column(String)

class LiveGameSnapshot(Base):
    __tablename__ = "live_game_snapshots"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(String)
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    snapshot_data: Mapped[dict] = mapped_column(JSON)
