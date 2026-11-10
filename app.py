# -*- coding: utf-8 -*-
"""
BridgeSpan AI — Live Heavy-Truck Bridge Strike, Axle Load & Flood-Scour Prevention Dashboard
Powered by Gemma / Gemini, Google ADK, OSRM Routing, Leaflet Maps, and Deterministic Civil Guardrails.
Author: Robina Mirbahar
"""

import json
from pathlib import Path
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
    page_title="BridgeSpan AI • Strike, Load & Scour Prevention",
    page_icon="🌉",
    layout="wide",
    initial_sidebar_state="expanded",
)


def render_html(raw_html: str) -> None:
    compact = "".join(line.strip() for line in raw_html.splitlines() if line.strip())
    st.markdown(compact, unsafe_allow_html=True)


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
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = [
        {
            "role": "assistant",
            "content": "👋 **Welcome to BridgeSpan AI!** Select a notorious low-clearance or scour-critical bridge on the left, test `ft-in` vs `m` truck heights, or trigger a river flood-scour surge.",
        }
    ]

# ---------------------------------------------------------
# Sidebar Controls & 1-Tap Real Hazard Presets
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("### 🌉 **Bridge Corridor Selector**")
    corridor_options = list(BRIDGE_CORRIDORS.keys())
    selected_corridor = st.selectbox(
        "Monitored Bridge / Underpass",
        options=corridor_options,
        index=corridor_options.index(st.session_state["corridor_id"]),
        format_func=lambda k: BRIDGE_CORRIDORS[k]["short_label"],
    )
    if selected_corridor != st.session_state["corridor_id"]:
        st.session_state["corridor_id"] = selected_corridor
        st.session_state["surge_m"] = float(BRIDGE_CORRIDORS[selected_corridor]["default_surge_m"])
        st.session_state["wind_kmh"] = float(BRIDGE_CORRIDORS[selected_corridor]["default_wind_kmh"])
        st.rerun()

    spec = BRIDGE_CORRIDORS[selected_corridor]

    st.markdown("#### ⚡ **1-Tap Viral & Civil Hazard Scenarios**")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🚚 11-Ft-8 Can Opener", use_container_width=True):
            st.session_state["corridor_id"] = "BRG-001"
            st.session_state["height_input"] = "13'-6\""
            st.session_state["weight_tons"] = 34.5
            st.session_state["high_sided"] = True
            st.session_state["surge_m"] = 0.15
            st.session_state["wind_kmh"] = 28.0
            st.rerun()
        if st.button("🌊 Potomac Pier Scour", use_container_width=True):
            st.session_state["corridor_id"] = "BRG-003"
            st.session_state["height_input"] = "10'-6\""
            st.session_state["weight_tons"] = 19.5
            st.session_state["high_sided"] = False
            st.session_state["surge_m"] = 2.40
            st.session_state["wind_kmh"] = 48.0
            st.rerun()
    with c2:
        if st.button("⚖️ 42t Crane Overload", use_container_width=True):
            st.session_state["corridor_id"] = "BRG-007"
            st.session_state["height_input"] = "12'-0\""
            st.session_state["weight_tons"] = 42.0
            st.session_state["high_sided"] = False
            st.session_state["surge_m"] = 0.30
            st.session_state["wind_kmh"] = 25.0
            st.rerun()
        if st.button("🌪️ Baku Khazri Gale", use_container_width=True):
            st.session_state["corridor_id"] = "BRG-006"
            st.session_state["height_input"] = "3.85 m"
            st.session_state["weight_tons"] = 24.0
            st.session_state["high_sided"] = True
            st.session_state["surge_m"] = 0.0
            st.session_state["wind_kmh"] = 78.0
            st.rerun()

    st.divider()
    st.markdown("#### 🚛 **Approaching Vehicle Profile**")
    preset_id = st.selectbox(
        "Fleet Preset",
        options=list(FLEET_PRESETS.keys()),
        format_func=lambda k: FLEET_PRESETS[k]["vehicle_class"],
    )
    if st.button("Load Fleet Preset Values", use_container_width=True):
        p = FLEET_PRESETS[preset_id]
        st.session_state["vehicle_id"] = preset_id
        st.session_state["height_input"] = p["raw_height_input"]
        st.session_state["weight_tons"] = float(p["gross_weight_tons"])
        st.session_state["high_sided"] = bool(p["is_high_sided"])
        st.rerun()

    height_raw = st.text_input(
        "Declared Height (`ft-in` or `m`, e.g. `13'-6\"` or `3.89 m`)",
        value=st.session_state["height_input"],
    )
    st.session_state["height_input"] = height_raw

    weight_val = st.slider("Gross Vehicle Weight (Metric Tons)", 2.0, 60.0, float(st.session_state["weight_tons"]), 0.5)
    st.session_state["weight_tons"] = weight_val

    high_sided_val = st.checkbox("High-Sided Trailer / Box Profile", value=bool(st.session_state["high_sided"]))
    st.session_state["high_sided"] = high_sided_val

    st.divider()
    st.markdown("#### 🌧️ **Live River Scour & Crosswind Telemetry**")
    surge_val = st.slider("USGS / GloFAS River Stage Surge (+m)", 0.0, 3.5, float(st.session_state["surge_m"]), 0.05)
    st.session_state["surge_m"] = surge_val

    wind_val = st.slider("Bridge Deck Crosswind Gust (km/h)", 0.0, 120.0, float(st.session_state["wind_kmh"]), 1.0)
    st.session_state["wind_kmh"] = wind_val

