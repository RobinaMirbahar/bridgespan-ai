# -*- coding: utf-8 -*-
"""
BridgeSpan AI — Global Fleet Bridge-Clearance, Load & Flood-Scour Safety Platform
Modern Mobile-Responsive Fleet Command UI (inspired by Samsara, Hammer & BridgeWatch)
Powered by Gemma 4, Google ADK, OSRM Routing & 4,809 Real FHWA NBI / OSM Bridges.
Author: Robina Mirbahar
"""

import json
from pathlib import Path
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from bridgespan_agent.agent import run_bridgespan_dispatch
from bridgespan_agent.chat import answer_bridge_chat_query
from bridgespan_agent.guardrails import DYNAMIC_BOUNCE_BUFFER_M, meters_to_ft_in, parse_height_to_meters
from bridgespan_agent.tools import (
    BRIDGE_CORRIDORS,
    FLEET_PRESETS,
    get_live_river_scour_and_wind,
    load_sample_nbi_bridges,
)

st.set_page_config(
    page_title="BridgeSpan AI | Global Bridge Strike & Scour Safety",
    page_icon="🌉",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def render_html(raw_html: str) -> None:
    compact = "".join(line.strip() for line in raw_html.splitlines() if line.strip())
    st.markdown(compact, unsafe_allow_html=True)


# ---------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------
if "corridor_id" not in st.session_state:
    st.session_state["corridor_id"] = "BRG-001"
if "vehicle_id" not in st.session_state:
    st.session_state["vehicle_id"] = "TRK-SEMI-136"
if "height_input" not in st.session_state:
    st.session_state["height_input"] = "13'-6\""
if "weight_tons" not in st.session_state:
    st.session_state["weight_tons"] = 34.5
if "high_sided" not in st.session_state:
    st.session_state["high_sided"] = True
if "surge_m" not in st.session_state:
    st.session_state["surge_m"] = 0.15
if "wind_kmh" not in st.session_state:
    st.session_state["wind_kmh"] = 28.0
if "map_mode" not in st.session_state:
    st.session_state["map_mode"] = "CORRIDOR"
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = [
        {
            "role": "assistant",
            "content": "👋 **BridgeSpan Safety Copilot Ready.** Tap any scenario preset above or ask why a bridge was blocked, how Imperial/Metric clearance math works, or which OSRM bypass route is safest.",
        }
    ]

# ---------------------------------------------------------
# Modern Mobile-Responsive Fleet Telematics CSS (Samsara / Hammer / BridgeWatch Style)
# ---------------------------------------------------------
render_html("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600;700&display=swap');

:root { color-scheme: dark; }
html, body, .stApp {
    background: radial-gradient(circle at 15% 0%, #131c31 0%, #090d16 55%, #060910 100%) !important;
    color: #f8fafc !important;
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
}
.block-container {
    padding-top: 1.2rem !important;
    padding-bottom: 2.2rem !important;
    max-width: 1440px !important;
}
header[data-testid="stHeader"] { background: transparent !important; }

/* Touch-Friendly Pill & Action Buttons */
div[data-testid="stButton"] > button {
    background: rgba(17, 25, 40, 0.88) !important;
    color: #e2e8f0 !important;
    border: 1px solid rgba(148, 163, 184, 0.22) !important;
    border-radius: 10px !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    min-height: 42px !important;
    padding: 0.45rem 0.85rem !important;
    transition: all 0.18s cubic-bezier(0.16, 1, 0.3, 1) !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.22) !important;
}
div[data-testid="stButton"] > button:hover {
    border-color: #38bdf8 !important;
    background: rgba(30, 41, 59, 0.95) !important;
    color: #ffffff !important;
    transform: translateY(-1px);
}
div[data-testid="stButton"] > button[kind="primary"] {
    background: linear-gradient(135deg, #f59e0b 0%, #ea580c 100%) !important;
    color: #ffffff !important;
    border: 1px solid rgba(251, 191, 36, 0.65) !important;
    font-weight: 700 !important;
    box-shadow: 0 4px 14px rgba(245, 158, 11, 0.30) !important;
}

/* Top Navigation Header */
.bs-nav {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 12px;
    background: rgba(15, 23, 42, 0.78);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(148, 163, 184, 0.16);
    border-radius: 16px;
    padding: 14px 20px;
    margin-bottom: 16px;
}
.bs-brand {
    display: flex;
    align-items: center;
    gap: 12px;
}
.bs-brand-icon {
    width: 38px;
    height: 38px;
    border-radius: 10px;
    background: linear-gradient(135deg, #f59e0b, #ea580c);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    box-shadow: 0 4px 12px rgba(245, 158, 11, 0.35);
}
.bs-brand-name {
    font-size: 1.15rem;
    font-weight: 800;
    letter-spacing: -0.01em;
    color: #ffffff;
}
.bs-brand-sub {
    font-size: 0.78rem;
    color: #94a3b8;
}
.bs-badges {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
}
.bs-pill {
    font-size: 11.5px;
    font-weight: 600;
    padding: 5px 11px;
    border-radius: 999px;
    background: rgba(30, 41, 59, 0.85);
    border: 1px solid rgba(148, 163, 184, 0.2);
    color: #cbd5e1;
}
.bs-pill-live {
    background: rgba(16, 185, 129, 0.14);
    border: 1px solid rgba(16, 185, 129, 0.4);
    color: #34d399;
}

/* Main Verdict & Highway LED Sign Card */
.bs-verdict-wrap {
    border-radius: 18px;
    padding: 20px 24px;
    margin-bottom: 16px;
    border: 1px solid;
    display: grid;
    grid-template-columns: 1.35fr 1fr;
    gap: 18px;
    align-items: center;
}
.verdict-danger {
    background: linear-gradient(135deg, rgba(127, 29, 29, 0.38) 0%, rgba(15, 23, 42, 0.92) 100%);
    border-color: rgba(239, 68, 68, 0.55);
}
.verdict-warn {
    background: linear-gradient(135deg, rgba(120, 53, 15, 0.38) 0%, rgba(15, 23, 42, 0.92) 100%);
    border-color: rgba(245, 158, 11, 0.55);
}
.verdict-safe {
    background: linear-gradient(135deg, rgba(6, 78, 59, 0.38) 0%, rgba(15, 23, 42, 0.92) 100%);
    border-color: rgba(16, 185, 129, 0.50);
}
.bs-corridor-tag {
    font-size: 11.5px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #38bdf8;
    margin-bottom: 4px;
}
.bs-bridge-title {
    font-size: clamp(1.2rem, 2.2vw, 1.65rem);
    font-weight: 800;
    color: #ffffff;
    line-height: 1.2;
    margin-bottom: 8px;
}
.bs-led-sign {
    font-family: 'JetBrains Mono', monospace;
    background: #05070c;
    border: 2px solid #334155;
    border-radius: 12px;
    padding: 13px 16px;
    text-align: center;
    box-shadow: inset 0 0 18px rgba(0, 0, 0, 0.85);
}
.bs-led-label {
    font-size: 10px;
    letter-spacing: 0.14em;
    color: #64748b;
    margin-bottom: 5px;
}
.bs-led-text {
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.04em;
}

/* Visual Clearance & Load Meter Cards */
.bs-kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 18px;
}
.bs-card {
    background: rgba(15, 23, 42, 0.78);
    border: 1px solid rgba(148, 163, 184, 0.16);
    border-radius: 14px;
    padding: 16px 18px;
}
.bs-card-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 12px;
    font-weight: 600;
    color: #94a3b8;
    margin-bottom: 8px;
}
.bs-card-val {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.32rem;
    font-weight: 700;
    color: #ffffff;
    margin-bottom: 8px;
}
.bs-meter-bg {
    width: 100%;
    height: 7px;
    background: rgba(51, 65, 85, 0.65);
    border-radius: 999px;
    overflow: hidden;
    margin-bottom: 7px;
}
.bs-meter-fill {
    height: 100%;
    border-radius: 999px;
}
.bs-card-sub {
    font-size: 11.5px;
    color: #cbd5e1;
}

/* 4-Gate Traffic Light Cards */
.bs-gate-list {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
    margin-bottom: 14px;
}
.bs-gate-item {
    border-radius: 12px;
    padding: 12px 14px;
    background: rgba(15, 23, 42, 0.82);
    border: 1px solid rgba(148, 163, 184, 0.18);
}
.bs-gate-trip {
    border-color: rgba(239, 68, 68, 0.65);
    background: rgba(127, 29, 29, 0.22);
}
.bs-gate-pass {
    border-color: rgba(16, 185, 129, 0.35);
}

.bs-section-label {
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    color: #94a3b8;
    margin: 6px 0 10px 0;
}

/* Mobile & Tablet Responsive Breakpoints */
@media (max-width: 1024px) {
    .bs-verdict-wrap { grid-template-columns: 1fr; }
    .bs-kpi-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 640px) {
    .block-container { padding-left: 0.75rem !important; padding-right: 0.75rem !important; padding-top: 0.7rem !important; }
    .bs-nav { padding: 12px 14px; border-radius: 12px; }
    .bs-verdict-wrap { padding: 15px; border-radius: 14px; }
    .bs-kpi-grid { grid-template-columns: 1fr; gap: 10px; }
    .bs-gate-list { grid-template-columns: 1fr; }
    div[data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; }
    div[data-testid="column"] { min-width: 47% !important; flex: 1 1 47% !important; }
}
</style>
""")

# ---------------------------------------------------------
# 1. Clean Top Navigation Bar
# ---------------------------------------------------------
render_html("""
<div class="bs-nav">
  <div class="bs-brand">
    <div class="bs-brand-icon">🌉</div>
    <div>
      <div class="bs-brand-name">BridgeSpan AI</div>
      <div class="bs-brand-sub">Global Truck Bridge-Strike, Load &amp; Flood-Scour Safety Platform</div>
    </div>
  </div>
  <div class="bs-badges">
    <span class="bs-pill">4,809 Real FHWA + OSM Spans</span>
    <span class="bs-pill">Gemma 4 + Google ADK + OSRM</span>
    <span class="bs-pill bs-pill-live">● Live Telemetry Active</span>
  </div>
</div>
""")

# ---------------------------------------------------------
# 2. User-Friendly Quick Demo Scenarios (1-Tap Mobile Friendly)
# ---------------------------------------------------------
render_html('<div class="bs-section-label">⚡ Try a Real-World Dispatch Scenario (1-Tap Presets)</div>')
sc1, sc2, sc3, sc4, sc5 = st.columns(5)
with sc1:
    if st.button("🚚 13'-6\" Can-Opener Strike", use_container_width=True):
        st.session_state.update({
            "corridor_id": "BRG-001", "vehicle_id": "TRK-SEMI-136",
            "height_input": "13'-6\"", "weight_tons": 34.5, "high_sided": True,
            "surge_m": 0.15, "wind_kmh": 28.0, "map_mode": "CORRIDOR",
        })
        st.rerun()
with sc2:
    if st.button("🌊 Potomac Flood Scour", use_container_width=True):
        st.session_state.update({
            "corridor_id": "BRG-003", "vehicle_id": "TRK-BOX-106",
            "height_input": "10'-6\"", "weight_tons": 19.5, "high_sided": False,
            "surge_m": 2.40, "wind_kmh": 48.0, "map_mode": "CORRIDOR",
        })
        st.rerun()
with sc3:
    if st.button("🏗️ 42t Crane Load Violation", use_container_width=True):
        st.session_state.update({
            "corridor_id": "BRG-007", "vehicle_id": "TRK-CRANE-42T",
            "height_input": "12'-0\"", "weight_tons": 42.0, "high_sided": False,
            "surge_m": 0.30, "wind_kmh": 25.0, "map_mode": "CORRIDOR",
        })
        st.rerun()
with sc4:
    if st.button("💨 Baku 78 km/h Gale", use_container_width=True):
        st.session_state.update({
            "corridor_id": "BRG-006", "vehicle_id": "TRK-SEMI-136",
            "height_input": "3.85 m", "weight_tons": 24.0, "high_sided": True,
            "surge_m": 0.0, "wind_kmh": 78.0, "map_mode": "CORRIDOR",
        })
        st.rerun()
with sc5:
    if st.button("✅ Safe Box-Truck Pass", use_container_width=True):
        st.session_state.update({
            "corridor_id": "BRG-001", "vehicle_id": "TRK-BOX-106",
            "height_input": "10'-6\"", "weight_tons": 12.0, "high_sided": False,
            "surge_m": 0.10, "wind_kmh": 20.0, "map_mode": "CORRIDOR",
        })
        st.rerun()

# ---------------------------------------------------------
# 3. Clean Mobile-Responsive Corridor & Vehicle Selector Bar
# ---------------------------------------------------------
CORRIDOR_LABELS = {
    k: f"[{v['city_country'].split(',')[-1].strip()}] {v['short_label']}"
    for k, v in BRIDGE_CORRIDORS.items()
}
VEHICLE_LABELS = {
    "TRK-SEMI-136": "53-ft Semi-Trailer (13'-6\" / 34.5 t)",
    "TRK-BOX-106": "Urban Box Delivery Truck (10'-6\" / 12.0 t)",
    "TRK-CRANE-42T": "4-Axle Mobile Crane (12'-0\" / 42.0 t)",
    "CUSTOM": "Custom Vehicle Dimensions",
}

sel_c1, sel_c2, sel_c3 = st.columns([1.6, 1.3, 0.9])
with sel_c1:
    chosen_cid = st.selectbox(
        "📍 Monitored Global Bridge Corridor (US • Australia • Azerbaijan • Pakistan)",
        options=list(BRIDGE_CORRIDORS.keys()),
        index=list(BRIDGE_CORRIDORS.keys()).index(st.session_state["corridor_id"]),
        format_func=lambda cid: CORRIDOR_LABELS[cid],
    )
    if chosen_cid != st.session_state["corridor_id"]:
        st.session_state["corridor_id"] = chosen_cid
        st.session_state["surge_m"] = float(BRIDGE_CORRIDORS[chosen_cid]["default_surge_m"])
        st.session_state["wind_kmh"] = float(BRIDGE_CORRIDORS[chosen_cid]["default_wind_kmh"])
        st.session_state["map_mode"] = "CORRIDOR"
        st.rerun()

with sel_c2:
    curr_vid = st.session_state["vehicle_id"] if st.session_state["vehicle_id"] in VEHICLE_LABELS else "CUSTOM"
    chosen_vid = st.selectbox(
        "🚛 Commercial Vehicle Profile",
        options=list(VEHICLE_LABELS.keys()),
        index=list(VEHICLE_LABELS.keys()).index(curr_vid),
        format_func=lambda vid: VEHICLE_LABELS[vid],
    )
    if chosen_vid != curr_vid and chosen_vid != "CUSTOM":
        preset = FLEET_PRESETS.get(chosen_vid)
        st.session_state["vehicle_id"] = chosen_vid
        if preset:
            st.session_state["height_input"] = preset["default_height"]
            st.session_state["weight_tons"] = float(preset["default_tons"])
            st.session_state["high_sided"] = bool(preset["is_high_sided"])
        elif chosen_vid == "TRK-BOX-106":
            st.session_state["height_input"] = "10'-6\""
            st.session_state["weight_tons"] = 12.0
            st.session_state["high_sided"] = False
        elif chosen_vid == "TRK-CRANE-42T":
            st.session_state["height_input"] = "12'-0\""
            st.session_state["weight_tons"] = 42.0
            st.session_state["high_sided"] = False
        st.rerun()

with sel_c3:
    st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
    world_lbl = "📍 Zoom to Active Bridge" if st.session_state["map_mode"] == "GLOBAL" else "🌍 View All 8 Global Spans"
    if st.button(world_lbl, type="primary" if st.session_state["map_mode"] == "GLOBAL" else "secondary", use_container_width=True):
        st.session_state["map_mode"] = "GLOBAL" if st.session_state["map_mode"] == "CORRIDOR" else "CORRIDOR"
        st.rerun()

with st.expander("🎛️ Fine-Tune Truck Height (`13'-6\"` or `3.89 m`), Gross Axle Mass, River Flood Surge & Wind", expanded=False):
    ctl1, ctl2, ctl3, ctl4 = st.columns(4)
    with ctl1:
        h_in = st.text_input("Declared Vehicle Height", value=st.session_state["height_input"], help="Supports Imperial (13'-6\", 12ft 4in) or Metric (3.89 m, 389 cm)")
        st.session_state["height_input"] = h_in
    with ctl2:
        w_in = st.slider("Gross Mass (Metric Tons)", 2.0, 60.0, float(st.session_state["weight_tons"]), 0.5)
        st.session_state["weight_tons"] = w_in
    with ctl3:
        s_in = st.slider("River Stage Surge (+m)", 0.0, 3.5, float(st.session_state["surge_m"]), 0.05)
        st.session_state["surge_m"] = s_in
    with ctl4:
        g_in = st.slider("Deck Crosswind Gust (km/h)", 0.0, 120.0, float(st.session_state["wind_kmh"]), 1.0)
        st.session_state["wind_kmh"] = g_in

# ---------------------------------------------------------
# Execute Deterministic Civil Guardrails + Agent Pipeline
# ---------------------------------------------------------
spec = BRIDGE_CORRIDORS[st.session_state["corridor_id"]]
try:
    parsed_h_m = parse_height_to_meters(st.session_state["height_input"])
    valid_height_str = st.session_state["height_input"]
    parse_error = None
except ValueError as exc:
    parsed_h_m = 4.115
    valid_height_str = "13'-6\""
    parse_error = str(exc)

env_state = get_live_river_scour_and_wind(
    spec["corridor_id"],
    override_surge_m=st.session_state["surge_m"],
    override_wind_kmh=st.session_state["wind_kmh"],
)

advisory = run_bridgespan_dispatch(
    corridor_id=spec["corridor_id"],
    vehicle_class=VEHICLE_LABELS.get(st.session_state["vehicle_id"], "Commercial Freight"),
    raw_vehicle_height=valid_height_str,
    vehicle_gross_tons=st.session_state["weight_tons"],
    is_high_sided=st.session_state["high_sided"],
    river_stage_surge_m=st.session_state["surge_m"],
    wind_gust_kmh=st.session_state["wind_kmh"],
    requested_speed_kmh=80,
)

if parse_error:
    st.warning(f"Height format `{st.session_state['height_input']}` could not be parsed — using safe fallback `13'-6\"` (`4.12 m`).")

# ---------------------------------------------------------
# 4. High-Clarity Dispatch Verdict Banner & Roadside LED Gantry Sign
# ---------------------------------------------------------
is_danger = advisory.dispatch_status in {
    "DIVERT_OVERHEIGHT_STRIKE_PREVENTED",
    "DIVERT_OVERWEIGHT_LOAD_LIMIT",
    "CLOSE_BRIDGE_SCOUR_INTERLOCK",
}
is_warn = advisory.dispatch_status == "PROCEED_CLAMP_SPEED_50KMH"

verdict_cls = "verdict-danger" if is_danger else ("verdict-warn" if is_warn else "verdict-safe")
led_color = "#f87171" if is_danger else ("#fbbf24" if is_warn else "#34d399")
human_status = {
    "DIVERT_OVERHEIGHT_STRIKE_PREVENTED": "🛑 BRIDGE STRIKE PREVENTED — AUTO-REROUTED TO HIGH-CLEARANCE BYPASS",
    "DIVERT_OVERWEIGHT_LOAD_LIMIT": "🛑 AXLE TONNAGE EXCEEDED — AUTO-REROUTED AROUND LOAD-POSTED SPAN",
    "CLOSE_BRIDGE_SCOUR_INTERLOCK": "🌊 HYDRAULIC PIER-SCOUR CLOSURE — SPAN LOCKED & DETOURED",
    "PROCEED_CLAMP_SPEED_50KMH": "⚠️ CROSSWIND ROLLOVER PROTECTION — SPEED CLAMPED TO 50 KM/H",
    "CLEAR_PRIMARY_ROUTE": "✅ ALL 4 SAFETY INTERLOCKS CLEAR — PROCEED ON PRIMARY ROUTE",
}.get(advisory.dispatch_status, advisory.dispatch_status)

clr_badge = (
    spec["posted_sign_label"]
    if "m" in spec["posted_sign_label"].lower()
    else f"{spec['posted_sign_label']} ({spec['posted_clearance_m']:.2f} m)"
) if spec["posted_clearance_m"] > 0 else "Unrestricted Open Deck"

render_html(f"""
<div class="bs-verdict-wrap {verdict_cls}">
  <div>
    <div class="bs-corridor-tag">{spec['corridor_id']} • {spec['city_country']} • Basin: {spec['river_name']}</div>
    <div class="bs-bridge-title">{spec['bridge_name']}</div>
    <div style="font-size:13.5px;font-weight:700;color:{led_color};margin-bottom:6px;">{human_status}</div>
    <div style="font-size:12.5px;color:#cbd5e1;">
      Posted Sign: <b>{clr_badge}</b> &nbsp;•&nbsp;
      Max Operating Load: <b>{spec['operating_limit_tons']:.1f} t</b> &nbsp;•&nbsp;
      Active Route: <b>{spec['detour_road_name'] if not advisory.guardrail_interlock_passed else 'Direct Primary Corridor'}</b>
    </div>
  </div>
  <div class="bs-led-sign">
    <div class="bs-led-label">LIVE HIGHWAY OVERHEAD LED GANTRY SIGN</div>
    <div class="bs-led-text" style="color:{led_color};">{advisory.vms_sign_banner}</div>
  </div>
</div>
""")

# ---------------------------------------------------------
# 5. Visual Progress-Meter Telemetry Cards (At-a-Glance Understanding)
# ---------------------------------------------------------
eff_truck_h = parsed_h_m + DYNAMIC_BOUNCE_BUFFER_M
if spec["posted_clearance_m"] > 0:
    h_pct = min(100, int((eff_truck_h / spec["posted_clearance_m"]) * 100))
    h_bar_col = "#ef4444" if eff_truck_h > spec["posted_clearance_m"] else "#10b981"
    h_sub = f"Margin: {advisory.effective_clearance_margin_m:+.2f} m (incl. 0.15m bounce)"
else:
    h_pct = 28
    h_bar_col = "#10b981"
    h_sub = "Open deck — no overhead beam hazard"

w_pct = min(100, int((st.session_state["weight_tons"] / max(spec["operating_limit_tons"], 1.0)) * 100))
w_bar_col = "#ef4444" if st.session_state["weight_tons"] > spec["operating_limit_tons"] else "#10b981"

scour_pct = min(100, int((env_state["river_stage_surge_m"] / 1.80) * 100))
scour_tripped = bool(spec["scour_critical"] and env_state["river_stage_surge_m"] >= 1.80)
s_bar_col = "#ef4444" if scour_tripped else ("#f59e0b" if env_state["wind_gust_kmh"] >= 65.0 else "#10b981")

route_pct = 100 if advisory.extra_detour_km > 0 else 55
r_bar_col = "#10b981" if advisory.extra_detour_km == 0 else "#38bdf8"

render_html(f"""
<div class="bs-kpi-grid">
  <div class="bs-card">
    <div class="bs-card-top"><span>📏 Truck Height vs. Sign</span><span>ft-in ⇄ m</span></div>
    <div class="bs-card-val">{parsed_h_m:.2f} m <span style="font-size:13px;color:#94a3b8;">({meters_to_ft_in(parsed_h_m)})</span></div>
    <div class="bs-meter-bg"><div class="bs-meter-fill" style="width:{h_pct}%;background:{h_bar_col};"></div></div>
    <div class="bs-card-sub">{h_sub}</div>
  </div>
  <div class="bs-card">
    <div class="bs-card-top"><span>⚖️ Gross Axle Mass</span><span>FHWA Item 064</span></div>
    <div class="bs-card-val">{st.session_state['weight_tons']:.1f} t <span style="font-size:13px;color:#94a3b8;">/ {spec['operating_limit_tons']:.1f} t</span></div>
    <div class="bs-meter-bg"><div class="bs-meter-fill" style="width:{w_pct}%;background:{w_bar_col};"></div></div>
    <div class="bs-card-sub">{'Overload — Detour Required' if w_pct > 100 and st.session_state['weight_tons'] > spec['operating_limit_tons'] else 'Within Structural Load Rating'}</div>
  </div>
  <div class="bs-card">
    <div class="bs-card-top"><span>🌊 Scour &amp; Crosswind</span><span>Item 113 / Gust</span></div>
    <div class="bs-card-val">+{env_state['river_stage_surge_m']:.2f} m <span style="font-size:13px;color:#94a3b8;">• {env_state['wind_gust_kmh']:.0f} km/h</span></div>
    <div class="bs-meter-bg"><div class="bs-meter-fill" style="width:{scour_pct}%;background:{s_bar_col};"></div></div>
    <div class="bs-card-sub">{'Scour-Critical Pier' if spec['scour_critical'] else 'Stable Foundation'} • Flow {env_state['river_discharge_cms']} m³/s</div>
  </div>
  <div class="bs-card">
    <div class="bs-card-top"><span>🗺️ Verified OSRM Route</span><span>Speed Limit</span></div>
    <div class="bs-card-val">{advisory.route_distance_km:.2f} km <span style="font-size:13px;color:#38bdf8;">@ {advisory.approved_speed_kmh} km/h</span></div>
    <div class="bs-meter-bg"><div class="bs-meter-fill" style="width:{route_pct}%;background:{r_bar_col};"></div></div>
    <div class="bs-card-sub">{f'Safe Truck Bypass (+{advisory.extra_detour_km:.2f} km)' if advisory.extra_detour_km > 0 else 'Direct Primary Route Clear'}</div>
  </div>
</div>
""")

# ---------------------------------------------------------
# 6. Split View: Live Keyless Dark Vector Map + 4-Gate Status & AI Copilot
# ---------------------------------------------------------
col_map, col_ops = st.columns([1.52, 1.0], gap="medium")

with col_map:
    map_hdr = "🌍 Global 8-Corridor Safety Map" if st.session_state["map_mode"] == "GLOBAL" else f"🗺️ Live OSRM Heavy-Truck Routing — {spec['short_label']}"
    render_html(f'<div class="bs-section-label">{map_hdr}</div>')

    all_nodes_json = json.dumps([
        {
            "id": k,
            "name": v["bridge_name"],
            "city": v["city_country"],
            "lat": v["latitude"],
            "lon": v["longitude"],
            "sign": v["posted_sign_label"],
            "tons": v["operating_limit_tons"],
        }
        for k, v in BRIDGE_CORRIDORS.items()
    ])
    is_diverted = "true" if not advisory.guardrail_interlock_passed else "false"
    is_global = "true" if st.session_state["map_mode"] == "GLOBAL" else "false"

    dark_leaflet_html = f"""<!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8"/>
      <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
      <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
      <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
      <style>
        * {{ box-sizing: border-box; }}
        body {{ margin:0; padding:0; background:#090d16; font-family:'Plus Jakarta Sans', -apple-system, sans-serif; }}
        #wrap {{ position:relative; width:100%; height:450px; border:1px solid rgba(148,163,184,0.22); border-radius:14px; overflow:hidden; background:#090d16; }}
        #map {{ width:100%; height:100%; background:#090d16; }}
        .hud-top {{
          position:absolute; top:10px; left:50px; right:10px; z-index:999;
          display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:6px;
          background:rgba(15,23,42,0.88); border:1px solid rgba(148,163,184,0.25); border-radius:10px;
          padding:7px 12px; color:#f1f5f9; font-size:11.5px; font-weight:600; backdrop-filter:blur(8px);
        }}
        .hud-bot {{
          position:absolute; bottom:10px; left:10px; right:10px; z-index:999;
          display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;
          pointer-events:none;
        }}
        .hud-btn {{
          pointer-events:auto; background:rgba(15,23,42,0.92); color:#f8fafc;
          border:1px solid rgba(56,189,248,0.55); border-radius:8px;
          padding:6px 11px; font-size:11.5px; font-weight:600; cursor:pointer;
        }}
        .hud-legend {{
          pointer-events:auto; background:rgba(15,23,42,0.90); border:1px solid rgba(148,163,184,0.25);
          border-radius:8px; padding:6px 11px; color:#e2e8f0; font-size:11.5px; font-weight:600;
        }}
        .leaflet-tile {{ filter: invert(100%) hue-rotate(180deg) brightness(93%) contrast(92%); }}
        .leaflet-popup-content-wrapper, .leaflet-popup-tip {{
          background:#0f172a !important; color:#f8fafc !important; border:1px solid #334155; border-radius:10px;
        }}
        @media (max-width: 600px) {{
          #wrap {{ height: 360px; }}
          .hud-top {{ font-size: 10.5px; padding: 5px 9px; }}
        }}
      </style>
    </head>
    <body>
      <div id="wrap">
        <div id="map"></div>
        <div class="hud-top">
          <div>🌉 <b>{spec['short_label']}</b></div>
          <div style="color:#94a3b8;font-family:monospace;">{spec['latitude']:.4f}, {spec['longitude']:.4f}</div>
        </div>
        <div class="hud-bot">
          <div style="display:flex;gap:6px;">
            <button class="hud-btn" onclick="zoomCorridor()">📍 Corridor View</button>
            <button class="hud-btn" onclick="zoomWorld()">🌍 All 8 Global Spans</button>
          </div>
          <div class="hud-legend">
            <span style="color:#f87171;">- - Blocked Bridge</span> &nbsp;|&nbsp;
            <span style="color:#34d399;">━━ Safe Truck Route</span>
          </div>
        </div>
      </div>
      <script>
        const nodes = {all_nodes_json};
        const blat = {spec['latitude']}, blon = {spec['longitude']};
        const olat = {spec['origin_lat']}, olon = {spec['origin_lon']};
        const dlat = {spec['dest_lat']}, dlon = {spec['dest_lon']};
        const vlat = {spec['detour_waypoint_lat']}, vlon = {spec['detour_waypoint_lon']};
        const diverted = {is_diverted};
        const startGlobal = {is_global};

        const map = L.map('map', {{ attributionControl: false }}).setView(startGlobal ? [28.0, 5.0] : [blat, blon], startGlobal ? 2 : 14);
        L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{ maxZoom: 19 }}).addTo(map);

        nodes.forEach(n => {{
          const isCurrent = n.id === "{spec['corridor_id']}";
          const col = isCurrent ? (diverted ? '#ef4444' : '#10b981') : '#f59e0b';
          const m = L.circleMarker([n.lat, n.lon], {{
            radius: isCurrent ? 10 : 6,
            color: '#ffffff',
            weight: isCurrent ? 2.5 : 1.5,
            fillColor: col,
            fillOpacity: 0.95
          }}).addTo(map);
          m.bindPopup(`<div style="font-size:12px;line-height:1.4;"><b>${{n.name}}</b><br/><span style="color:#94a3b8;">${{n.city}}</span><br/>Clearance: <b>${{n.sign}}</b> • Max Load: <b>${{n.tons}}t</b></div>`);
          if (isCurrent && !startGlobal) m.openPopup();
        }});

        L.circleMarker([olat, olon], {{radius:6, color:'#38bdf8', fillColor:'#38bdf8', fillOpacity:0.95}}).addTo(map).bindPopup('🚛 Truck Origin');
        L.circleMarker([dlat, dlon], {{radius:6, color:'#a855f7', fillColor:'#a855f7', fillOpacity:0.95}}).addTo(map).bindPopup('🏁 Destination');

        let corridorBounds = L.latLngBounds([[olat, olon], [blat, blon], [dlat, dlon], [vlat, vlon]]);

        async function drawOsrm() {{
          try {{
            const r1 = await fetch(`https://router.project-osrm.org/route/v1/driving/${{olon}},${{olat}};${{blon}},${{blat}};${{dlon}},${{dlat}}?overview=full&geometries=geojson`);
            const j1 = await r1.json();
            if (j1.routes && j1.routes[0]) {{
              const l1 = L.geoJSON(j1.routes[0].geometry, {{
                style: {{ color: diverted ? '#ef4444' : '#10b981', weight: diverted ? 3.5 : 5.5, dashArray: diverted ? '7,7' : null, opacity: 0.92 }}
              }}).addTo(map);
              if (!diverted && !startGlobal) map.fitBounds(l1.getBounds(), {{padding:[34,34]}});
            }}
            if (diverted) {{
              const r2 = await fetch(`https://router.project-osrm.org/route/v1/driving/${{olon}},${{olat}};${{vlon}},${{vlat}};${{dlon}},${{dlat}}?overview=full&geometries=geojson`);
              const j2 = await r2.json();
              if (j2.routes && j2.routes[0]) {{
                const l2 = L.geoJSON(j2.routes[0].geometry, {{
                  style: {{ color: '#10b981', weight: 5.5, opacity: 0.96 }}
                }}).addTo(map);
                L.circleMarker([vlat, vlon], {{radius:6, color:'#10b981', fillColor:'#10b981', fillOpacity:1}})
                  .addTo(map).bindPopup('✅ Safe Truck Bypass: {spec["detour_road_name"]}');
                if (!startGlobal) map.fitBounds(l2.getBounds(), {{padding:[34,34]}});
              }}
            }}
          }} catch (err) {{
            if (!startGlobal) map.fitBounds(corridorBounds, {{padding:[34,34]}});
          }}
        }}
        drawOsrm();

        window.zoomCorridor = function() {{ map.fitBounds(corridorBounds, {{padding:[34,34]}}); }};
        window.zoomWorld = function() {{ map.setView([28.0, 5.0], 2); }};
      </script>
    </body>
    </html>"""
    components.html(dark_leaflet_html, height=460)

with col_ops:
    render_html('<div class="bs-section-label">🛡️ 4-Gate Civil Safety Interlock Checklist</div>')

    g1_trip = advisory.dispatch_status == "DIVERT_OVERHEIGHT_STRIKE_PREVENTED" or (
        spec["posted_clearance_m"] > 0 and eff_truck_h > spec["posted_clearance_m"]
    )
    g2_trip = st.session_state["weight_tons"] > spec["operating_limit_tons"]
    g3_trip = bool(spec["scour_critical"] and env_state["river_stage_surge_m"] >= 1.80)
    g4_trip = bool(st.session_state["high_sided"] and env_state["wind_gust_kmh"] >= 65.0)

    render_html(f"""
    <div class="bs-gate-list">
      <div class="bs-gate-item {'bs-gate-trip' if g1_trip else 'bs-gate-pass'}">
        <div style="font-size:11px;color:#94a3b8;font-weight:600;">GATE 1 • OVERHEAD CLEARANCE</div>
        <div style="font-size:13px;font-weight:700;color:{'#f87171' if g1_trip else '#34d399'};margin-top:3px;">
          {'🔴 BLOCKED (Strike Risk)' if g1_trip else '🟢 SAFE CLEARANCE'}
        </div>
      </div>
      <div class="bs-gate-item {'bs-gate-trip' if g2_trip else 'bs-gate-pass'}">
        <div style="font-size:11px;color:#94a3b8;font-weight:600;">GATE 2 • AXLE LOAD RATING</div>
        <div style="font-size:13px;font-weight:700;color:{'#f87171' if g2_trip else '#34d399'};margin-top:3px;">
          {'🔴 OVERLOAD (> Item 064)' if g2_trip else '🟢 WITHIN TONNAGE'}
        </div>
      </div>
      <div class="bs-gate-item {'bs-gate-trip' if g3_trip else 'bs-gate-pass'}">
        <div style="font-size:11px;color:#94a3b8;font-weight:600;">GATE 3 • FLOOD PIER SCOUR</div>
        <div style="font-size:13px;font-weight:700;color:{'#f87171' if g3_trip else '#34d399'};margin-top:3px;">
          {'🔴 CLOSED (Surge ≥ 1.8m)' if g3_trip else '🟢 NOMINAL RIVER STAGE'}
        </div>
      </div>
      <div class="bs-gate-item {'bs-gate-trip' if g4_trip else 'bs-gate-pass'}">
        <div style="font-size:11px;color:#94a3b8;font-weight:600;">GATE 4 • DECK CROSSWIND</div>
        <div style="font-size:13px;font-weight:700;color:{'#fbbf24' if g4_trip else '#34d399'};margin-top:3px;">
          {'🟡 CLAMPED TO 50 KM/H' if g4_trip else '🟢 NORMAL DECK WIND'}
        </div>
      </div>
    </div>
    """)

    render_html('<div class="bs-section-label">🤖 Gemma 4 + Google ADK Engineering Copilot</div>')
    q1, q2 = st.columns(2)
    quick_q = None
    with q1:
        if st.button("📏 Explain Clearance Math", use_container_width=True):
            quick_q = f"Explain the ft-in vs meter height conversion and 0.15m bounce margin for {valid_height_str}."
        if st.button("🌊 Pier-Scour Rule", use_container_width=True):
            quick_q = "How does the USGS river surge and FHWA Item 113 pier-scour closure rule work?"
    with q2:
        if st.button("⚖️ Structural Load Limit", use_container_width=True):
            quick_q = f"Is {st.session_state['weight_tons']} metric tons safe across this span?"
        if st.button("🛣️ Safe Truck Detour", use_container_width=True):
            quick_q = "Show the OSRM safe truck bypass detour comparison."

    chat_box = st.container(height=210)
    with chat_box:
        for msg in st.session_state["chat_history"]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    user_prompt = st.chat_input("Ask why a bridge was blocked or request route details...")
    active_query = quick_q or user_prompt
    if active_query:
        st.session_state["chat_history"].append({"role": "user", "content": active_query})
        reply = answer_bridge_chat_query(
            query=active_query,
            corridor_id=spec["corridor_id"],
            advisory=advisory,
            env_state=env_state,
        )
        st.session_state["chat_history"].append({"role": "assistant", "content": reply})
        st.rerun()

# ---------------------------------------------------------
# 7. Clean Visual Dataset Explorer (No Cluttered Raw JSON Tab!)
# ---------------------------------------------------------
render_html('<div class="bs-section-label" style="margin-top:14px;">📊 Explore Real Public Bridge Inventory (4,809 Global Structures)</div>')
tab_osm, tab_nbi = st.tabs([
    "🌍 Global OpenStreetMap Low-Clearance Spans (309)",
    "🌉 2024 US DOT FHWA National Bridge Inventory (4,500)",
])

with tab_osm:
    osm_p = Path(__file__).resolve().parent / "dataset" / "osm_global_low_clearance_bridges.csv"
    if osm_p.exists():
        osm_df = pd.read_csv(osm_p)
        st.dataframe(osm_df.head(40), use_container_width=True, hide_index=True)

with tab_nbi:
    st_sel = st.selectbox("Filter 2024 FHWA NBI Bridges by US State", ["NC", "NY", "MA", "PA", "DC", "MD", "ALL"], index=0)
    rows = load_sample_nbi_bridges(state_code=st_sel, limit=30)
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
