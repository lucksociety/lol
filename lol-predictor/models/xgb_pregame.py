import os
import pandas as pd
import xgboost as xgb
import optuna
from sklearn.metrics import roc_auc_score, log_loss, brier_score_loss
import joblib
import json

def train_xgb_optuna(train_df: pd.DataFrame, test_df: pd.DataFrame, target_col: str = 'win'):
    drop_cols = [target_col, 'match_id', 'team_id', 'patch']
    features = [c for c in train_df.columns if c not in drop_cols]
    
    X_train, y_train = train_df[features], train_df[target_col]
    X_test, y_test = test_df[features], test_df[target_col]
    
    def objective(trial):
        params = {
            'objective': 'binary:logistic',
            'eval_metric': 'auc',
            'max_depth': trial.suggest_int('max_depth', 3, 9),
            'learning_rate': trial.suggest_float('learning_rate', 1e-3, 0.3, log=True),
            'n_estimators': trial.suggest_int('n_estimators', 50, 500),
            'subsample': trial.suggest_float('subsample', 0.6, 1.0),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0)
        }
        
        model = xgb.XGBClassifier(**params, random_state=42)
        model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)
        preds = model.predict_proba(X_test)[:, 1]
        auc = roc_auc_score(y_test, preds)
        return auc
        
    study = optuna.create_study(direction='maximize')
    study.optimize(objective, n_trials=20)
    
    best_params = study.best_params
    best_params['objective'] = 'binary:logistic'
    best_params['eval_metric'] = 'auc'
    
    final_model = xgb.XGBClassifier(**best_params, random_state=42)
    final_model.fit(X_train, y_train)
    
    preds = final_model.predict_proba(X_test)[:, 1]
    metrics = {
        'auc': float(roc_auc_score(y_test, preds)),
        'log_loss': float(log_loss(y_test, preds)),
        'brier_score': float(brier_score_loss(y_test, preds))
    }
    
    return final_model, metrics, features

if __name__ == "__main__":
    train_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "processed", "train_pregame.parquet")
    test_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "processed", "test_pregame.parquet")
    if os.path.exists(train_path) and os.path.exists(test_path):
        train_df = pd.read_parquet(train_path)
        test_df = pd.read_parquet(test_path)
        model, metrics, features = train_xgb_optuna(train_df, test_df)
        print("XGBoost Baseline Metrics:", metrics)
        
        save_dir = os.path.join(os.path.dirname(__file__), "saved", "v1.0")
        os.makedirs(save_dir, exist_ok=True)
        joblib.dump(model, os.path.join(save_dir, "xgb_pregame.pkl"))
        with open(os.path.join(save_dir, "xgb_metadata.json"), "w") as f:
            json.dump({'metrics': metrics, 'features': features}, f)
