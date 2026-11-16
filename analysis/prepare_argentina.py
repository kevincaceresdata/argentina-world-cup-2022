"""Team-level and player-level numbers for the Argentina 2022 dashboard."""

import json
from collections import defaultdict
from pathlib import Path

from profile import MATCHES, ORDER, ROOT, load


def main():
    events, frames = load()

    matches_out, players, dibu = [], {}, defaultdict(list)
    team_shots_af, team_shots_ec = defaultdict(int), defaultdict(int)
    pressures_team = defaultdict(int)

    for mid in ORDER:
        label, stage = MATCHES[mid]
        evs = [e for e in events if e["match_id"] == mid and e["period"] <= 4]
        gf = gc = xg_af = xg_ec = 0
        for e in evs:
            team = e["team"]["name"]
            p = (e.get("player") or {})
            pid, name = p.get("id"), p.get("name")
            if name:
                d = players.setdefault(pid, {"name": name, "goals": 0, "xg": 0.0,
                                             "shots": 0, "assists": 0, "pressures": 0,
                                             "matches": set()})
                d["matches"].add(mid)
            if e["type"]["name"] == "Shot":
                shot = e["shot"]
                xg = shot["statsbomb_xg"]
                scored = shot["outcome"]["name"] == "Goal"
                if team == "Argentina":
                    gf += scored
                    xg_af += xg
                    team_shots_af[mid] += 1
                    if name:
                        players[pid]["shots"] += 1
                        players[pid]["xg"] += xg
                        players[pid]["goals"] += scored
                else:
                    gc += scored
                    xg_ec += xg
                    team_shots_ec[mid] += 1
                    dibu[mid].append({"xg": xg, "goal": scored, "minute": e["minute"]})
            elif e["type"]["name"] == "Own Goal For":
                # deflected own goal: credited to this event's team
                if team == "Argentina":
                    gf += 1
                else:
                    gc += 1
                    dibu[mid].append({"xg": None, "goal": True, "minute": e["minute"]})
            elif e["type"]["name"] == "Pass" and team == "Argentina":
                if e.get("pass", {}).get("shot_assist") and name:
                    players[pid]["assists"] += 1
            elif e["type"]["name"] == "Pressure":
                if team == "Argentina":
                    pressures_team[mid] += 1
                    if name:
                        players[pid]["pressures"] += 1
        matches_out.append({
            "match_id": mid, "label": label, "stage": stage,
            "goals_for": gf, "goals_against": gc,
            "xg_for": round(xg_af, 2), "xg_against": round(xg_ec, 2),
            "shots_for": team_shots_af[mid], "shots_against": team_shots_ec[mid],
        })

    players_out = [
        {"name": d["name"], "goals": d["goals"], "xg": round(d["xg"], 2),
         "shots": d["shots"], "assists": d["assists"], "pressures": d["pressures"],
         "matches": len(d["matches"])}
        for d in players.values()
    ]
    players_out.sort(key=lambda d: (-d["goals"], -d["xg"]))

    dibu_out = [
        {"match": MATCHES[mid][0], "label": MATCHES[mid][0], "stage": MATCHES[mid][1],
         "xg_faced": round(sum(s["xg"] for s in dibu[mid] if s["xg"] is not None), 2),
         "goals_conceded": sum(1 for s in dibu[mid] if s["goal"])}
        for mid in ORDER
    ]

    totals = {
        "goals_for": sum(m["goals_for"] for m in matches_out),
        "goals_against": sum(m["goals_against"] for m in matches_out),
        "xg_for": round(sum(m["xg_for"] for m in matches_out), 2),
        "xg_against": round(sum(m["xg_against"] for m in matches_out), 2),
        "pressures": sum(pressures_team.values()),
    }

    out = {
        "team": {"name": "Argentina", "tournament": "2022 FIFA World Cup",
                 "result": "World champions"},
        "totals": totals,
        "matches": matches_out,
        "players": players_out,
        "dibu": dibu_out,
        "credit": "Data: StatsBomb (open data)",
    }
    dest = ROOT / "output" / "argentina.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(totals, indent=1))
    print("\nTOP 8 por goles:")
    for p in players_out[:8]:
        print(f"  {p['name']:<28} goles {p['goals']}  xG {p['xg']:.2f}  asist {p['assists']}  presiones {p['pressures']}  PJ {p['matches']}")
    print("\nDibu (xG enfrentado vs goles recibidos):")
    for d in dibu_out:
        print(f"  {d['match']:<18} xG en contra {d['xg_faced']:.2f}  goles {d['goals_conceded']}  {(d['xg_faced'] - d['goals_conceded']):+.2f}")
    print("\nPartidos (xG AF-EC):")
    for m in matches_out:
        print(f"  {m['label']:<18} {m['goals_for']}-{m['goals_against']}  xG {m['xg_for']:.2f}-{m['xg_against']:.2f}")


if __name__ == "__main__":
    main()
