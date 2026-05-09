import numpy as np

def extract_timeline_features(match_id: str, timeline_data: dict) -> dict:
    if not timeline_data or 'info' not in timeline_data:
        return {}
        
    frames = timeline_data['info'].get('frames', [])
    features = {}
    
    for minute in [10, 15, 20]:
        if len(frames) > minute:
            frame = frames[minute]
            team100_gold = 0
            team200_gold = 0
            
            for p_id, p_data in frame.get('participantFrames', {}).items():
                if int(p_id) <= 5:
                    team100_gold += p_data.get('totalGold', 0)
                else:
                    team200_gold += p_data.get('totalGold', 0)
                    
            features[f'gd_{minute}'] = team100_gold - team200_gold
        else:
            features[f'gd_{minute}'] = np.nan
            
    fb, ft, fd, fbaron = False, False, False, False
    for frame in frames:
        for event in frame.get('events', []):
            e_type = event.get('type')
            if e_type == 'CHAMPION_KILL' and not fb:
                fb = True
                features['first_blood_team'] = 100 if event.get('killerId', 0) <= 5 else 200
            elif e_type == 'BUILDING_KILL' and not ft:
                if event.get('buildingType') == 'TOWER_BUILDING':
                    ft = True
                    features['first_tower_team'] = 100 if event.get('killerId', 0) <= 5 else 200
            elif e_type == 'ELITE_MONSTER_KILL':
                monster = event.get('monsterType')
                if monster == 'DRAGON' and not fd:
                    fd = True
                    features['first_dragon_team'] = 100 if event.get('killerId', 0) <= 5 else 200
                elif monster == 'BARON_NASHOR' and not fbaron:
                    fbaron = True
                    features['first_baron_team'] = 100 if event.get('killerId', 0) <= 5 else 200
                    
    return features