# ---------------------------------------------------------
# Run Deterministic Civil Interlock + Agent Pipeline
# ---------------------------------------------------------
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
# Custom Industrial Dark UI Styling + Roadside VMS Sign
# ---------------------------------------------------------
render_html("""
<style>
.bp-hero {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    border: 1px solid #334155;
    border-radius: 14px;
    padding: 18px 24px;
    color: #f8fafc;
    margin-bottom: 14px;
}
.bp-vms {
    font-family: 'Consolas', 'Courier New', monospace;
    font-weight: 800;
    font-size: 1.08rem;
    letter-spacing: 0.04em;
    padding: 13px 18px;
    border-radius: 10px;
    text-align: center;
    margin-bottom: 16px;
    border: 2px solid;
}
.vms-danger { background: #2a0a0e; color: #ff6b6b; border-color: #ef4444; box-shadow: 0 0 18px rgba(239,68,68,0.28); }
.vms-warn   { background: #2b1d06; color: #fbbf24; border-color: #f59e0b; }
.vms-ok     { background: #06281b; color: #34d399; border-color: #10b981; }
.bp-kpi {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 14px 16px;
    color: #e2e8f0;
}
.bp-kpi-lbl { font-size: 0.76rem; text-transform: uppercase; color: #94a3b8; letter-spacing: 0.05em; }
.bp-kpi-val { font-size: 1.32rem; font-weight: 700; margin-top: 4px; color: #f8fafc; }
.bp-kpi-sub { font-size: 0.78rem; color: #64748b; margin-top: 2px; }
</style>
""")

render_html(f"""
<div class="bp-hero">
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">
    <div>
      <div style="font-size:0.8rem;color:#38bdf8;font-weight:700;letter-spacing:0.08em;">BRIDGESPAN AI • STRUCTURAL CLEARANCE, AXLE LOAD &amp; SCOUR SAFETY AGENT</div>
      <div style="font-size:1.5rem;font-weight:800;margin-top:2px;">🌉 {spec['bridge_name']}</div>
      <div style="font-size:0.88rem;color:#94a3b8;margin-top:2px;">📍 {spec['city_country']} &nbsp;|&nbsp; River Basin: {spec['river_name']} &nbsp;|&nbsp; Google ADK + Deterministic Civil Interlocks</div>
    </div>
    <div style="text-align:right;">
      <span style="background:#1e293b;border:1px solid #475569;padding:6px 12px;border-radius:999px;font-size:0.8rem;color:#e2e8f0;">
        Posted Sign: <b>{spec['posted_sign_label']}</b> &bull; Max Load: <b>{spec['operating_limit_tons']:.1f} t</b>
      </span>
    </div>
  </div>
</div>
""")

if parse_error:
    st.warning(f"Height input warning (`{parse_error}`) — defaulted evaluation to `13'-6\"` (`4.115 m`).")

vms_cls = (
    "vms-danger"
    if advisory.dispatch_status in {"DIVERT_OVERHEIGHT_STRIKE_PREVENTED", "DIVERT_OVERWEIGHT_LOAD_LIMIT", "CLOSE_BRIDGE_SCOUR_INTERLOCK"}
    else ("vms-warn" if advisory.dispatch_status == "PROCEED_CLAMP_SPEED_50KMH" else "vms-ok")
)
render_html(f'<div class="bp-vms {vms_cls}">LED ROADSIDE VMS GANTRY &bull; {advisory.vms_sign_banner}</div>')

k1, k2, k3, k4 = st.columns(4)
with k1:
    clr_disp = f"{spec['posted_clearance_m']:.2f} m ({spec['posted_sign_label']})" if spec["posted_clearance_m"] > 0 else "UNRESTRICTED"
    margin_txt = (
        f"Margin: {advisory.effective_clearance_margin_m:+.2f} m (incl. 0.15m bounce)"
        if advisory.effective_clearance_margin_m is not None
        else "Open overhead truss/deck"
    )
    render_html(f"""
    <div class="bp-kpi">
      <div class="bp-kpi-lbl">Unit-Converted Height Check</div>
      <div class="bp-kpi-val">{parsed_h_m:.2f} m ({meters_to_ft_in(parsed_h_m)})</div>
      <div class="bp-kpi-sub">Bridge: {clr_disp} • {margin_txt}</div>
    </div>
    """)
