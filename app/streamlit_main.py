from datetime import datetime, timezone

import pandas as pd
import pydeck as pdk
import streamlit as st
from streamlit_calendar import calendar
from supabase import Client, create_client

supabase: Client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

response = supabase.table("events").select("*, venue:venue_id(*)").execute()

rows = []
for event in response.data:
    venue = event["venue"] or {}
    start = event["start_datetime"]
    end = event["end_datetime"]
    if not end:
        dt = datetime.fromisoformat(start).replace(
            hour=23, minute=59, second=59, tzinfo=timezone.utc
        )
        end = dt.isoformat()
    rows.append(
        {
            "lat": venue.get("latitude"),
            "lon": venue.get("longitude"),
            "title": event["title"],
            "start_datetime": start,
            "end_datetime": end,
            "venue": venue.get("name"),
        }
    )

df = pd.DataFrame(rows).dropna(subset=["lat", "lon"])

calendar_events = []
for _, row in df.iterrows():
    calendar_events.append(
        {
            "title": f"{row['title']} @ {row['venue']}",
            "start": row["start_datetime"],
            "end": row["end_datetime"],
        }
    )


col1, col2 = st.columns([1.5, 1])
with col1:
    calendar_state = calendar(
        events=calendar_events,
        options={
            "initialView": "dayGridWeek",
            "headerToolbar": {
                "center": "title",
                "right": "prev,next",
            },
        },
    )

    view = calendar_state.get("eventsSet", {}).get("view", {})
with col2:
    if view and "activeStart" in view:
        active_start = datetime.fromisoformat(view["activeStart"])
        active_end = datetime.fromisoformat(view["activeEnd"])
        mask = (pd.to_datetime(df["end_datetime"]) > active_start) & (
            pd.to_datetime(df["start_datetime"]) < active_end
        )
        map_df = df[mask]
    else:
        map_df = df

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_df,
        get_position=["lon", "lat"],
        get_radius=200,
        get_fill_color=[255, 0, 0, 160],
        pickable=True,
    )
    tooltip = {
        "html": "<b>{title}</b><br/>{venue}",
        "style": {"backgroundColor": "black", "color": "white"},
    }
    st.pydeck_chart(
        pdk.Deck(
            layers=[layer],
            initial_view_state=pdk.ViewState(latitude=60.17, longitude=24.94, zoom=12),
            tooltip=tooltip,
        )
    )
