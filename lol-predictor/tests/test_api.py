from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_get_model_info():
    response = client.get("/model/info")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "metrics" in data

def test_predict_pregame_validation():
    payload = {
        "team100_picks": [1, 2],
        "team200_picks": [6, 7, 8, 9, 10]
    }
    response = client.post("/predict/pregame", json=payload)
    assert response.status_code == 422
    
def test_predict_live_validation():
    payload = {
        "match_id": "NA1_12345",
        "minute": 15,
        "gd_10": 1000
    }
    response = client.post("/predict/live", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "win_probability_100" in data
    assert "win_probability_200" in data
    assert "confidence_interval" in data