with k2:
    render_html(f"""
    <div class="bp-kpi">
      <div class="bp-kpi-lbl">Operating Tonnage Rating</div>
      <div class="bp-kpi-val">{st.session_state['weight_tons']:.1f} t / {spec['operating_limit_tons']:.1f} t</div>
      <div class="bp-kpi-sub">{'⚠️ OVERWEIGHT — BYPASS REQUIRED' if st.session_state['weight_tons'] > spec['operating_limit_tons'] else '✓ Within FHWA Item 064 operating limit'}</div>
    </div>
    """)
with k3:
    scour_tag = "CRITICAL (Item 113)" if spec["scour_critical"] else "Non-Scour Span"
    render_html(f"""
    <div class="bp-kpi">
      <div class="bp-kpi-lbl">River Scour &amp; Crosswind</div>
      <div class="bp-kpi-val">+{env_state['river_stage_surge_m']:.2f} m &bull; {env_state['wind_gust_kmh']:.0f} km/h</div>
      <div class="bp-kpi-sub">Pier: {scour_tag} • Flow: {env_state['river_discharge_cms']} m³/s</div>
    </div>
    """)
with k4:
    render_html(f"""
    <div class="bp-kpi">
      <div class="bp-kpi-lbl">OSRM Route &amp; Safe Speed</div>
      <div class="bp-kpi-val">{advisory.route_distance_km:.2f} km @ {advisory.approved_speed_kmh} km/h</div>
      <div class="bp-kpi-sub">{'Diverted (+' + str(advisory.extra_detour_km) + ' km safe truck bypass)' if advisory.extra_detour_km > 0 else 'Direct primary bridge route open'}</div>
    </div>
    """)

st.write("")

# ---------------------------------------------------------
# Live Interactive Leaflet + Live OSRM Geometry Map & Copilot
# ---------------------------------------------------------
col_map, col_right = st.columns([1.55, 1.0], gap="large")

