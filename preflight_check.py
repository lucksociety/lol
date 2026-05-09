import sys
import os
import sqlite3
import io

def check_package(package):
    try:
        if package == "pure_python_ensemble":
            # Add models dir to path to check our custom module
            sys.path.append(os.path.join(os.getcwd(), "models"))
            import pure_python_ensemble
            return True
        __import__(package)
        return True
    except ImportError:
        return False

def run_preflight():
    print("=== League of Legends Predictor Preflight Check (Self-Sufficient Mode) ===")
    
    # 1. Environment Checks
    packages = ["sqlite3", "urllib.request", "json", "pure_python_ensemble"]
    print("\n[1] Checking Core Dependencies:")
    missing = []
    for pkg in packages:
        status = "OK" if check_package(pkg) else "MISSING"
        print(f"  - {pkg:22}: {status}")
        if status == "MISSING":
            missing.append(pkg)
            
    # 2. Database Checks
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, "data", "lol_predictions.db")
    print("\n[2] Checking Database:")
    if os.path.exists(db_path):
        print(f"  - Path: {db_path} (FOUND)")
    else:
        print(f"  - Path: {db_path} (NOT FOUND - Pipeline Run Required)")

    # 3. Config Checks
    env_path = os.path.join(base_dir, ".env")
    print("\n[3] Checking Configuration:")
    if os.path.exists(env_path):
        print(f"  - .env: FOUND")
    else:
        print(f"  - .env: NOT FOUND (Required for Riot API)")

    # 4. Advanced Modeling Readiness
    ensemble_path = os.path.join(base_dir, "models", "pure_python_ensemble.py")
    print("\n[4] Checking Advanced Models:")
    if os.path.exists(ensemble_path):
        print(f"  - Pure Python GBDT: READY")
    else:
        print(f"  - Pure Python GBDT: MISSING")
        missing.append("pure_python_ensemble")

    # 5. Deterministic Fallback
    det_model_path = os.path.join(base_dir, "models", "deterministic_lol.py")
    print("\n[5] Checking Deterministic Fallback:")
    if os.path.exists(det_model_path):
        print(f"  - Deterministic Model: READY")
    else:
        print(f"  - Deterministic Model: MISSING")

    print("\n=== Preflight Summary ===")
    if missing:
        print(f"STATUS: YELLOW (Some core components missing)")
    else:
        print("STATUS: GREEN (System is fully self-sufficient and ready)")

    # 6. Roster Verification Gate
    roster_gate_path = os.path.join(base_dir, "models", "roster_gate.py")
    roster_file_path = os.path.join(base_dir, "data", "verified_rosters.json")
    print("\n[6] Checking Roster Verification Gate:")
    if os.path.exists(roster_gate_path):
        print(f"  - roster_gate.py: READY")
    else:
        print(f"  - roster_gate.py: MISSING (⚠️ Simulations will run WITHOUT verification!)")

    if os.path.exists(roster_file_path):
        import json
        try:
            with open(roster_file_path, "r") as f:
                rosters = json.load(f)
            verified_count = len(rosters)
            print(f"  - verified_rosters.json: FOUND ({verified_count} teams verified)")
            if verified_count == 0:
                print(f"  - ⚠️  WARNING: No teams verified. Run 'python3 -m models.roster_gate verify' before simulating.")
            else:
                from datetime import datetime, timezone, timedelta
                stale_teams = []
                for code, entry in rosters.items():
                    try:
                        verified_at = datetime.fromisoformat(entry.get("verified_at", ""))
                        if verified_at.tzinfo is None:
                            verified_at = verified_at.replace(tzinfo=timezone.utc)
                        if (datetime.now(timezone.utc) - verified_at) > timedelta(hours=12):
                            stale_teams.append(code)
                    except:
                        stale_teams.append(code)
                if stale_teams:
                    print(f"  - [STALE] STALE ROSTERS: {', '.join(stale_teams)} (>12h old, re-verify before simulating)")
                else:
                    print(f"  - [FRESH] All {verified_count} rosters are FRESH")
        except Exception as e:
            print(f"  - verified_rosters.json: ERROR ({e})")
    else:
        print(f"  - verified_rosters.json: NOT FOUND (Run roster_gate to create)")

    # 7. Prediction Ledger (Quant-Elite 4.0)
    print("\n[7] Checking Prediction Ledger (4.0):")
    ledger_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "prediction_ledger.db")
    if os.path.exists(ledger_db):
        import sqlite3
        conn = sqlite3.connect(ledger_db)
        total = conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
        resolved = conn.execute("SELECT COUNT(*) FROM predictions WHERE winner IS NOT NULL").fetchone()[0]
        conn.close()
        print(f"  - prediction_ledger.db: FOUND ({total} predictions, {resolved} resolved)")
    else:
        print(f"  - prediction_ledger.db: NOT YET CREATED (will auto-create on first prediction)")

    # 8. Computed Ratings & Synergy (Quant-Elite 4.0)
    print("\n[8] Checking Auto-Computed Ratings (4.0):")
    ratings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "computed_ratings.json")
    synergy_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "computed_synergy.json")
    if os.path.exists(ratings_file):
        with open(ratings_file, "r") as f:
            ratings_data = json.load(f)
        player_count = len(ratings_data.get("players", {}))
        league = ratings_data.get("league", "?")
        print(f"  - computed_ratings.json: FOUND ({player_count} players, {league})")
    else:
        print(f"  - computed_ratings.json: NOT YET COMPUTED (using manual fallback ratings)")
    
    if os.path.exists(synergy_file):
        with open(synergy_file, "r") as f:
            syn_data = json.load(f)
        team_count = len(syn_data.get("teams", {}))
        print(f"  - computed_synergy.json: FOUND ({team_count} teams)")
    else:
        print(f"  - computed_synergy.json: NOT YET COMPUTED (using manual fallback synergy)")

    # 9. Ensemble Engine (Quant-Elite 4.0)
    print("\n[9] Checking Ensemble Engine (4.0):")
    ensemble_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "ensemble_engine.py")
    if os.path.exists(ensemble_path):
        print(f"  - ensemble_engine.py: READY")
        print(f"  - GBDT Status: Awaiting training data (will auto-train once historical matches are loaded)")
    else:
        print(f"  - ensemble_engine.py: NOT FOUND")

if __name__ == "__main__":
    run_preflight()
