from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class PregameRequest(BaseModel):
    team100_picks: List[int] = Field(..., max_length=5, min_length=5)
    team200_picks: List[int] = Field(..., max_length=5, min_length=5)
    team100_bans: List[int] = Field(default_factory=list)
    team200_bans: List[int] = Field(default_factory=list)
    summoner_ids_100: List[str] = Field(default_factory=list)
    summoner_ids_200: List[str] = Field(default_factory=list)
    patch: str = Field(default="14.1")
    region: str = Field(default="Unknown")

class LiveGameRequest(BaseModel):
    match_id: str
    minute: int
    gd_10: Optional[float] = None
    gd_15: Optional[float] = None
    first_blood_team: Optional[int] = None
    first_dragon_team: Optional[int] = None
    first_tower_team: Optional[int] = None
    first_baron_team: Optional[int] = None
    
class PredictionResponse(BaseModel):
    win_probability_100: float
    win_probability_200: float
    confidence_interval: List[float]
    recommended_spread: Optional[str] = None
    regional_volatility_penalty: Optional[float] = None

class ModelInfoResponse(BaseModel):
    version: str
    last_trained: str
    metrics: Dict[str, float]
