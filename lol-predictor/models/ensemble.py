import os
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, log_loss, brier_score_loss
import joblib

def train_meta_learner(base_preds_train, y_train, base_preds_test, y_test):
    meta_model = LogisticRegression()
    meta_model.fit(base_preds_train, y_train)
    
    final_preds = meta_model.predict_proba(base_preds_test)[:, 1]
    
    metrics = {
        'auc': float(roc_auc_score(y_test, final_preds)),
        'log_loss': float(log_loss(y_test, final_preds)),
        'brier_score': float(brier_score_loss(y_test, final_preds))
    }
    
    return meta_model, metrics

if __name__ == "__main__":
    print("Ensemble meta-learner defined.")
