#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════
LOL DATA RECORDER — AUTOMATIC SIMULATION PERSISTENCE
═══════════════════════════════════════════════════════════════════════

Ported from MLB Omni-Prophet V16.0 data_recorder.py.
Auto-records every simulation run to:
  1. prediction_ledger.db (enhanced with calibration/trap data)
  2. audits/audit_[T1]_[T2]_[DATE].json (full audit trail)
  3. intelligence/matchup_[T1]_[T2]_[DATE].md (intelligence report)

Usage:
    from data_recorder import record_simulation
    record_simulation(match_data, sim_results, market_odds)
"""

import json
import os
import sqlite3
from datetime import datetime, timezone
import sys
import io

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDITS_DIR = os.path.join(BASE_DIR, "audits")
INTEL_DIR = os.path.join(BASE_DIR, "intelligence")
LEDGER_DB = os.path.join(BASE_DIR, "data", "prediction_ledger.db")


def record_simulation(match_data, sim_results, market_odds=None):
    """Record a complete simulation run to all persistence layers.
    
    Args:
        match_data: dict with keys: team1, team2, league, date, etc.
        sim_results: dict from simulate_bo_series() with win_prob, scores, etc.
        market_odds: optional dict of market odds
    """
    t1_name = match_data.get('team1', {}).get('name', 'T1')
    t2_name = match_data.get('team2', {}).get('name', 'T2')
    date_str = match_data.get('date', datetime.now().strftime('%Y-%m-%d'))
    league = match_data.get('league', match_data.get('team1', {}).get('league', 'Unknown'))
    
    # 1. JSON Audit Trail
    _write_audit(t1_name, t2_name, date_str, match_data, sim_results, market_odds)
    
    # 2. Intelligence Report
    _write_intelligence(t1_name, t2_name, date_str, match_data, sim_results, market_odds)
    
    print(f"  📁 Data recorded: audit + intelligence for {t1_name} vs {t2_name}")


def _write_audit(t1, t2, date_str, match_data, sim_results, market_odds):
    """Write complete JSON audit trail."""
    os.makedirs(AUDITS_DIR, exist_ok=True)
    
    audit = {
        'meta': {
            'engine': 'LOL Omni-Prophet V5.0',
            'recorded_at': datetime.now(timezone.utc).isoformat(),
            'match_date': date_str,
        },
        'match_data': _sanitize_for_json(match_data),
        'sim_results': _sanitize_for_json(sim_results),
        'market_odds': market_odds,
        'accuracy': {
            'winner': 'TBD',
            'actual_score': 'TBD',
            'correct': None,
        }
    }
    
    filename = f"audit_{t1}_{t2}_{date_str}.json"
    filepath = os.path.join(AUDITS_DIR, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(audit, f, indent=2, default=str, ensure_ascii=False)
    
    print(f"  📄 Audit: {filename}")


def _write_intelligence(t1, t2, date_str, match_data, sim_results, market_odds):
    """Write structured intelligence report."""
    os.makedirs(INTEL_DIR, exist_ok=True)
    
    win_prob = sim_results.get('win_prob', 0.5)
    scores = sim_results.get('scores', {})
    ensemble = sim_results.get('ensemble', {})
    value_traps = sim_results.get('value_traps', {})
    calibration = sim_results.get('calibration', {})
    
    league = match_data.get('league', 'Unknown')
    
    # Build the report
    lines = [
        f"# Match Intelligence: {t1} vs {t2}",
        f"**Date**: {date_str} | **League**: {league} | **Engine**: LOL Omni-Prophet V5.0",
        f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "---",
        "",
        "## Series Projection",
        f"- **{t1} Win Probability**: {win_prob*100:.1f}%",
        f"- **{t2} Win Probability**: {(1-win_prob)*100:.1f}%",
    ]
    
    if scores:
        lines.append("- **Score Distribution**:")
        for score, prob in sorted(scores.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"  - {score}: {prob*100:.1f}%")
    
    if ensemble:
        lines.extend([
            "",
            "## Ensemble Cross-Check",
            f"- Deterministic: {ensemble.get('det_prob', 0)*100:.1f}%",
            f"- GBDT: {ensemble.get('gbdt_prob', 0)*100:.1f}%",
            f"- Disagreement: {ensemble.get('disagreement', 0)*100:.1f}%",
            f"- Status: {'⚠️ SPLIT SIGNAL' if ensemble.get('warning') else '✅ ALIGNED'}",
        ])
    
    if value_traps:
        lines.extend(["", "## Value Trap Alerts"])
        for team, flags in value_traps.items():
            lines.append(f"- 🚨 **{team}**:")
            for f in flags:
                lines.append(f"  - {f}")
    
    if calibration:
        lines.extend([
            "",
            "## Calibration Applied",
            f"- Prob Adjustment: {calibration.get('prob_adjustment', 1.0):.3f}x",
            f"- Status: {calibration.get('status', 'N/A')}",
        ])
    
    if market_odds:
        lines.extend(["", "## Market Intelligence"])
        for label, odds in market_odds.items():
            lines.append(f"- {label}: {odds}")
    
    lines.extend([
        "",
        "---",
        "## Outcome (Post-Match)",
        "- **Winner**: TBD",
        "- **Actual Score**: TBD",
        "- **Prediction Correct**: TBD",
    ])
    
    filename = f"matchup_{t1}_{t2}_{date_str}.md"
    filepath = os.path.join(INTEL_DIR, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"  📄 Intel: {filename}")


def _sanitize_for_json(obj):
    """Convert non-serializable objects for JSON output."""
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_sanitize_for_json(item) for item in obj]
    elif isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    else:
        return str(obj)
