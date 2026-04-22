import pandas as pd
import plotly.graph_objects as go


ZONE_COLORS = {
    "Z1": "#6ee7b7",
    "Z2": "#34d399",
    "Z3": "#fbbf24",
    "Z4": "#fb7185",
    "Z5": "#b91c1c",
}
ZONE_LABELS = ["Z1", "Z2", "Z3", "Z4", "Z5"]
ZONE_CENTERS = {
    "Z1": 0.55,
    "Z2": 0.66,
    "Z3": 0.77,
    "Z4": 0.86,
    "Z5": 0.95,
}


def _format_pace(minutes_per_km: float | None) -> str:
    if minutes_per_km is None or pd.isna(minutes_per_km):
        return "-"

    total_seconds = int(minutes_per_km * 60)
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes}:{seconds:02d} /km"


def _base_figure(title: str, height: int = 360) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        title=title,
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#fffaf2",
        margin=dict(l=36, r=24, t=64, b=42),
        font=dict(family="Georgia, serif", color="#1f2937", size=13),
        title_font=dict(size=20, color="#111827"),
        xaxis=dict(
            showgrid=False,
            linecolor="rgba(31,41,55,0.14)",
            tickfont=dict(color="#6b7280"),
        ),
        yaxis=dict(
            gridcolor="rgba(31,41,55,0.08)",
            zeroline=False,
            tickfont=dict(color="#6b7280"),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            bgcolor="rgba(255,255,255,0.72)",
        ),
    )
    return fig


