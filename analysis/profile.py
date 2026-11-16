"""Player profile: Julián Álvarez at the 2022 World Cup (StatsBomb open data).

Run:  python analysis/profile.py
Deps: pandas, matplotlib, mplsoccer (data already in data/).

Produces the figures in output/ and prints the numbers used in the README.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from matplotlib.figure import Figure
from mplsoccer import Pitch

ROOT = Path(__file__).resolve().parent.parent
JULIAN = 29560
MATCHES = {
    3857300: ("vs Saudi Arabia", "Group"),
    3857289: ("vs Mexico", "Group"),
    3857264: ("vs Poland", "Group"),
    3869151: ("vs Australia", "R16"),
    3869321: ("vs Netherlands", "QF"),
    3869519: ("vs Croatia", "SF"),
    3869685: ("vs France", "Final"),
}
ORDER = [3857300, 3857289, 3857264, 3869151, 3869321, 3869519, 3869685]


def load():
    events, frames = [], {}
    for mid in ORDER:
        evs = json.loads((ROOT / "data" / "events" / f"{mid}.json").read_text(encoding="utf-8"))
        for ev in evs:
            ev["match_id"] = mid
        events += evs
        for fr in json.loads((ROOT / "data" / "three_sixty" / f"{mid}.json").read_text(encoding="utf-8")):
            frames[fr["event_uuid"]] = fr
    return events, frames


def juvian(events):
    return [e for e in events if (e.get("player") or {}).get("id") == JULIAN]


def shot_rows(events, frames):
    rows = []
    for e in juvian(events):
        if e["type"]["name"] != "Shot":
            continue
        shot = e["shot"]
        fr = frames.get(e["id"])
        nearest = None
        if fr:
            loc = e["location"]
            rivals = [p for p in fr["freeze_frame"] if not p["teammate"] and not p["keeper"] and p.get("location")]
            if rivals:
                nearest = min(((loc[0] - p["location"][0]) ** 2 + (loc[1] - p["location"][1]) ** 2) ** 0.5
                              for p in rivals)
        rows.append({
            "match": e["match_id"], "minute": e["minute"], "x": e["location"][0], "y": e["location"][1],
            "xg": shot["statsbomb_xg"], "outcome": shot["outcome"]["name"],
            "goal": shot["outcome"]["name"] == "Goal",
            "pattern": shot["play_pattern"]["name"] if "play_pattern" in shot else e["play_pattern"]["name"],
            "assist": shot.get("key_pass_id"),
            "defender_m": nearest,
        })
    return pd.DataFrame(rows)


def pressure_stats(events, frames):
    receipts = [e for e in juvian(events) if e["type"]["name"] == "Ball Receipt*"]
    under = sum(1 for e in receipts if e.get("under_pressure"))
    pressures = sum(1 for e in juvian(events) if e["type"]["name"] == "Pressure")
    press_locs = [(e["location"][0], e["location"][1]) for e in juvian(events)
                  if e["type"]["name"] == "Pressure" and e.get("location")]
    assists = sum(1 for e in juvian(events) if e["type"]["name"] == "Pass"
                  and e.get("pass", {}).get("shot_assist"))
    return len(receipts), under, pressures, press_locs, assists


def save(fig, name):
    fig.text(0.99, 0.005, "Data: StatsBomb", ha="right", fontsize=7, color="0.55")
    fig.savefig(ROOT / "output" / name, dpi=160, bbox_inches="tight")


def shot_map(shots):
    pitch = Pitch(pitch_type="statsbomb", pitch_color="#22312b", line_color="#c7d5cc")
    fig = Figure(figsize=(11, 7))
    ax = fig.add_subplot()
    pitch.draw(ax=ax)
    for _, r in shots.iterrows():
        color = "#7CFC00" if r.goal else "#ff7f0e" if r.outcome in ("Saved", "Saved To Post") else "#bdbdbd"
        size = 120 + 2600 * r.xg
        ax.scatter(r.x, r.y, s=size, color=color, alpha=0.75, edgecolors="white", linewidths=0.8, zorder=3)
        if r.goal:
            ax.annotate(f"{r.minute}'", (r.x, r.y), fontsize=9, color="white",
                        xytext=(4, 5), textcoords="offset points", zorder=4)
    ax.set_title("Julián Álvarez — shots, 2022 World Cup\n(size = xG · green = goal · orange = saved · grey = other)",
                 color="white", fontsize=12)
    fig.patch.set_facecolor("#22312b")
    save(fig, "shot_map.png")


def xg_by_match(shots):
    fig = Figure(figsize=(10, 5))
    ax = fig.add_subplot()
    g = shots.groupby("match").agg(xg=("xg", "sum"), goals=("goal", "sum")).reindex(ORDER).fillna(0)
    labels = [MATCHES[m][0] for m in ORDER]
    ax.bar(labels, g.xg, color="#4472a8", width=0.6)
    ax.scatter(labels, g.goals, color="#d62728", zorder=3, s=60, label="goals")
    for i, (xg, gl) in enumerate(zip(g.xg, g.goals)):
        ax.annotate(f"{xg:.2f}", (i, xg), textcoords="offset points", xytext=(0, 4), ha="center", fontsize=9)
    ax.set_ylabel("xG / goals")
    ax.set_title("xG vs actual goals by match — Julián Álvarez, 2022 World Cup")
    ax.legend()
    fig.autofmt_xdate()
    save(fig, "xg_by_match.png")


def pressure_map(press_locs):
    pitch = Pitch(pitch_type="statsbomb", pitch_color="#1a1a2e", line_color="#8899aa")
    fig = Figure(figsize=(11, 7))
    ax = fig.add_subplot()
    pitch.draw(ax=ax)
    xs, ys = zip(*press_locs)
    pitch.kdeplot(xs, ys, ax=ax, cmap="plasma", fill=True, levels=100, alpha=0.6)
    ax.set_title("Julián Álvarez — pressure events (heatmap), 2022 World Cup", color="white", fontsize=12)
    fig.patch.set_facecolor("#1a1a2e")
    save(fig, "pressure_map.png")


def shot_pressure(shots):
    fig = Figure(figsize=(9, 5))
    ax = fig.add_subplot()
    s = shots.dropna(subset=["defender_m"])
    colors = s.goal.map({True: "#2ca02c", False: "#4472a8"})
    ax.scatter(s.defender_m, s.xg, c=colors, s=90, alpha=0.8, edgecolors="white")
    ax.set_xlabel("distance to nearest defender at shot (m)")
    ax.set_ylabel("xG")
    ax.set_title("Shot quality vs. pressure — Julián Álvarez (green = goal)")
    save(fig, "shot_pressure.png")


def main():
    events, frames = load()
    shots = shot_rows(events, frames)
    n_rec, n_under, n_press, press_locs, n_assists = pressure_stats(events, frames)

    goals = int(shots.goal.sum())
    print(f"partidos: {shots.match.nunique()} | tiros: {len(shots)} | goles: {goals}")
    print(f"xG total: {shots.xg.sum():.2f} | xG/tiro: {shots.xg.mean():.3f}")
    print(f"goles de {shots.xg.sum():.2f} xG -> {goals - shots.xg.sum():+.2f}")
    print(f"asistencias de tiro (sus pases que terminan en tiro): {n_assists}")
    s = shots.dropna(subset=["defender_m"])
    print(f"presión media al tirar: {s.defender_m.mean():.2f} m (mediana {s.defender_m.median():.2f})")
    print(f"tiros con defensor <2m: {(s.defender_m < 2).sum()} de {len(s)}")
    print(f"recepciones: {n_rec} ({n_under} bajo presión, {100*n_under/max(n_rec,1):.0f}%) | eventos Pressure: {n_press}")

    shot_map(shots)
    xg_by_match(shots)
    pressure_map(press_locs)
    shot_pressure(shots)
    print("figuras en output/")


if __name__ == "__main__":
    main()
