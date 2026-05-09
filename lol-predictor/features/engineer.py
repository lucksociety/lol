import os
import pandas as pd
from features.loader import load_raw_matches, load_participants
from features.pregame import (
    compute_patch_winrates, compute_synergy_scores, 
    compute_counter_picks, compute_player_history,
    compute_team_archetype, get_patch_recency_weight
)

def build_pregame_dataset() -> pd.DataFrame:
    print("Loading raw data...")
    matches_df = load_raw_matches()
    participants_df = load_participants()
    
    if matches_df.empty or participants_df.empty:
        print("No data available in DB to engineer features.")
        return pd.DataFrame()
        
    print("Computing pre-game historical features...")
    # In a full pipeline, we would merge these dictionary-like DataFrames onto the main df
    # patch_wr = compute_patch_winrates(participants_df, matches_df)
    # synergy = compute_synergy_scores(participants_df)
    # counters = compute_counter_picks(participants_df)
    # history = compute_player_history(participants_df)
    
    current_patch = matches_df['patch'].max()
    
    print("Building match-level dataset...")
    team_comps = participants_df.groupby(['match_id', 'team_id'])['champion_name'].apply(list).reset_index()
    team_comps['archetype'] = team_comps['champion_name'].apply(compute_team_archetype)
    
    target = matches_df[['match_id', 'team_id', 'win', 'patch']]
    
    df = target.merge(team_comps[['match_id', 'team_id', 'archetype']], on=['match_id', 'team_id'], how='left')
    df['patch_weight'] = df['patch'].apply(lambda x: get_patch_recency_weight(x, current_patch))
    df = pd.get_dummies(df, columns=['archetype'])
    
    print("Feature engineering complete.")
    return df

def save_datasets(df: pd.DataFrame, output_dir: str):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    if df.empty:
        return
        
    df = df.sort_values('match_id')
    split_idx = int(len(df) * 0.8)
    
    train = df.iloc[:split_idx]
    test = df.iloc[split_idx:]
    
    train.to_parquet(os.path.join(output_dir, 'train_pregame.parquet'))
    test.to_parquet(os.path.join(output_dir, 'test_pregame.parquet'))
    print(f"Saved datasets to {output_dir}")

if __name__ == "__main__":
    df = build_pregame_dataset()
    base_dir = os.path.dirname(os.path.dirname(__file__))
    save_datasets(df, os.path.join(base_dir, "data", "processed"))
