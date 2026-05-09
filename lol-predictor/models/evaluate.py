import matplotlib.pyplot as plt
from sklearn.metrics import calibration_curve, roc_curve, auc
import os

def plot_calibration(y_true, y_prob, name, save_dir):
    prob_true, prob_pred = calibration_curve(y_true, y_prob, n_bins=10)
    
    plt.figure(figsize=(8, 8))
    plt.plot([0, 1], [0, 1], "k:", label="Perfectly calibrated")
    plt.plot(prob_pred, prob_true, "s-", label=f"{name}")
    plt.ylabel("Fraction of positives")
    plt.xlabel("Mean predicted value")
    plt.title(f"Calibration Curve - {name}")
    plt.legend(loc="lower right")
    
    os.makedirs(save_dir, exist_ok=True)
    plt.savefig(os.path.join(save_dir, f"{name}_calibration.png"))
    plt.close()

def plot_roc(y_true, y_prob, name, save_dir):
    fpr, tpr, _ = roc_curve(y_true, y_prob)
    roc_auc = auc(fpr, tpr)
    
    plt.figure(figsize=(8, 8))
    plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (area = {roc_auc:.2f})')
    plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title(f'Receiver Operating Characteristic - {name}')
    plt.legend(loc="lower right")
    
    os.makedirs(save_dir, exist_ok=True)
    plt.savefig(os.path.join(save_dir, f"{name}_roc.png"))
    plt.close()
