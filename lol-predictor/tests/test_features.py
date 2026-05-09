import pytest
from features.pregame import compute_team_archetype, get_patch_recency_weight
from features.livegame import extract_timeline_features

def test_compute_team_archetype():
    poke_comp = ['Zoe', 'Ezreal', 'Jayce', 'Karma', 'Nidalee']
    dive_comp = ['Malphite', 'Diana', 'Kaisa', 'Nautilus', 'Vi']
    balanced = ['Garen', 'Annie', 'Ashe', 'Soraka', 'MasterYi']
    
    assert compute_team_archetype(poke_comp) == 'Poke'
    assert compute_team_archetype(dive_comp) == 'Dive'
    assert compute_team_archetype(balanced) == 'Balanced'

def test_get_patch_recency_weight():
    assert get_patch_recency_weight('14.2', '14.2') == 1.0
    
    weight_older = get_patch_recency_weight('14.1', '14.2')
    assert weight_older < 1.0
    assert weight_older > 0.0

def test_extract_timeline_features():
    mock_timeline = {
        'info': {
            'frames': [
                {'events': []},
                {'events': []},
                {'events': []},
                {'events': []},
                {'events': []},
                {'events': [{'type': 'CHAMPION_KILL', 'killerId': 3}]},
                {'events': []},
                {'events': []},
                {'events': []},
                {'events': []},
                {
                    'participantFrames': {
                        '1': {'totalGold': 3000},
                        '2': {'totalGold': 3000},
                        '3': {'totalGold': 3500},
                        '4': {'totalGold': 3000},
                        '5': {'totalGold': 3000},
                        '6': {'totalGold': 2500},
                        '7': {'totalGold': 2500},
                        '8': {'totalGold': 2500},
                        '9': {'totalGold': 2500},
                        '10': {'totalGold': 2500}
                    },
                    'events': []
                }
            ]
        }
    }
    
    features = extract_timeline_features("mock_id", mock_timeline)
    
    assert features.get('first_blood_team') == 100
    assert features.get('gd_10') == 3000
    
    import math
    assert math.isnan(features.get('gd_15'))
