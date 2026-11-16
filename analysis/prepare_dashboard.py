"""Precompute a compact summary.json for the dashboard from the raw StatsBomb data.

Run from the repo root:  python analysis/prepare_dashboard.py
Output: output/summary.json (copy to julian-dashboard/public/data/).
"""

from __future__ import annotations

import json
from pathlib import Path

from profile import JULIAN, MATCHES, ORDER, ROOT, juvian, load, shot_rows


def main():
    events, frames = load()
    shots = shot_rows(events, frames)

    receipts = [e for e in juvian(events) if e["type"]["name"] == "Ball Receipt*"]
    under = sum(1 for e in receipts if e.get("under_pressure"))
    press_locs = [(round(e["location"][0], 1), round(e["location"][1], 1))
                  for e in juvian(events)
                  if e["type"]["name"] == "Pressure" and e.get("location")]
    assists = sum(1 for e in juvian(events) if e["type"]["name"] == "Pass"
                  and e.get("pass", {}).get("shot_assist"))

    by_match = []
    for mid in ORDER:
        label, stage = MATCHES[mid]
        g = shots[shots.match == mid]
        by_match.append({
            "match_id": mid, "label": label, "stage": stage,
            "shots": int(len(g)), "goals": int(g.goal.sum()),
            "xg": round(float(g.xg.sum()), 3),
        })

    s = shots.dropna(subset=["defender_m"])
    summary = {
        "player": {"name": "Julián Álvarez", "team": "Argentina",
                   "tournament": "2022 FIFA World Cup", "position": "Forward"},
        "totals": {
            "shots": int(len(shots)), "goals": int(shots.goal.sum()),
            "xg": round(float(shots.xg.sum()), 2),
            "xg_per_shot": round(float(shots.xg.mean()), 3),
            "shot_assists": int(assists),
            "pressure_events": int(len(press_locs)),
            "receipts": len(receipts), "receipts_under_pressure": int(under),
            "receipts_under_pressure_pct": round(100 * under / len(receipts)),
            "mean_defender_m": round(float(s.defender_m.mean()), 2),
            "shots_with_frame": int(len(s)),
            "shots_under_2m": int((s.defender_m < 2).sum()),
        },
        "matches": by_match,
        "shots": [
            {"match": MATCHES[r.match][0], "stage": MATCHES[r.match][1],
             "minute": int(r.minute), "x": round(r.x, 1), "y": round(r.y, 1),
             "xg": round(r.xg, 3), "outcome": r.outcome, "goal": bool(r.goal),
             "defender_m": None if pd_isna(r.defender_m) else round(r.defender_m, 2)}
            for r in shots.itertuples()
        ],
        "pressure_points": [{"x": x, "y": y} for x, y in press_locs],
        "credit": "Data: StatsBomb (open data)",
    }
    out = ROOT / "output" / "summary.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size} bytes)")


def pd_isna(v):
    return v is None or (isinstance(v, float) and v != v)


if __name__ == "__main__":
    main()
