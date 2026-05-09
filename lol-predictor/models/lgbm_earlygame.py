import os
import pandas as pd
import lightgbm as lgb
import optuna
from sklearn.metrics import roc_auc_score, log_loss, brier_score_loss
import joblib
import json

def train_lgbm_optuna(train_df: pd.DataFrame, test_df: pd.DataFrame, target_col: str = 'win'):
    drop_cols = [target_col, 'match_id', 'team_id', 'patch']
    features = [c for c in train_df.columns if c not in drop_cols]
    
    X_train, y_train = train_df[features], train_df[target_col]
    X_test, y_test = test_df[features], test_df[target_col]
    
    def objective(trial):
        params = {
            'objective': 'binary',
            'metric': 'auc',
            'boosting_type': 'gbdt',
            'num_leaves': trial.suggest_int('num_leaves', 20, 150),
            'learning_rate': trial.suggest_float('learning_rate', 1e-3, 0.3, log=True),
            'feature_fraction': trial.suggest_float('feature_fraction', 0.6, 1.0),
            'verbose': -1
        }
        
        train_data = lgb.Dataset(X_train, label=y_train)
        valid_data = lgb.Dataset(X_test, label=y_test, reference=train_data)
        
        model = lgb.train(params, train_data, num_boost_round=500, valid_sets=[valid_data], callbacks=[lgb.early_stopping(stopping_rounds=50, verbose=False)])
        preds = model.predict(X_test)
        auc = roc_auc_score(y_test, preds)
        return auc
        
    study = optuna.create_study(direction='maximize')
    study.optimize(objective, n_trials=20)
    
    best_params = study.best_params
    best_params['objective'] = 'binary'
    best_params['metric'] = 'auc'
    best_params['verbose'] = -1
    
    train_data = lgb.Dataset(X_train, label=y_train)
    final_model = lgb.train(best_params, train_data, num_boost_round=200)
    
    preds = final_model.predict(X_test)
    metrics = {
        'auc': float(roc_auc_score(y_test, preds)),
        'log_loss': float(log_loss(y_test, preds)),
        'brier_score': float(brier_score_loss(y_test, preds))
    }
    
    return final_model, metrics, features

if __name__ == "__main__":
    train_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "processed", "train_earlygame.parquet")
    test_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "processed", "test_earlygame.parquet")
    if os.path.exists(train_path) and os.path.exists(test_path):
        train_df = pd.read_parquet(train_path)
        test_df = pd.read_parquet(test_path)
        model, metrics, features = train_lgbm_optuna(train_df, test_df)
        print("LightGBM Early Game Metrics:", metrics)
        
        save_dir = os.path.join(os.path.dirname(__file__), "saved", "v1.0")
        os.makedirs(save_dir, exist_ok=True)
        joblib.dump(model, os.path.join(save_dir, "lgbm_earlygame.pkl"))
        with open(os.path.join(save_dir, "lgbm_metadata.json"), "w") as f:
            json.dump({'metrics': metrics, 'features': features}, f)