def _empty_chart(message: str, include_plotlyjs: str | bool = False, height: int = 320) -> str:
    fig = _base_figure(message, height=height)
    fig.add_annotation(
        text=message,
        x=0.5,
        y=0.5,
        showarrow=False,
        xref="paper",
        yref="paper",
        font=dict(size=16, color="#6b7280"),
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return fig.to_html(full_html=False, include_plotlyjs=include_plotlyjs)


def _estimate_hr_metrics(df: pd.DataFrame) -> tuple[pd.DataFrame, float, float]:
    observed_max = pd.to_numeric(df.get("max_heartrate"), errors="coerce").max()
    avg_max = pd.to_numeric(df.get("average_heartrate"), errors="coerce").max()
    estimated_max_hr = observed_max if pd.notna(observed_max) else avg_max + 8 if pd.notna(avg_max) else 190.0
    threshold_hr = estimated_max_hr * 0.88

    df["hr_ratio"] = pd.to_numeric(df["average_heartrate"], errors="coerce") / estimated_max_hr
    df["max_hr_ratio"] = pd.to_numeric(df["max_heartrate"], errors="coerce") / estimated_max_hr

    zone_bins = [0, 0.60, 0.72, 0.82, 0.90, 10]
    df["hr_zone"] = pd.cut(
        df["hr_ratio"],
        bins=zone_bins,
        labels=ZONE_LABELS,
        include_lowest=True,
    )

    load_ratio = (pd.to_numeric(df["average_heartrate"], errors="coerce") / threshold_hr).clip(lower=0.5)
    df["training_load"] = (df["duration_min"] * (load_ratio ** 2) * 10).fillna(df["duration_min"] * 0.6)
    return df, float(estimated_max_hr), float(threshold_hr)


def _estimate_session_zone_distribution(row: pd.Series) -> dict[str, float]:
    avg_ratio = row.get("hr_ratio")
    max_ratio = row.get("max_hr_ratio")
    if pd.isna(avg_ratio):
        return {zone: 0.0 for zone in ZONE_LABELS}

    scores = {}
    for zone in ZONE_LABELS:
        center = ZONE_CENTERS[zone]
        avg_score = max(0.0, 1 - abs(center - avg_ratio) / 0.14)
        max_score = 0.0 if pd.isna(max_ratio) else max(0.0, 1 - abs(center - max_ratio) / 0.10)
        scores[zone] = avg_score + 0.35 * max_score

    total = sum(scores.values()) or 1.0
    return {zone: round(score / total * 100, 1) for zone, score in scores.items()}


def _build_weekly_volume_chart(weekly: pd.DataFrame) -> str:
    if weekly.empty:
        return _empty_chart("Volume hebdomadaire indisponible", "cdn")

    fig = _base_figure("Kilometrage et denivele par semaine", height=410)
    fig.add_trace(
        go.Bar(
            x=weekly["week"],
            y=weekly["distance_km"],
            name="Km",
            marker=dict(
                color="rgba(232, 93, 4, 0.82)",
                line=dict(color="#c2410c", width=1.2),
            ),
            hovertemplate="Semaine %{x}<br>%{y:.1f} km<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=weekly["week"],
            y=weekly["elevation_gain"],
            mode="lines+markers",
            name="Denivele",
            line=dict(color="#0f766e", width=3, shape="spline"),
            marker=dict(size=9, color="#ecfdf5", line=dict(color="#0f766e", width=2)),
            hovertemplate="Semaine %{x}<br>%{y:.0f} m D+<extra></extra>",
            yaxis="y2",
        )
    )
    fig.update_layout(
        yaxis=dict(title="Kilometres"),
        yaxis2=dict(
            title="Denivele (m)",
            overlaying="y",
            side="right",
            showgrid=False,
        ),
    )
    return fig.to_html(full_html=False, include_plotlyjs="cdn")


def _build_session_zone_chart(session_label: str, distribution: dict[str, float]) -> str:
    if not any(distribution.values()):
        return _empty_chart("Zones cardiaques indisponibles pour cette seance", False, height=420)

    fig = _base_figure(f"Repartition des zones estimee - {session_label}", height=420)
    fig.add_trace(
        go.Bar(
            x=ZONE_LABELS,
            y=[distribution[zone] for zone in ZONE_LABELS],
            marker_color=[ZONE_COLORS[zone] for zone in ZONE_LABELS],
            text=[f"{distribution[zone]:.0f}%" for zone in ZONE_LABELS],
            textposition="outside",
            hovertemplate="Zone %{x}<br>%{y:.1f}% de la seance<extra></extra>",
            showlegend=False,
        )
    )
    fig.update_yaxes(title="% estime de la seance", ticksuffix="%", range=[0, 100])
    return fig.to_html(full_html=False, include_plotlyjs=False)


def _build_load_chart(load_df: pd.DataFrame) -> str:
    if load_df.empty:
        return _empty_chart("Charge et fatigue indisponibles", False, height=520)

    fig = _base_figure("Charge, fatigue et forme", height=560)
    fig.add_trace(
        go.Bar(
            x=load_df["day_label"],
            y=load_df["daily_load"],
            name="Charge quotidienne",
            marker_color="rgba(14, 116, 144, 0.28)",
            hovertemplate="Jour %{x}<br>Charge %{y:.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=load_df["day_label"],
            y=load_df["fatigue"],
            mode="lines",
            line=dict(color="#fb7185", width=3, shape="spline"),
            name="Fatigue (ATL 7j)",
            hovertemplate="Jour %{x}<br>Fatigue %{y:.1f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=load_df["day_label"],
            y=load_df["fitness"],
            mode="lines",
            line=dict(color="#0f766e", width=3, shape="spline"),
            name="Charge (CTL 28j)",
            hovertemplate="Jour %{x}<br>Charge %{y:.1f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=load_df["day_label"],
            y=load_df["form"],
            mode="lines",
            line=dict(color="#7c3aed", width=2, dash="dot"),
            name="Forme",
            hovertemplate="Jour %{x}<br>Forme %{y:.1f}<extra></extra>",
            yaxis="y2",
        )
    )
    fig.update_layout(
        yaxis=dict(title="Charge"),
        yaxis2=dict(
            title="Forme",
            overlaying="y",
            side="right",
            showgrid=False,
            zeroline=True,
            zerolinecolor="rgba(124,58,237,0.20)",
        ),
    )
    return fig.to_html(full_html=False, include_plotlyjs=False)


def build_dashboard_context(activities_data: list[dict]) -> dict:
    if not activities_data:
        return {
            "activities": [],
            "total_distance": 0.0,
            "total_duration": 0.0,
            "average_pace": "-",
            "average_hr": "-",
            "current_fitness": 0,
            "graph_weekly_volume": _empty_chart("Aucune activite recente", "cdn"),
            "graph_load_fatigue": _empty_chart("Aucune activite recente", False, 520),
            "session_zone_charts": [],
        }

    df = pd.DataFrame(activities_data)
    for column in ["name", "type", "average_heartrate", "max_heartrate", "total_elevation_gain"]:
        if column not in df.columns:
            df[column] = None

    df["date"] = pd.to_datetime(df["start_date"])
    df["distance_km"] = pd.to_numeric(df["distance"], errors="coerce").fillna(0) / 1000
    df["duration_min"] = pd.to_numeric(df["moving_time"], errors="coerce").fillna(0) / 60
    df["pace"] = df["duration_min"].where(df["distance_km"] > 0).div(
        df["distance_km"].where(df["distance_km"] > 0)
    )
    df["week"] = df["date"].dt.strftime("%Y-W%V")
    df["display_date"] = df["date"].dt.strftime("%d/%m/%Y")
    df["average_heartrate"] = pd.to_numeric(df["average_heartrate"], errors="coerce")
    df["max_heartrate"] = pd.to_numeric(df["max_heartrate"], errors="coerce")
    df["elevation_gain"] = pd.to_numeric(df["total_elevation_gain"], errors="coerce").fillna(0)

    df = df[df["type"].fillna("Run").isin(["Run", "TrailRun", "VirtualRun", "Workout"])].copy()
    df, estimated_max_hr, threshold_hr = _estimate_hr_metrics(df)

    weekly = (
        df.groupby("week", as_index=False)
        .agg(
            distance_km=("distance_km", "sum"),
            elevation_gain=("elevation_gain", "sum"),
        )
    )

    daily_load = (
        df.assign(day=df["date"].dt.normalize())
        .groupby("day", as_index=False)["training_load"]
        .sum()
        .rename(columns={"training_load": "daily_load"})
    )

    if daily_load.empty:
        load_df = pd.DataFrame()
    else:
        all_days = pd.date_range(daily_load["day"].min(), daily_load["day"].max(), freq="D")
        load_df = (
            daily_load.set_index("day")
            .reindex(all_days, fill_value=0)
            .rename_axis("day")
            .reset_index()
        )
        load_df["fatigue"] = load_df["daily_load"].ewm(span=7, adjust=False).mean()
        load_df["fitness"] = load_df["daily_load"].ewm(span=28, adjust=False).mean()
        load_df["form"] = load_df["fitness"] - load_df["fatigue"]
        load_df["day_label"] = load_df["day"].dt.strftime("%d/%m")

    session_zone_charts = []
    zone_candidates = df.dropna(subset=["average_heartrate"]).sort_values("date", ascending=False).copy()
    for index, row in zone_candidates.iterrows():
        label = f"{row['name']} - {row['display_date']} - {row['distance_km']:.1f} km"
        session_zone_charts.append(
            {
                "id": f"session-zone-{index}",
                "label": label,
                "chart_html": _build_session_zone_chart(label, _estimate_session_zone_distribution(row)),
            }
        )

    activities = (
        df[
            [
                "name",
                "type",
                "date",
                "display_date",
                "distance_km",
                "elevation_gain",
                "duration_min",
                "pace",
                "average_heartrate",
            ]
        ]
        .sort_values("date", ascending=False)
        .assign(
            distance_km=lambda frame: frame["distance_km"].round(2),
            elevation_gain=lambda frame: frame["elevation_gain"].round(0),
            duration_min=lambda frame: frame["duration_min"].round(1),
            pace=lambda frame: frame["pace"].apply(_format_pace),
            average_heartrate=lambda frame: frame["average_heartrate"].round(0).fillna("-"),
        )
        .drop(columns=["date"])
        .rename(columns={"display_date": "date", "average_heartrate": "avg_hr"})
        .to_dict("records")
    )

    average_pace = _format_pace(df["pace"].dropna().mean() if df["pace"].notna().any() else None)
    average_hr = int(df["average_heartrate"].dropna().mean()) if df["average_heartrate"].notna().any() else "-"
    current_fitness = round(load_df["fitness"].iloc[-1], 1) if not load_df.empty else 0

    return {
        "activities": activities,
        "total_distance": round(df["distance_km"].sum(), 1),
        "total_duration": round(df["duration_min"].sum(), 1),
        "average_pace": average_pace,
        "average_hr": average_hr,
        "current_fitness": current_fitness,
        "estimated_max_hr": round(estimated_max_hr),
        "threshold_hr": round(threshold_hr),
        "graph_weekly_volume": _build_weekly_volume_chart(weekly),
        "graph_load_fatigue": _build_load_chart(load_df),
        "session_zone_charts": session_zone_charts,
    }
