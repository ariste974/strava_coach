import json

import pandas as pd


def _format_pace(minutes_per_km: float | None) -> str:
    if minutes_per_km is None or pd.isna(minutes_per_km):
        return "-"

    total_seconds = int(minutes_per_km * 60)
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes}:{seconds:02d} /km"


def build_training_snapshot(activities_data: list[dict]) -> dict:
    if not activities_data:
        return {
            "summary_text": "Aucune activite recente disponible.",
            "athlete_context": {},
        }

    df = pd.DataFrame(activities_data)
    for column in [
        "name",
        "type",
        "average_heartrate",
        "max_heartrate",
        "total_elevation_gain",
    ]:
        if column not in df.columns:
            df[column] = None

    df["date"] = pd.to_datetime(df["start_date"])
    df["distance_km"] = pd.to_numeric(df["distance"], errors="coerce").fillna(0) / 1000
    df["duration_min"] = pd.to_numeric(df["moving_time"], errors="coerce").fillna(0) / 60
    df["elevation_gain"] = pd.to_numeric(df["total_elevation_gain"], errors="coerce").fillna(0)
    df["average_heartrate"] = pd.to_numeric(df["average_heartrate"], errors="coerce")
    df["pace"] = df["duration_min"].where(df["distance_km"] > 0).div(
        df["distance_km"].where(df["distance_km"] > 0)
    )
    df["week"] = df["date"].dt.strftime("%Y-W%V")
    df["display_date"] = df["date"].dt.strftime("%d/%m/%Y")

    runs = df[df["type"].fillna("Run").isin(["Run", "TrailRun", "VirtualRun", "Workout"])].copy()
    if runs.empty:
        runs = df.copy()

    weekly = (
        runs.groupby("week", as_index=False)
        .agg(
            distance_km=("distance_km", "sum"),
            duration_min=("duration_min", "sum"),
            elevation_gain=("elevation_gain", "sum"),
        )
        .sort_values("week", ascending=False)
        .head(8)
        .sort_values("week")
    )
    weekly["pace"] = weekly["duration_min"].where(weekly["distance_km"] > 0).div(
        weekly["distance_km"].where(weekly["distance_km"] > 0)
    )

    recent_activities = (
        runs.sort_values("date", ascending=False)
        .head(12)[
            [
                "display_date",
                "name",
                "type",
                "distance_km",
                "elevation_gain",
                "duration_min",
                "pace",
                "average_heartrate",
            ]
        ]
        .assign(
            distance_km=lambda frame: frame["distance_km"].round(1),
            elevation_gain=lambda frame: frame["elevation_gain"].round(0),
            duration_min=lambda frame: frame["duration_min"].round(0),
            pace=lambda frame: frame["pace"].apply(_format_pace),
            average_heartrate=lambda frame: frame["average_heartrate"].round(0),
        )
        .rename(columns={"display_date": "date", "average_heartrate": "avg_hr"})
        .to_dict("records")
    )

    athlete_context = {
        "total_distance_km": round(runs["distance_km"].sum(), 1),
        "total_duration_min": round(runs["duration_min"].sum(), 0),
        "average_pace": _format_pace(runs["pace"].dropna().mean() if runs["pace"].notna().any() else None),
        "average_hr": (
            int(runs["average_heartrate"].dropna().mean())
            if runs["average_heartrate"].notna().any()
            else None
        ),
        "weekly_summary": [
            {
                "week": row["week"],
                "distance_km": round(row["distance_km"], 1),
                "duration_min": round(row["duration_min"], 0),
                "elevation_gain": round(row["elevation_gain"], 0),
                "average_pace": _format_pace(row["pace"]),
            }
            for _, row in weekly.iterrows()
        ],
        "recent_activities": recent_activities,
    }

    summary_text = json.dumps(athlete_context, ensure_ascii=False, indent=2)
    return {
        "summary_text": summary_text,
        "athlete_context": athlete_context,
    }


def build_coach_system_prompt(training_snapshot: str) -> str:
    return (
        "Tu es un coach de course a pied expert, pragmatique et pedagogique. "
        "Tu conseilles l'athlete uniquement a partir du contexte fourni. "
        "Tu reponds toujours en francais. "
        "Quand une donnee semble insuffisante ou estimee, tu le dis clairement. "
        "Tu ne donnes pas de diagnostic medical et tu encourages la prudence en cas de douleur, blessure ou fatigue anormale. "
        "Tu privilegies des recommandations concretes, actionnables, personnalisees, avec volumes, intensites, objectifs de seance et points de vigilance. "
        "Tu peux proposer des semaines types, des ajustements de charge, des seances ciblees et des conseils de recuperation. "
        "Voici le contexte d'entrainement actuel de l'athlete au format JSON:\n"
        f"{training_snapshot}"
    )
