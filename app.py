# -*- coding: utf-8 -*-
"""
BridgeSpan AI — Global Autonomous Infrastructure & Heavy-Freight Safety Console
Tactical Deep-Tech Interface inspired by Harmattan AI • Powered by Gemma 4, Google ADK & OSRM.
Author: Robina Mirbahar
"""

import json
import streamlit as st
import streamlit.components.v1 as components

from bridgespan_agent.agent import run_bridgespan_dispatch
from bridgespan_agent.chat import answer_bridge_chat_query
from bridgespan_agent.guardrails import meters_to_ft_in, parse_height_to_meters
from bridgespan_agent.tools import (
    BRIDGE_CORRIDORS,
    FLEET_PRESETS,
    get_live_river_scour_and_wind,
    load_sample_nbi_bridges,
)

st.set_page_config(
    page_title="BRIDGESPAN AI // GLOBAL AUTONOMOUS SPAN SAFETY",
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
            "content": "**BRIDGESPAN COMMAND ONLINE.** Select any of the 8 global spans above (USA, Australia, Azerbaijan, Pakistan) or trigger a live overheight / pier-scour / tonnage scenario.",
        }
    ]

# ---------------------------------------------------------
# Harmattan-Inspired Deep-Tech Matte-Obsidian & Hairline Grid CSS
# ---------------------------------------------------------
render_html("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600;700&display=swap');

:root { color-scheme: dark; }
html, body, .stApp {
    background-color: #06080b !important;
    background-image:
        linear-gradient(rgba(255,255,255,0.022) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.022) 1px, transparent 1px);
    background-size: 40px 40px;
    color: #f4f4f5 !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}
.block-container {
    padding-top: 1.6rem !important;
    padding-bottom: 2.0rem !important;
    max-width: 1480px !important;
}
header[data-testid="stHeader"] { background: transparent !important; }

/* Sharp industrial buttons */
div[data-testid="stButton"] > button {
    background: #0c1017 !important;
    color: #e4e4e7 !important;
    border: 1px solid #222936 !important;
    border-radius: 3px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 11.5px !important;
    font-weight: 600 !important;
    letter-spacing: 0.04em !important;
    padding: 0.45rem 0.65rem !important;
    transition: all 0.15s ease !important;
    white-space: nowrap !important;
}
div[data-testid="stButton"] > button:hover {
    border-color: #f59e0b !important;
    color: #ffffff !important;
    background: #131924 !important;
}
div[data-testid="stButton"] > button[kind="primary"] {
    background: #f59e0b !important;
    color: #06080b !important;
    border: 1px solid #fbbf24 !important;
    font-weight: 700 !important;
}

/* Top Telemetry Bar */
.hm-topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 12px;
    border-bottom: 1px solid #1c222d;
    padding-bottom: 12px;
    margin-bottom: 16px;
}
.hm-brand {
    display: flex;
    align-items: center;
    gap: 14px;
}
.hm-logo-mark {
    width: 12px;
    height: 12px;
    background: #f59e0b;
    box-shadow: 0 0 12px rgba(245,158,11,0.85);
}
.hm-brand-title {
    font-family: 'Inter', sans-serif;
    font-weight: 800;
    font-size: 15px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: #ffffff;
}
.hm-meta-strip {
    display: flex;
    align-items: center;
    gap: 18px;
    flex-wrap: wrap;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: #9ca3af;
}
.hm-live-pill {
    color: #10b981;
    border: 1px solid rgba(16,185,129,0.35);
    background: rgba(16,185,129,0.08);
    padding: 3px 9px;
    border-radius: 2px;
    font-weight: 700;
}

/* Hero Command Banner */
.hm-hero {
    background: linear-gradient(180deg, rgba(14,19,28,0.94) 0%, rgba(8,11,16,0.98) 100%);
    border: 1px solid #1e2532;
    position: relative;
    padding: 22px 26px;
    margin-bottom: 16px;
}
.hm-hero::before {
    content: "";
    position: absolute;
    top: -1px; left: -1px;
    width: 14px; height: 14px;
    border-top: 2px solid #f59e0b;
    border-left: 2px solid #f59e0b;
}
.hm-hero::after {
    content: "";
    position: absolute;
    bottom: -1px; right: -1px;
    width: 14px; height: 14px;
    border-bottom: 2px solid #f59e0b;
    border-right: 2px solid #f59e0b;
}
.hm-eyebrow {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    letter-spacing: 0.14em;
    color: #f59e0b;
    text-transform: uppercase;
    margin-bottom: 6px;
}
.hm-headline {
    font-size: clamp(1.35rem, 2.4vw, 2.05rem);
    font-weight: 800;
    letter-spacing: -0.025em;
    color: #ffffff;
    line-height: 1.15;
}
.hm-subline {
    font-size: 0.88rem;
    color: #94a3b8;
    margin-top: 6px;
    max-width: 860px;
}