with col_map:
    st.markdown("#### 🗺️ **Live OpenStreetMap + OSRM Safe Heavy-Truck Rerouting**")
    is_diverted = "true" if not advisory.guardrail_interlock_passed else "false"
    leaflet_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8"/>
      <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
      <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
      <style>
        body {{ margin:0; padding:0; background:#0f172a; font-family: system-ui, sans-serif; }}
        #map {{ width: 100%; height: 435px; border-radius: 12px; border: 1px solid #334155; }}
        .legend {{
          background: rgba(15,23,42,0.92); color: #f8fafc; padding: 8px 12px;
          border-radius: 8px; border: 1px solid #475569; font-size: 12px; line-height: 1.5;
        }}
      </style>
    </head>
    <body>
      <div id="map"></div>
      <script>
        const blat = {spec['latitude']};
        const blon = {spec['longitude']};
        const olat = {spec['origin_lat']};
        const olon = {spec['origin_lon']};
        const dlat = {spec['dest_lat']};
        const dlon = {spec['dest_lon']};
        const vlat = {spec['detour_waypoint_lat']};
        const vlon = {spec['detour_waypoint_lon']};
        const diverted = {is_diverted};

        const map = L.map('map').setView([blat, blon], 14);
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
          maxZoom: 19,
          attribution: '&copy; OpenStreetMap contributors &bull; OSRM Routing'
        }}).addTo(map);

        const bridgeColor = diverted ? '#ef4444' : '#10b981';
        const bridgeMarker = L.circleMarker([blat, blon], {{
          radius: 11, color: '#ffffff', weight: 2.5, fillColor: bridgeColor, fillOpacity: 0.95
        }}).addTo(map);
        bridgeMarker.bindPopup(
          `<b>{spec['bridge_name']}</b><br/>Posted: {spec['posted_sign_label']} | Limit: {spec['operating_limit_tons']}t<br/>Status: <b>{advisory.dispatch_status}</b>`
        ).openPopup();

        L.circleMarker([olat, olon], {{radius:7, color:'#38bdf8', fillColor:'#38bdf8', fillOpacity:0.9}})
          .addTo(map).bindPopup('<b>Approach Origin</b>');
        L.circleMarker([dlat, dlon], {{radius:7, color:'#a855f7', fillColor:'#a855f7', fillOpacity:0.9}})
          .addTo(map).bindPopup('<b>Freight Destination</b>');

        async function drawRoutes() {{
          try {{
            const rPrimary = await fetch(`https://router.project-osrm.org/route/v1/driving/${{olon}},${{olat}};${{blon}},${{blat}};${{dlon}},${{dlat}}?overview=full&geometries=geojson`);
            const jPrimary = await rPrimary.json();
            if (jPrimary.routes && jPrimary.routes[0]) {{
              const primLine = L.geoJSON(jPrimary.routes[0].geometry, {{
                style: {{
                  color: diverted ? '#ef4444' : '#10b981',
                  weight: diverted ? 4 : 6,
                  dashArray: diverted ? '8, 8' : null,
                  opacity: 0.9
                }}
              }}).addTo(map);
              if (!diverted) map.fitBounds(primLine.getBounds(), {{padding:[32,32]}});
            }}

            if (diverted) {{
              const rDetour = await fetch(`https://router.project-osrm.org/route/v1/driving/${{olon}},${{olat}};${{vlon}},${{vlat}};${{dlon}},${{dlat}}?overview=full&geometries=geojson`);
              const jDetour = await rDetour.json();
              if (jDetour.routes && jDetour.routes[0]) {{
                const detLine = L.geoJSON(jDetour.routes[0].geometry, {{
                  style: {{ color: '#22c55e', weight: 6, opacity: 0.95 }}
                }}).addTo(map);
                L.circleMarker([vlat, vlon], {{radius:7, color:'#22c55e', fillColor:'#22c55e', fillOpacity:0.95}})
                  .addTo(map).bindPopup('<b>Verified Safe Bypass Waypoint</b><br/>{spec["detour_road_name"]}');
                map.fitBounds(detLine.getBounds(), {{padding:[32,32]}});
              }}
            }}
          }} catch (e) {{
            L.polyline([[olat, olon], [blat, blon], [dlat, dlon]], {{
              color: diverted ? '#ef4444' : '#10b981', dashArray: diverted ? '8,8' : null, weight: 5
            }}).addTo(map);
            if (diverted) {{
              L.polyline([[olat, olon], [vlat, vlon], [dlat, dlon]], {{ color: '#22c55e', weight: 6 }}).addTo(map);
            }}
          }}
        }}
        drawRoutes();

        const legend = L.control({{position: 'bottomright'}});
        legend.onAdd = function() {{
          const div = L.DomUtil.create('div', 'legend');
          div.innerHTML = diverted
            ? '<div><span style="color:#ef4444;font-weight:bold;">- - -</span> Blocked Primary Span (Strike/Load/Scour)</div><div><span style="color:#22c55e;font-weight:bold;">━━━</span> Active Safe OSRM Truck Bypass</div>'
            : '<div><span style="color:#10b981;font-weight:bold;">━━━</span> Verified Clear Primary Bridge Route</div>';
          return div;
        }};
        legend.addTo(map);
      </script>
    </body>
    </html>
    """
    components.html(leaflet_html, height=450)

    with st.expander("📋 Validated Pydantic `BridgeDispatchAdvisory` JSON Payload & ADK Tool Trace", expanded=False):
        st.json(json.loads(advisory.model_dump_json()))

with col_right:
    st.markdown("#### 🤖 **BridgeSpan Civil Safety Copilot**")
    q_cols = st.columns(2)
    quick_q = None
    with q_cols[0]:
        if st.button("📐 Unit Conversion Trap?", use_container_width=True):
            quick_q = "Explain the Imperial vs Metric unit conversion check on this bridge."
        if st.button("🌊 Pier Scour Rule?", use_container_width=True):
            quick_q = "How does FHWA Item 113 pier flood scour closure work here?"
    with q_cols[1]:
        if st.button("⚖️ Tonnage Rating?", use_container_width=True):
            quick_q = "Explain the operating weight tonnage rating for this bridge."
        if st.button("🗺️ Why This Detour?", use_container_width=True):
            quick_q = "Show the OSRM safe truck bypass detour comparison."

    chat_box = st.container(height=285)
    with chat_box:
        for msg in st.session_state["chat_history"]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    user_prompt = st.chat_input("Ask about ft-in vs m clearance, pier scour, or truck detours...")
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

st.divider()
st.markdown("#### 📊 **Bundled Multi-Source Real Dataset Explorer (`4,500` 2024 FHWA NBI Bridges + `309` OSM Global Low Bridges + USGS/GloFAS)**")
st_filter = st.selectbox("Inspect Real 2024 FHWA National Bridge Inventory (NBI) Hazard Structures by State", ["NC", "NY", "MA", "PA", "DC", "MD", "ALL"])
sample_rows = load_sample_nbi_bridges(state_code=st_filter, limit=25)
if sample_rows:
    st.dataframe(sample_rows, use_container_width=True, hide_index=True)
