import pandas as pd
import numpy as np

# Simplified archetype mappings
COMP_TAGS = {
    'Poke': ['Zoe', 'Ezreal', 'Jayce', 'Xerath', 'Velkoz', 'Nidalee', 'Varus', 'Karma'],
    'Dive': ['Malphite', 'JarvanIV', 'Diana', 'Kaisa', 'Nautilus', 'Leona', 'Vi', 'Nocturne'],
    'Teamfight': ['Orianna', 'Amumu', 'MissFortune', 'Rell', 'Kennen', 'Rumble', 'Seraphine'],
    'Pick': ['Ahri', 'Blitzcrank', 'Elise', 'Thresh', 'Syndra', 'Ashe', 'Morgana'],
    'Split': ['Fiora', 'Jax', 'Camille', 'Tryndamere', 'Trundle', 'Yorick', 'Nasus']
}

def compute_patch_winrates(participants_df: pd.DataFrame, matches_df: pd.DataFrame) -> pd.DataFrame:
    merged = participants_df.merge(matches_df[['match_id', 'patch']], on='match_id')
    wr = merged.groupby(['patch', 'champion_id']).agg(
        games=('win', 'count'),
        wins=('win', 'sum')
    ).reset_index()
    wr['win_rate'] = wr['wins'] / wr['games']
    return wr

def compute_synergy_scores(participants_df: pd.DataFrame) -> pd.DataFrame:
    pairs = participants_df.merge(participants_df, on=['match_id', 'team_id'], suffixes=('_1', '_2'))
    pairs = pairs[pairs['champion_id_1'] < pairs['champion_id_2']]
    synergy = pairs.groupby(['champion_id_1', 'champion_id_2']).agg(
        games=('win_1', 'count'),
        wins=('win_1', 'sum')
    ).reset_index()
    synergy['synergy_win_rate'] = synergy['wins'] / synergy['games']
    return synergy

def compute_counter_picks(participants_df: pd.DataFrame) -> pd.DataFrame:
    team1 = participants_df[participants_df['team_id'] == 100]
    team2 = participants_df[participants_df['team_id'] == 200]
    matchups = team1.merge(team2, on=['match_id', 'team_position'], suffixes=('_1', '_2'))
    counters = matchups.groupby(['champion_id_1', 'champion_id_2', 'team_position']).agg(
        games=('win_1', 'count'),
        wins=('win_1', 'sum')
    ).reset_index()
    counters['matchup_win_rate'] = counters['wins'] / counters['games']
    return counters

def compute_player_history(participants_df: pd.DataFrame) -> pd.DataFrame:
    history = participants_df.groupby(['puuid', 'champion_id']).agg(
        games=('win', 'count'),
        wins=('win', 'sum'),
        total_kills=('kills', 'sum'),
        total_deaths=('deaths', 'sum'),
        total_assists=('assists', 'sum')
    ).reset_index()
    history['player_win_rate'] = history['wins'] / history['games']
    history['kda'] = (history['total_kills'] + history['total_assists']) / history['total_deaths'].replace(0, 1)
    
    # C. Synergy Half-Life: Discount stats for unproven players
    mask = history['games'] < 3
    history.loc[mask, 'player_win_rate'] *= 0.70
    history.loc[mask, 'kda'] *= 0.70
    
    return history

def compute_team_archetype(team_champions: list[str]) -> str:
    scores = {k: 0 for k in COMP_TAGS}
    for champ in team_champions:
        for archetype, champs in COMP_TAGS.items():
            if champ in champs:
                scores[archetype] += 1
    best_archetype = max(scores, key=scores.get)
    return best_archetype if scores[best_archetype] > 0 else 'Balanced'

def get_patch_recency_weight(patch: str, current_patch: str) -> float:
    try:
        p_major, p_minor = map(int, patch.split('.')[:2])
        c_major, c_minor = map(int, current_patch.split('.')[:2])
        diff = (c_major - p_major) * 20 + (c_minor - p_minor)
        return np.exp(-0.1 * max(0, diff))
    except:
        return 0.5

def get_coach_rating(coach_name: str) -> float:
    """
    Returns a normalized rating (0-1) based on historical draft success.
    TODO: Integrate with Leaguepedia coaching stats.
    """
    top_tier = ['Reapered', 'GrabbZ', 'Koma', 'Dylan Falco']
    if coach_name in top_tier:
        return 0.85
    return 0.50

def get_conversion_efficiency(team_id: str) -> float:
    """
    Measures how often a team closes games from a >2k gold lead.
    """
    # Heuristic based on today's LEC observations
    throw_heavy = ['SHFT', 'BDS', 'VIT']
    if team_id in throw_heavy:
        return 0.40
    return 0.65

def get_pressure_coefficient(venue_type: str) -> float:
    """
    Adjusts for 'Stage' vs 'Studio' performance based on experience.
    """
    if venue_type == 'Stage':
        return 1.10 
    return 1.0
