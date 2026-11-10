"""Context-aware Civil Engineering & Heavy-Freight Copilot for BridgeSpan AI."""

from typing import Any, Dict

from bridgespan_agent.guardrails import DYNAMIC_BOUNCE_BUFFER_M, meters_to_ft_in
from bridgespan_agent.tools import BRIDGE_CORRIDORS


def answer_bridge_chat_query(
    query: str,
    corridor_id: str = "BRG-001",
    advisory: Any = None,
    env_state: Dict[str, Any] | None = None,
) -> str:
    """Answer driver, fleet-dispatcher, and civil-engineering questions with live bridge interlock context."""
    q = (query or "").lower().strip()
    spec = BRIDGE_CORRIDORS.get(corridor_id, BRIDGE_CORRIDORS["BRG-001"])
    env = env_state or {"river_stage_surge_m": 0.15, "wind_gust_kmh": 28.0, "usgs_site_id": "02085070"}

    status = getattr(advisory, "dispatch_status", "CLEAR_PRIMARY_ROUTE")
    margin = getattr(advisory, "effective_clearance_margin_m", None)
    route_lbl = getattr(advisory, "assigned_route_label", spec["bridge_name"])
    extra_km = getattr(advisory, "extra_detour_km", 0.0)
    speed = getattr(advisory, "approved_speed_kmh", 80)
    summary = getattr(advisory, "engineering_summary", "")

    if any(k in q for k in ["unit", "feet", "inch", "metric", "convert", "11-foot", "can opener", "strike", "height", "clear"]):
        clr_str = (
            f"{spec['posted_clearance_m']:.2f} m ({spec['posted_sign_label']})"
            if spec["posted_clearance_m"] > 0
            else "Unrestricted (Open Deck)"
        )
        margin_line = (
            f"• **Net Dynamic Clearance Margin:** `{margin:+.2f} m` (includes mandatory `{DYNAMIC_BOUNCE_BUFFER_M:.2f} m` / `6 in` suspension bounce & asphalt overlay buffer)"
            if margin is not None
            else "• **Overhead Restriction:** None (open truss / deck crossing)"
        )
        return (
            f"📐 **Imperial vs. Metric Clearance Interlock — {spec['bridge_name']}**\n\n"
            f"• **Posted Physical Clearance:** `{clr_str}`\n"
            f"{margin_line}\n"
            f"• **Current Guardrail Verdict:** `{status}`\n"
            f"• **Assigned Route:** `{route_lbl}` (`+{extra_km:.2f} km` detour)\n\n"
            "💡 **Why LLMs Fail Without Hard Gate Conversion:** Standard North American semi-trailers measure `13'-6\"` (`4.115 m`). "
            "Drivers and raw LLMs frequently confuse `12'-4\"` (`3.76 m`) or metric `3.89 m` signs, or forget suspension bounce on uneven underpass dips. "
            "BridgeSpan parses both `ft-in` and `m` deterministically before unlocking primary bridge entry."
        )

    if any(k in q for k in ["scour", "flood", "river", "usgs", "pier", "water", "potomac"]):
        return (
            f"🌊 **FHWA Item 113 Pier Flood-Scour Monitor — {spec['river_name']}**\n\n"
            f"• **Scour-Critical Foundation:** `{'YES (FHWA Item 113 Critical)' if spec['scour_critical'] else 'NO (Rock / Non-Scour Span)'}`\n"
            f"• **Telemetry Source:** `{env.get('usgs_site_id', 'GLOFAS')}` | **Live River Surge:** `+{env.get('river_stage_surge_m', 0.0):.2f} m`\n"
            f"• **Closure Threshold:** `>= +1.80 m` stage rise on scour-critical piers\n\n"
            "💡 **Civil Engineering Context:** Hydraulic pier scour—rapid floodwater eroding sediment from beneath bridge footings—is the **#1 cause of highway bridge failure in the United States** (accounting for >50% of collapses). "
            "When river gauges spike past `+1.80 m` on an Item 113 scour-critical bridge, BridgeSpan closes the span immediately regardless of vehicle size."
        )

    if any(k in q for k in ["weight", "ton", "axle", "load", "crane", "heavy"]):
        return (
            f"⚖️ **FHWA Operating Tonnage & Axle Rating — {spec['bridge_name']}**\n\n"
            f"• **Maximum Operating Rating (Item 064):** `{spec['operating_limit_tons']:.1f} metric tons`\n"
            f"• **Active Dispatch Status:** `{status}`\n"
            f"• **Safe Heavy-Haul Bypass:** `{spec['detour_road_name']}` (`{spec['safe_detour_km']:.2f} km`)\n\n"
            "💡 **Structural Interlock:** Historic stone-arch parkways (e.g., Hutchinson Pkwy `15 t`) and aging steel trusses (`22.5 t`) cannot safely carry `34.5 t` semi-trailers or `42 t` mobile cranes even when overhead clearance looks open."
        )

    if any(k in q for k in ["detour", "bypass", "osrm", "route", "map", "shortcut"]):
        return (
            f"🗺️ **OSRM Verified Heavy-Truck Routing — {spec['city_country']}**\n\n"
            f"• **Primary Bridge Corridor:** `{spec['primary_route_km']:.2f} km` via `{spec['bridge_name']}`\n"
            f"• **Verified High-Clearance Bypass:** `{spec['safe_detour_km']:.2f} km` via `{spec['detour_road_name']}` (`+{spec['safe_detour_km'] - spec['primary_route_km']:.2f} km`)\n"
            f"• **Approved Speed Ceiling:** `{speed} km/h`"
        )

    return (
        f"🌉 **BridgeSpan AI Live Status — {spec['bridge_name']}**\n\n"
        f"• **Dispatch Verdict:** `{status}` | **Approved Speed:** `{speed} km/h`\n"
        f"• **Assigned Corridor:** `{route_lbl}`\n"
        f"• **Posted Clearance:** `{meters_to_ft_in(spec['posted_clearance_m']) if spec['posted_clearance_m'] > 0 else 'UNRESTRICTED'}` "
        f"| **Load Limit:** `{spec['operating_limit_tons']:.1f} t`\n"
        f"• **Engineering Trace:** {summary}\n\n"
        "Ask me about **Imperial vs. Metric unit traps**, **FHWA pier flood-scour closures**, **axle/gross load limits**, or **OSRM safe truck detours**!"
    )
