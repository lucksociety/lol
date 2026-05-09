import math
import random

class DecisionNode:
    def __init__(self, feature_idx=None, threshold=None, left=None, right=None, value=None):
        self.feature_idx = feature_idx
        self.threshold = threshold
        self.left = left
        self.right = right
        self.value = value

class PurePythonDecisionTree:
    def __init__(self, max_depth=3):
        self.max_depth = max_depth
        self.root = None

    def fit(self, X, y, depth=0):
        num_samples = len(X)
        if num_samples == 0:
            return None
        
        # If all labels are same or max depth reached
        if len(set(y)) == 1 or depth >= self.max_depth or num_samples < 2:
            return DecisionNode(value=sum(y)/num_samples)

        num_features = len(X[0])
        best_feat, best_thresh = None, None
        best_mse = float('inf')

        # Simple greedy search for best split
        for feat_idx in range(num_features):
            thresholds = sorted(list(set([row[feat_idx] for row in X])))
            for thresh in thresholds:
                left_indices = [i for i, row in enumerate(X) if row[feat_idx] <= thresh]
                right_indices = [i for i, row in enumerate(X) if row[feat_idx] > thresh]
                
                if not left_indices or not right_indices:
                    continue
                
                left_y = [y[i] for i in left_indices]
                right_y = [y[i] for i in right_indices]
                
                mse = self._calc_mse(left_y) + self._calc_mse(right_y)
                if mse < best_mse:
                    best_mse = mse
                    best_feat = feat_idx
                    best_thresh = thresh

        if best_feat is None:
            return DecisionNode(value=sum(y)/num_samples)

        left_X = [X[i] for i, row in enumerate(X) if row[best_feat] <= best_thresh]
        left_y = [y[i] for i, row in enumerate(X) if row[best_feat] <= best_thresh]
        right_X = [X[i] for i, row in enumerate(X) if row[best_feat] > best_thresh]
        right_y = [y[i] for i, row in enumerate(X) if row[best_feat] > best_thresh]

        return DecisionNode(
            feature_idx=best_feat,
            threshold=best_thresh,
            left=self.fit(left_X, left_y, depth + 1),
            right=self.fit(right_X, right_y, depth + 1)
        )

    def _calc_mse(self, y):
        if not y: return 0
        mean = sum(y) / len(y)
        return sum((val - mean) ** 2 for val in y)

    def predict_one(self, x, node=None):
        if node is None: node = self.root
        if node.value is not None:
            return node.value
        if x[node.feature_idx] <= node.threshold:
            return self.predict_one(x, node.left)
        else:
            return self.predict_one(x, node.right)

class PurePythonGBDT:
    def __init__(self, n_estimators=10, learning_rate=0.1, max_depth=3):
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.max_depth = max_depth
        self.trees = []
        self.initial_prediction = 0

    def fit(self, X, y):
        self.initial_prediction = sum(y) / len(y)
        current_preds = [self.initial_prediction] * len(y)
        
        for _ in range(self.n_estimators):
            residuals = [y[i] - current_preds[i] for i in range(len(y))]
            tree = PurePythonDecisionTree(max_depth=self.max_depth)
            tree.root = tree.fit(X, residuals)
            self.trees.append(tree)
            
            for i in range(len(X)):
                current_preds[i] += self.learning_rate * tree.predict_one(X[i])

    def predict_proba(self, X):
        results = []
        for x in X:
            pred = self.initial_prediction
            for tree in self.trees:
                pred += self.learning_rate * tree.predict_one(x)
            # Apply sigmoid for probability
            prob = 1 / (1 + math.exp(-pred))
            results.append([1-prob, prob])
        return results

    def predict(self, X):
        return [1 if p[1] > 0.5 else 0 for p in self.predict_proba(X)]

if __name__ == "__main__":
    print("Pure Python GBDT model defined.")
