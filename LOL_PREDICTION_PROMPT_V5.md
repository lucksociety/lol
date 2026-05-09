# LOL OMNI-PROPHET V5.1 — PREDICTION PROMPT

> **Copy everything inside the code block below and paste it into a new conversation along with the matchup details.**

---

```
Analyze the attached match information.

### THE LAW: MANDATORY DATA INTEGRITY CHECK
BEFORE any simulations are performed, you MUST verify the completeness and freshness of the data. 

Step 1: Extract the team names (Team1, Team2) and their exact 5-man starting rosters.
Step 2: Run this exact bash command to check the local database:
`$env:PYTHONIOENCODING="utf-8"; & "C:\Users\dreis\AppData\Local\Programs\Python\Python313\python.exe" C:\Users\dreis\OneDrive\Desktop\Antigravity\LoL\lol_auto_sim.py --team1 "[TEAM1]" --team2 "[TEAM2]" --team1_roster "[...]" --team2_roster "[...]" --check_data`

Step 3: Data Validation & Ingestion Protocol
- If status is "OK": Proceed to Step 4.
- If status is "STALE_OR_MISSING":
  1. Execute `$env:PYTHONIOENCODING="utf-8"; & "C:\Users\dreis\AppData\Local\Programs\Python\Python313\python.exe" C:\Users\dreis\OneDrive\Desktop\Antigravity\LoL\lol_ingest_data.py` to auto-fetch missing stats.
  2. Search the web for current 2026 player metrics, form, and tier lists for the missing players.
  3. If data is still missing or remains "STALE_OR_MISSING" after these attempts: **STOP ALL WORK IMMEDIATELY.** Do not attempt a simulation. Provide a "Data Requirement Report" listing every missing player and the specific stats/metrics (Power Rating, Current Form, 2026 stats) needed for a high-precision prediction. Wait for the user to provide this data before continuing.

Step 4: Final Simulation
- ONLY if all data is present (or user-approved overrides are applied), run the simulation command:
`$env:PYTHONIOENCODING="utf-8"; & "C:\Users\dreis\AppData\Local\Programs\Python\Python313\python.exe" C:\Users\dreis\OneDrive\Desktop\Antigravity\LoL\lol_auto_sim.py --team1 "[TEAM1]" --team2 "[TEAM2]" --team1_roster "[...]" --team2_roster "[...]" [OVERRIDES_IF_ANY]`
- Report the exact output.
```