/* VMS Tactical Banner */
.hm-vms {
    font-family: 'JetBrains Mono', monospace;
    font-size: 12.5px;
    font-weight: 700;
    letter-spacing: 0.08em;
    padding: 12px 18px;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 8px;
    border-left: 4px solid;
}
.vms-crit { background: rgba(239,68,68,0.10); border-color: #ef4444; border-top: 1px solid rgba(239,68,68,0.28); border-right: 1px solid rgba(239,68,68,0.28); border-bottom: 1px solid rgba(239,68,68,0.28); color: #fca5a5; }
.vms-warn { background: rgba(245,158,11,0.10); border-color: #f59e0b; border-top: 1px solid rgba(245,158,11,0.28); border-right: 1px solid rgba(245,158,11,0.28); border-bottom: 1px solid rgba(245,158,11,0.28); color: #fcd34d; }
.vms-pass { background: rgba(16,185,129,0.09); border-color: #10b981; border-top: 1px solid rgba(16,185,129,0.28); border-right: 1px solid rgba(16,185,129,0.28); border-bottom: 1px solid rgba(16,185,129,0.28); color: #6ee7b7; }

/* 4-Column Structural Telemetry Grid */
.hm-kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 16px;
}
.hm-kpi-card {
    background: #0a0e14;
    border: 1px solid #1c2330;
    padding: 16px 18px;
    position: relative;
}
.hm-kpi-idx {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    color: #64748b;
    letter-spacing: 0.12em;
    display: flex;
    justify-content: space-between;
    text-transform: uppercase;
}
.hm-kpi-val {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.35rem;
    font-weight: 700;
    color: #ffffff;
    margin: 8px 0 4px 0;
}
.hm-kpi-foot {
    font-size: 11.5px;
    color: #94a3b8;
}

/* Section Label */
.hm-sec-hdr {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.14em;
    color: #94a3b8;
    text-transform: uppercase;
    margin: 8px 0 8px 0;
    display: flex;
    align-items: center;
    gap: 8px;
}
.hm-sec-hdr span { color: #f59e0b; }

/* Interlock Gate Matrix */
.hm-gate-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
    margin-bottom: 12px;
}
.hm-gate {
    background: #0a0e14;
    border: 1px solid #1c2330;
    padding: 10px 12px;
    font-family: 'JetBrains Mono', monospace;
}
.hm-gate-trip { border-color: rgba(239,68,68,0.65); background: rgba(239,68,68,0.06); }
.hm-gate-ok   { border-color: rgba(16,185,129,0.35); }

@media (max-width: 1024px) {
    .hm-kpi-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 640px) {
    .hm-kpi-grid { grid-template-columns: 1fr; }
    .hm-gate-grid { grid-template-columns: 1fr; }
    .hm-hero { padding: 16px; }
}
</style>
""")

# ---------------------------------------------------------
# 1. Top Tactical Status Header
# ---------------------------------------------------------
render_html("""
<div class="hm-topbar">
  <div class="hm-brand">
    <div class="hm-logo-mark"></div>
    <div class="hm-brand-title">BRIDGESPAN AI <span style="color:#64748b;font-weight:500;">// PHYSICAL INFRASTRUCTURE INTERLOCK</span></div>
  </div>
  <div class="hm-meta-strip">
    <span>CORPUS: <b>4,809 GLOBAL SPANS</b></span>
    <span>ENGINES: <b>GEMMA 4 + GOOGLE ADK + OSRM</b></span>
    <span class="hm-live-pill">● TELEMETRY ONLINE</span>
  </div>
</div>
""")

# ---------------------------------------------------------
# 2. Global Corridor Selector Bar (All 5 Countries Visible Upfront!)
# ---------------------------------------------------------
render_html('<div class="hm-sec-hdr"><span>[01]</span> GLOBAL CORRIDOR NETWORK — SELECT MONITORED SPAN (US • AU • AZ • PK)</div>')

GLOBAL_BUTTONS = [
    ("BRG-001", "[US] DURHAM 11-FT-8"),
    ("BRG-002", "[US] BOSTON STORROW"),
    ("BRG-003", "[US] POTOMAC SCOUR"),
    ("BRG-004", "[AU] MELBOURNE 3.0M"),
    ("BRG-005", "[US] NYC PARKWAY"),
    ("BRG-006", "[AZ] BAKU KHAZRI"),
    ("BRG-007", "[US] PA 22.5T TRUSS"),
    ("BRG-008", "[PK] KARACHI MONSOON"),
]

g_cols = st.columns(4)
for idx, (cid, lbl) in enumerate(GLOBAL_BUTTONS):
    with g_cols[idx % 4]:
        is_sel = st.session_state["corridor_id"] == cid
        if st.button(lbl, key=f"btn_{cid}", type="primary" if is_sel else "secondary", use_container_width=True):
            st.session_state["corridor_id"] = cid
            st.session_state["surge_m"] = float(BRIDGE_CORRIDORS[cid]["default_surge_m"])
            st.session_state["wind_kmh"] = float(BRIDGE_CORRIDORS[cid]["default_wind_kmh"])
            st.session_state["map_mode"] = "CORRIDOR"
            st.rerun()

spec = BRIDGE_CORRIDORS[st.session_state["corridor_id"]]

# ---------------------------------------------------------
# 3. 1-Tap Scenario Triggers & Inline Telemetry Control Deck
# ---------------------------------------------------------
with st.expander("🎛️ LIVE VEHICLE & HYDRAULIC TELEMETRY CONTROLS  (HEIGHT FT-IN / METERS • AXLE TONNAGE • RIVER SCOUR • CROSSWIND)", expanded=True):
    p1, p2, p3, p4, p5 = st.columns(5)
    with p1:
        if st.button("⚡ 13'-6\" STRIKE TRAP", use_container_width=True):
            st.session_state.update({"corridor_id": "BRG-001", "height_input": "13'-6\"", "weight_tons": 34.5, "high_sided": True, "surge_m": 0.15, "wind_kmh": 28.0, "map_mode": "CORRIDOR"})
            st.rerun()
    with p2:
        if st.button("🌊 PIER SCOUR SURGE", use_container_width=True):
            st.session_state.update({"corridor_id": "BRG-003", "height_input": "10'-6\"", "weight_tons": 19.5, "high_sided": False, "surge_m": 2.40, "wind_kmh": 48.0, "map_mode": "CORRIDOR"})
            st.rerun()
    with p3:
        if st.button("⚖️ 42T CRANE OVERLOAD", use_container_width=True):
            st.session_state.update({"corridor_id": "BRG-007", "height_input": "12'-0\"", "weight_tons": 42.0, "high_sided": False, "surge_m": 0.30, "wind_kmh": 25.0, "map_mode": "CORRIDOR"})
            st.rerun()
    with p4:
        if st.button("🌪️ BAKU 78 KM/H GALE", use_container_width=True):
            st.session_state.update({"corridor_id": "BRG-006", "height_input": "3.85 m", "weight_tons": 24.0, "high_sided": True, "surge_m": 0.0, "wind_kmh": 78.0, "map_mode": "CORRIDOR"})
            st.rerun()
    with p5:
        if st.button("🌍 GLOBAL WORLD VIEW", type="primary" if st.session_state["map_mode"] == "GLOBAL" else "secondary", use_container_width=True):
            st.session_state["map_mode"] = "GLOBAL" if st.session_state["map_mode"] == "CORRIDOR" else "CORRIDOR"
            st.rerun()

    ctl1, ctl2, ctl3, ctl4 = st.columns([1.2, 1.1, 1.1, 1.1])
    with ctl1:
        h_in = st.text_input("DECLARED HEIGHT (`13'-6\"` or `3.89 m`)", value=st.session_state["height_input"])
        st.session_state["height_input"] = h_in
    with ctl2:
        w_in = st.slider("GROSS MASS (METRIC TONS)", 2.0, 60.0, float(st.session_state["weight_tons"]), 0.5)
        st.session_state["weight_tons"] = w_in
    with ctl3:
        s_in = st.slider("RIVER SCOUR SURGE (+M)", 0.0, 3.5, float(st.session_state["surge_m"]), 0.05)
        st.session_state["surge_m"] = s_in
    with ctl4:
        g_in = st.slider("DECK CROSSWIND (KM/H)", 0.0, 120.0, float(st.session_state["wind_kmh"]), 1.0)
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
    vehicle_class=FLEET_PRESETS.get(st.session_state["vehicle_id"], FLEET_PRESETS["TRK-SEMI-136"])["vehicle_class"],
    raw_vehicle_height=valid_height_str,
    vehicle_gross_tons=st.session_state["weight_tons"],
    is_high_sided=st.session_state["high_sided"],
    river_stage_surge_m=st.session_state["surge_m"],
    wind_gust_kmh=st.session_state["wind_kmh"],
    requested_speed_kmh=80,
)

# ---------------------------------------------------------
# 4. Harmattan-Style Tactical Hero & VMS Gantry Banner
# ---------------------------------------------------------
clr_hero = f"{spec['posted_clearance_m']:.2f} M ({spec['posted_sign_label']})" if spec["posted_clearance_m"] > 0 else "UNRESTRICTED OPEN DECK"
render_html(f"""
<div class="hm-hero">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:14px;">
    <div>
      <div class="hm-eyebrow">{spec['corridor_id']} // {spec['city_country']} // BASIN: {spec['river_name']}</div>
      <div class="hm-headline">{spec['bridge_name']}</div>
      <div class="hm-subline">Deterministic physical safety layer overriding LLM unit-conversion errors, operating-load violations, and underwater pier-scour hazards in real time.</div>
    </div>
    <div style="font-family:'JetBrains Mono',monospace;font-size:11.5px;background:#06080b;border:1px solid #262f40;padding:10px 14px;min-width:240px;">
      <div style="color:#64748b;">POSTED CLEARANCE</div>
      <div style="color:#f8fafc;font-weight:700;font-size:14px;margin-bottom:4px;">{clr_hero}</div>
      <div style="color:#64748b;">FHWA OPERATING RATING: <b style="color:#f59e0b;">{spec['operating_limit_tons']:.1f} T</b></div>
    </div>
  </div>
</div>
""")

if parse_error:
    st.warning(f"Input format fallback (`{parse_error}`) — evaluated using `13'-6\"` (`4.115 m`).")

vms_cls = (
    "vms-crit"
    if advisory.dispatch_status in {"DIVERT_OVERHEIGHT_STRIKE_PREVENTED", "DIVERT_OVERWEIGHT_LOAD_LIMIT", "CLOSE_BRIDGE_SCOUR_INTERLOCK"}
    else ("vms-warn" if advisory.dispatch_status == "PROCEED_CLAMP_SPEED_50KMH" else "vms-pass")
)
render_html(f"""
<div class="hm-vms {vms_cls}">
  <span>[GANTRY_VMS_OUTPUT] &raquo; {advisory.vms_sign_banner}</span>
  <span>VERDICT: {advisory.dispatch_status}</span>
</div>
""")

# ---------------------------------------------------------
# 5. Responsive 4-Card Precision Telemetry Grid
# ---------------------------------------------------------
margin_txt = (
    f"NET MARGIN: {advisory.effective_clearance_margin_m:+.2f}m (incl. 0.15m bounce)"
    if advisory.effective_clearance_margin_m is not None
    else "OPEN OVERHEAD SPAN"
)
load_state = "TRIPPED // BYPASS" if st.session_state["weight_tons"] > spec["operating_limit_tons"] else "NOMINAL // PASS"
scour_state = "CRITICAL ITEM 113" if spec["scour_critical"] else "NON-SCOUR FOUNDATION"

render_html(f"""
<div class="hm-kpi-grid">
  <div class="hm-kpi-card">
    <div class="hm-kpi-idx"><span>01 // CLEARANCE CHECK</span><span>FT-IN ⇄ M</span></div>
    <div class="hm-kpi-val">{parsed_h_m:.2f}m <span style="font-size:13px;color:#94a3b8;">({meters_to_ft_in(parsed_h_m)})</span></div>
    <div class="hm-kpi-foot">{margin_txt}</div>
  </div>
  <div class="hm-kpi-card">
    <div class="hm-kpi-idx"><span>02 // STRUCTURAL MASS</span><span>ITEM 064</span></div>
    <div class="hm-kpi-val">{st.session_state['weight_tons']:.1f}t <span style="font-size:13px;color:#94a3b8;">/ {spec['operating_limit_tons']:.1f}t</span></div>
    <div class="hm-kpi-foot">{load_state}</div>
  </div>
  <div class="hm-kpi-card">
    <div class="hm-kpi-idx"><span>03 // SCOUR &amp; WIND</span><span>{env_state['usgs_site_id']}</span></div>
    <div class="hm-kpi-val">+{env_state['river_stage_surge_m']:.2f}m <span style="font-size:13px;color:#94a3b8;">• {env_state['wind_gust_kmh']:.0f}km/h</span></div>
    <div class="hm-kpi-foot">{scour_state} • {env_state['river_discharge_cms']} m³/s</div>
  </div>
  <div class="hm-kpi-card">
    <div class="hm-kpi-idx"><span>04 // OSRM VECTOR</span><span>ROUTING</span></div>
    <div class="hm-kpi-val">{advisory.route_distance_km:.2f}km <span style="font-size:13px;color:#f59e0b;">@ {advisory.approved_speed_kmh}km/h</span></div>
    <div class="hm-kpi-foot">{'SAFE BYPASS (+' + str(advisory.extra_detour_km) + ' km)' if advisory.extra_detour_km > 0 else 'DIRECT PRIMARY SPAN'}</div>
  </div>
</div>
""")

# ---------------------------------------------------------
# 6. Tactical Dark CartoDB Map (Global Network + Live OSRM Corridor) & Interlock Console
# ---------------------------------------------------------
col_map, col_ops = st.columns([1.58, 1.0], gap="medium")

with col_map:
    mode_lbl = "GLOBAL 8-CORRIDOR NETWORK VIEW" if st.session_state["map_mode"] == "GLOBAL" else f"TACTICAL OSRM VECTOR // {spec['short_label'].upper()}"
    render_html(f'<div class="hm-sec-hdr"><span>[02]</span> {mode_lbl}</div>')

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
        body {{ margin:0; padding:0; background:#06080b; font-family:'JetBrains Mono', monospace; }}
        #wrap {{ position:relative; width:100%; height:465px; border:1px solid #1e2532; background:#06080b; }}
        #map {{ width:100%; height:100%; background:#06080b; }}
        .hud-top {{
          position:absolute; top:12px; left:52px; right:12px; z-index:999;
          display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:6px;
          background:rgba(6,8,11,0.88); border:1px solid #262f40; padding:7px 12px;
          color:#e2e8f0; font-size:11px; letter-spacing:0.05em; backdrop-filter:blur(6px);
        }}
        .hud-bot {{
          position:absolute; bottom:12px; left:12px; right:12px; z-index:999;
          display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;
          pointer-events:none;
        }}
        .hud-btn {{
          pointer-events:auto; background:#0c1017; color:#f8fafc; border:1px solid #f59e0b;
          padding:6px 12px; font-family:monospace; font-size:11px; font-weight:700; cursor:pointer;
        }}
        .hud-legend {{
          pointer-events:auto; background:rgba(6,8,11,0.90); border:1px solid #262f40;
          padding:6px 12px; color:#cbd5e1; font-size:11px;
        }}
        .leaflet-tile {{ filter: invert(100%) hue-rotate(180deg) brightness(92%) contrast(92%); }}
        .leaflet-popup-content-wrapper, .leaflet-popup-tip {{
          background:#0c1017 !important; color:#f8fafc !important; border:1px solid #334155; border-radius:2px;
        }}
      </style>
    </head>
    <body>
      <div id="wrap">
        <div id="map"></div>
        <div class="hud-top">
          <div><span style="color:#f59e0b;">■</span> ACTIVE SPAN: <b>{spec['corridor_id']}</b> // {spec['city_country'].upper()}</div>
          <div style="color:#94a3b8;">GPS: {spec['latitude']:.4f}, {spec['longitude']:.4f}</div>
        </div>
        <div class="hud-bot">
          <div style="display:flex;gap:6px;">
            <button class="hud-btn" onclick="zoomCorridor()">[ + ] TACTICAL CORRIDOR</button>
            <button class="hud-btn" onclick="zoomWorld()">[ 🌍 ] GLOBAL 8-SPAN NETWORK</button>
          </div>
          <div class="hud-legend">
            <span style="color:#ef4444;">- - BLOCKED SPAN</span> &nbsp;|&nbsp;
            <span style="color:#10b981;">━━ SAFE OSRM VECTOR</span>
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
        L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
          maxZoom: 19
        }}).addTo(map);

        // Plot all 8 global monitored corridors
        nodes.forEach(n => {{
          const isCurrent = n.id === "{spec['corridor_id']}";
          const col = isCurrent ? (diverted ? '#ef4444' : '#10b981') : '#f59e0b';
          const m = L.circleMarker([n.lat, n.lon], {{
            radius: isCurrent ? 10 : 6,
            color: '#ffffff',
            weight: isCurrent ? 2.5 : 1.2,
            fillColor: col,
            fillOpacity: 0.95
          }}).addTo(map);
          m.bindPopup(`<div style="font-family:monospace;font-size:11.5px;"><b>${{n.id}} // ${{n.name}}</b><br/>${{n.city}}<br/>Sign: ${{n.sign}} | Max: ${{n.tons}}t</div>`);
          if (isCurrent && !startGlobal) m.openPopup();
        }});

        L.circleMarker([olat, olon], {{radius:6, color:'#38bdf8', fillColor:'#38bdf8', fillOpacity:0.9}}).addTo(map).bindPopup('ORIGIN');
        L.circleMarker([dlat, dlon], {{radius:6, color:'#a855f7', fillColor:'#a855f7', fillOpacity:0.9}}).addTo(map).bindPopup('DESTINATION');

        let corridorBounds = L.latLngBounds([[olat, olon], [blat, blon], [dlat, dlon], [vlat, vlon]]);

        async function drawOsrm() {{
          try {{
            const r1 = await fetch(`https://router.project-osrm.org/route/v1/driving/${{olon}},${{olat}};${{blon}},${{blat}};${{dlon}},${{dlat}}?overview=full&geometries=geojson`);
            const j1 = await r1.json();
            if (j1.routes && j1.routes[0]) {{
              const l1 = L.geoJSON(j1.routes[0].geometry, {{
                style: {{ color: diverted ? '#ef4444' : '#10b981', weight: diverted ? 3.5 : 5.5, dashArray: diverted ? '7,7' : null, opacity: 0.92 }}
              }}).addTo(map);
              if (!diverted && !startGlobal) map.fitBounds(l1.getBounds(), {{padding:[36,36]}});
            }}
            if (diverted) {{
              const r2 = await fetch(`https://router.project-osrm.org/route/v1/driving/${{olon}},${{olat}};${{vlon}},${{vlat}};${{dlon}},${{dlat}}?overview=full&geometries=geojson`);
              const j2 = await r2.json();
              if (j2.routes && j2.routes[0]) {{
                const l2 = L.geoJSON(j2.routes[0].geometry, {{
                  style: {{ color: '#10b981', weight: 5.5, opacity: 0.96 }}
                }}).addTo(map);
                L.circleMarker([vlat, vlon], {{radius:6, color:'#10b981', fillColor:'#10b981', fillOpacity:1}})
                  .addTo(map).bindPopup('SAFE BYPASS WAYPOINT: {spec["detour_road_name"]}');
                if (!startGlobal) map.fitBounds(l2.getBounds(), {{padding:[36,36]}});
              }}
            }}
          }} catch (err) {{
            L.polyline([[olat, olon], [blat, blon], [dlat, dlon]], {{color: diverted ? '#ef4444' : '#10b981', dashArray: diverted ? '7,7' : null, weight:4}}).addTo(map);
            if (diverted) L.polyline([[olat, olon], [vlat, vlon], [dlat, dlon]], {{color:'#10b981', weight:5}}).addTo(map);
          }}
        }}
        drawOsrm();

        function zoomCorridor() {{ map.flyToBounds(corridorBounds, {{padding:[38,38], duration:0.9}}); }}
        function zoomWorld() {{ map.flyTo([25.0, 12.0], 2, {{duration:0.9}}); }}
      </script>
    </body>
    </html>"""
    components.html(dark_leaflet_html, height=475)

with col_ops:
    render_html('<div class="hm-sec-hdr"><span>[03]</span> 4-GATE DETERMINISTIC INTERLOCK STATUS</div>')

    h_trip = advisory.dispatch_status == "DIVERT_OVERHEIGHT_STRIKE_PREVENTED" or (
        advisory.effective_clearance_margin_m is not None and advisory.effective_clearance_margin_m < 0
    )
    w_trip = st.session_state["weight_tons"] > spec["operating_limit_tons"]
    s_trip = spec["scour_critical"] and st.session_state["surge_m"] >= 1.80
    g_trip = st.session_state["high_sided"] and st.session_state["wind_kmh"] >= 65.0

    render_html(f"""
    <div class="hm-gate-grid">
      <div class="hm-gate {'hm-gate-trip' if h_trip else 'hm-gate-ok'}">
        <div style="font-size:10px;color:#94a3b8;">GATE_01 // CLEARANCE</div>
        <div style="font-size:13px;font-weight:700;color:{'#f87171' if h_trip else '#34d399'};margin-top:3px;">{'TRIPPED (STRIKE)' if h_trip else 'LOCKED SAFE'}</div>
      </div>
      <div class="hm-gate {'hm-gate-trip' if w_trip else 'hm-gate-ok'}">
        <div style="font-size:10px;color:#94a3b8;">GATE_02 // AXLE MASS</div>
        <div style="font-size:13px;font-weight:700;color:{'#f87171' if w_trip else '#34d399'};margin-top:3px;">{'TRIPPED (OVERLOAD)' if w_trip else 'LOCKED SAFE'}</div>
      </div>
      <div class="hm-gate {'hm-gate-trip' if s_trip else 'hm-gate-ok'}">
        <div style="font-size:10px;color:#94a3b8;">GATE_03 // PIER SCOUR</div>
        <div style="font-size:13px;font-weight:700;color:{'#f87171' if s_trip else '#34d399'};margin-top:3px;">{'SPAN CLOSED' if s_trip else 'NOMINAL STAGE'}</div>
      </div>
      <div class="hm-gate {'hm-gate-trip' if g_trip else 'hm-gate-ok'}">
        <div style="font-size:10px;color:#94a3b8;">GATE_04 // CROSSWIND</div>
        <div style="font-size:13px;font-weight:700;color:{'#fbbf24' if g_trip else '#34d399'};margin-top:3px;">{'CLAMP 50 KM/H' if g_trip else 'NOMINAL DECK'}</div>
      </div>
    </div>
    """)

    render_html('<div class="hm-sec-hdr"><span>[04]</span> GEMMA 4 + ADK ENGINEERING COPILOT</div>')
    qc1, qc2 = st.columns(2)
    quick_q = None
    with qc1:
        if st.button("FT-IN vs M MATH", use_container_width=True):
            quick_q = "Explain the Imperial vs Metric unit conversion check on this bridge."
        if st.button("PIER SCOUR RULE", use_container_width=True):
            quick_q = "How does FHWA Item 113 pier flood scour closure work here?"
    with qc2:
        if st.button("TONNAGE LIMIT", use_container_width=True):
            quick_q = "Explain the operating weight tonnage rating for this bridge."
        if st.button("OSRM BYPASS", use_container_width=True):
            quick_q = "Show the OSRM safe truck bypass detour comparison."

    chat_box = st.container(height=225)
    with chat_box:
        for msg in st.session_state["chat_history"]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    user_prompt = st.chat_input("Query clearance math, scour thresholds, or OSRM detour...")
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
# 7. Tabbed Global Telemetry & Pydantic JSON Inspector
# ---------------------------------------------------------
render_html('<div class="hm-sec-hdr" style="margin-top:14px;"><span>[05]</span> MULTI-SOURCE INFRASTRUCTURE DATA &amp; ADK PAYLOAD</div>')
tab_osm, tab_nbi, tab_json = st.tabs([
    "GLOBAL OSM LOW-CLEARANCE SPANS (309)",
    "US 2024 FHWA NBI HAZARD INVENTORY (4,500)",
    "VALIDATED ADK PYDANTIC JSON",
])

with tab_osm:
    import pandas as pd
    from pathlib import Path
    osm_p = Path(__file__).resolve().parent / "dataset" / "osm_global_low_clearance_bridges.csv"
    if osm_p.exists():
        osm_df = pd.read_csv(osm_p)
        st.dataframe(osm_df.head(40), use_container_width=True, hide_index=True)

with tab_nbi:
    st_sel = st.selectbox("Filter 2024 FHWA NBI Bridges by State", ["NC", "NY", "MA", "PA", "DC", "MD", "ALL"], index=0)
    rows = load_sample_nbi_bridges(state_code=st_sel, limit=30)
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)

with tab_json:
    st.json(json.loads(advisory.model_dump_json()))
