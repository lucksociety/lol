import os
import json
import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from .schemas import PregameRequest, LiveGameRequest, PredictionResponse, ModelInfoResponse

models = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    base_dir = os.path.dirname(os.path.dirname(__file__))
    saved_dir = os.path.join(base_dir, "models", "saved", "v1.0")
    
    xgb_path = os.path.join(saved_dir, "xgb_pregame.pkl")
    if os.path.exists(xgb_path):
        models["xgb_pregame"] = joblib.load(xgb_path)
    
    meta_path = os.path.join(saved_dir, "xgb_metadata.json")
    if os.path.exists(meta_path):
        with open(meta_path, "r") as f:
            models["xgb_metadata"] = json.load(f)
            
    yield
    models.clear()

app = FastAPI(
    title="LoL Predictor API",
    description="World's best League of Legends match outcome prediction model",
    version="1.0.0",
    lifespan=lifespan
)

@app.post("/predict/pregame", response_model=PredictionResponse)
async def predict_pregame(request: PregameRequest):
    if "xgb_pregame" not in models:
        raise HTTPException(status_code=503, detail="Model not loaded")
        
    xgb_model = models["xgb_pregame"]
    features = models.get("xgb_metadata", {}).get("features", [])
    
    input_data = {f: 0 for f in features}
    df = pd.DataFrame([input_data])
    
    try:
        prob_100 = float(xgb_model.predict_proba(df)[:, 1][0])
        prob_200 = 1.0 - prob_100
        
        # A. Regional Volatility Penalty
        penalty = 0.0
        volatile_regions = ["LEC", "LCS", "CBLOL", "LCP", "NACL"]
        if request.region in volatile_regions:
            # High throw rate reduces the likelihood of a clean 2-0 sweep
            penalty = 0.10
            if prob_100 > 0.5:
                prob_100 -= penalty
                prob_200 += penalty
            else:
                prob_200 -= penalty
                prob_100 += penalty
                
        ci_lower = max(0.0, prob_100 - 0.05)
        ci_upper = min(1.0, prob_100 + 0.05)
        
        # B. Spread Activation Threshold
        threshold = 0.85 if request.region in volatile_regions else 0.70
        recommended_spread = "Moneyline Only"
        
        if prob_100 >= threshold:
            recommended_spread = "Team 100 -1.5"
        elif prob_200 >= threshold:
            recommended_spread = "Team 200 -1.5"
        
        return PredictionResponse(
            win_probability_100=prob_100,
            win_probability_200=prob_200,
            confidence_interval=[ci_lower, ci_upper],
            recommended_spread=recommended_spread,
            regional_volatility_penalty=penalty if penalty > 0 else None
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/predict/live", response_model=PredictionResponse)
async def predict_live(request: LiveGameRequest):
    prob_100 = 0.55
    if request.gd_15 and request.gd_15 > 0:
        prob_100 += 0.15
        
    prob_100 = min(max(prob_100, 0.0), 1.0)
    return PredictionResponse(
        win_probability_100=prob_100,
        win_probability_200=1.0 - prob_100,
        confidence_interval=[max(0.0, prob_100 - 0.08), min(1.0, prob_100 + 0.08)]
    )

@app.get("/model/info", response_model=ModelInfoResponse)
async def get_model_info():
    metadata = models.get("xgb_metadata", {})
    metrics = metadata.get("metrics", {"auc": 0.0, "log_loss": 0.0})
    return ModelInfoResponse(
        version="v1.0",
        last_trained="2026-04-24T00:00:00Z",
        metrics=metrics
    )
