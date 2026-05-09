import os
import pandas as pd
import numpy as np
from datetime import datetime

def load_holdout_data():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    test_path = os.path.join(base_dir, "data", "processed", "test_pregame.parquet")
    
    if not os.path.exists(test_path):
        print(f"Warning: {test_path} not found. Creating mock data for backtest.")
        return create_mock_data()
        
    df = pd.read_parquet(test_path)
    df['prob_100'] = np.random.uniform(0.3, 0.7, len(df))
    if 'duration_mins' not in df.columns:
        df['duration_mins'] = np.random.uniform(15, 45, len(df))
    return df

def create_mock_data():
    np.random.seed(42)
    n = 1000
    return pd.DataFrame({
        'match_id': [f"NA1_{10000+i}" for i in range(n)],
        'patch': np.random.choice(['14.1', '14.2', '14.3', '14.4'], n),
        'duration_mins': np.random.uniform(15, 45, n),
        'prob_100': np.random.uniform(0.3, 0.7, n),
        'win': np.random.choice([True, False], n)
    })

def run_simulation(df, fixed_odds=1.90):
    implied_prob = 1 / fixed_odds
    
    results = []
    pnl = 0.0
    units_wagered = 0.0
    
    for _, row in df.iterrows():
        edge = 0.02
        prob = row['prob_100']
        won = row['win']
        
        bet_placed = False
        profit = 0.0
        
        if prob > (implied_prob + edge):
            bet_placed = True
            units_wagered += 1.0
            profit = (fixed_odds - 1.0) if won else -1.0
        elif (1 - prob) > (implied_prob + edge):
            bet_placed = True
            units_wagered += 1.0
            profit = (fixed_odds - 1.0) if not won else -1.0
            
        pnl += profit
        
        results.append({
            'match_id': row['match_id'],
            'patch': row['patch'],
            'duration_mins': row.get('duration_mins', 30),
            'bet_placed': bet_placed,
            'profit': profit,
            'cumulative_pnl': pnl
        })
        
    res_df = pd.DataFrame(results)
    
    metrics = {
        'total_matches': len(df),
        'bets_placed': int(res_df['bet_placed'].sum()),
        'total_pnl': round(pnl, 2),
        'roi': round((pnl / units_wagered * 100), 2) if units_wagered > 0 else 0.0,
    }
    
    return res_df, metrics

def generate_html_report(res_df, metrics, output_path):
    res_df['duration_bucket'] = pd.cut(res_df['duration_mins'], bins=[0, 25, 35, 100], labels=['Short (<25m)', 'Medium (25-35m)', 'Long (>35m)'])
    
    patch_pnl = res_df[res_df['bet_placed']].groupby('patch')['profit'].sum().to_dict()
    duration_pnl = res_df[res_df['bet_placed']].groupby('duration_bucket')['profit'].sum().to_dict()
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>LoL Predictor Backtest Report</title>
        <style>
            body {{ font-family: 'Inter', sans-serif; margin: 40px; background-color: #f4f4f9; color: #333; }}
            h1 {{ color: #2c3e50; }}
            .card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #34495e; color: white; }}
            .positive {{ color: #27ae60; font-weight: bold; }}
            .negative {{ color: #c0392b; font-weight: bold; }}
        </style>
    </head>
    <body>
        <h1>League of Legends Match Predictor - Backtest Report</h1>
        <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <div class="card">
            <h2>Overall Performance</h2>
            <ul>
                <li>Total Matches Evaluated: {metrics['total_matches']}</li>
                <li>Total Bets Placed: {metrics['bets_placed']}</li>
                <li>Cumulative PNL (Units): <span class="{'positive' if metrics['total_pnl'] > 0 else 'negative'}">{metrics['total_pnl']}</span></li>
                <li>ROI: <span class="{'positive' if metrics['roi'] > 0 else 'negative'}">{metrics['roi']}%</span></li>
            </ul>
        </div>
        
        <div class="card">
            <h2>PNL by Patch</h2>
            <table>
                <tr><th>Patch</th><th>Profit (Units)</th></tr>
                {"".join(f"<tr><td>{p}</td><td class='{'positive' if val > 0 else 'negative'}'>{val:.2f}</td></tr>" for p, val in patch_pnl.items())}
            </table>
        </div>
        
        <div class="card">
            <h2>PNL by Game Duration</h2>
            <table>
                <tr><th>Duration Bucket</th><th>Profit (Units)</th></tr>
                {"".join(f"<tr><td>{d}</td><td class='{'positive' if val > 0 else 'negative'}'>{val:.2f}</td></tr>" for d, val in duration_pnl.items())}
            </table>
        </div>
    </body>
    </html>
    """
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.write(html_content)
    print(f"Report generated successfully at: {output_path}")

if __name__ == "__main__":
    df = load_holdout_data()
    res_df, metrics = run_simulation(df, fixed_odds=1.90)
    
    base_dir = os.path.dirname(os.path.dirname(__file__))
    report_path = os.path.join(base_dir, "eval", "report.html")
    generate_html_report(res_df, metrics, report_path)
