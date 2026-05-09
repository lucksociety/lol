import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np
from sklearn.metrics import roc_auc_score

class MatchTimelineDataset(Dataset):
    def __init__(self, sequences, labels):
        self.sequences = torch.tensor(sequences, dtype=torch.float32)
        self.labels = torch.tensor(labels, dtype=torch.float32)

    def __len__(self):
        return len(self.sequences)

    def __getitem__(self, idx):
        return self.sequences[idx], self.labels[idx]

class TemporalRNN(nn.Module):
    def __init__(self, input_dim, hidden_dim, num_layers=1):
        super().__init__()
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers, batch_first=True)
        self.attention = nn.MultiheadAttention(embed_dim=hidden_dim, num_heads=1, batch_first=True)
        self.fc = nn.Linear(hidden_dim, 1)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        attn_out, _ = self.attention(lstm_out, lstm_out, lstm_out)
        last_out = attn_out[:, -1, :]
        out = self.fc(last_out)
        return self.sigmoid(out).squeeze(-1)

def train_temporal_model(X_train, y_train, X_test, y_test, epochs=10, batch_size=32):
    train_dataset = MatchTimelineDataset(X_train, y_train)
    test_dataset = MatchTimelineDataset(X_test, y_test)
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)
    
    input_dim = X_train.shape[2]
    model = TemporalRNN(input_dim=input_dim, hidden_dim=64)
    criterion = nn.BCELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    for epoch in range(epochs):
        model.train()
        for seqs, labels in train_loader:
            optimizer.zero_grad()
            outputs = model(seqs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
    model.eval()
    all_preds = []
    with torch.no_grad():
        for seqs, _ in test_loader:
            preds = model(seqs)
            all_preds.extend(preds.numpy())
            
    auc = float(roc_auc_score(y_test, all_preds))
    return model, auc

if __name__ == "__main__":
    print("Temporal RNN model defined.")
