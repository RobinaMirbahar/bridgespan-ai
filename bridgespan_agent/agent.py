"""Google ADK LlmAgent definition and deterministic safety pipeline for BridgeSpan AI."""

import os
from typing import Any, Dict, Optional

from bridgespan_agent.guardrails import bridge_adk_before_tool_guardrail
from bridgespan_agent.schemas import BridgeDispatchAdvisory
from bridgespan_agent.tools import (
    compute_safe_bridge_dispatch,
    get_bridge_structural_profile,
    get_live_river_scour_and_wind,
)

DEFAULT_MODEL = os.environ.get("BRIDGESPAN_MODEL", "ollama_chat/gemma3:4b")
DEFAULT_OLLAMA_BASE = os.environ.get("OLLAMA_API_BASE", "http://localhost:11434")

SYSTEM_INSTRUCTION = """You are BridgeSpanDispatcher, a civil-engineering heavy-vehicle bridge strike,
axle-load, and river flood-scour safety agent powered by Google ADK and Gemma / Gemini.

For every approaching commercial truck or emergency vehicle, execute this exact 3-step trajectory:
1. Call `get_bridge_structural_profile(corridor_id)` to retrieve exact posted vertical clearance (m & ft-in),
   FHWA operating tonnage rating, and Item 113 pier-scour criticality.
2. Call `get_live_river_scour_and_wind(corridor_id)` to read USGS / GloFAS river stage surge and crosswind gusts.
3. Call `compute_safe_bridge_dispatch(...)` to enforce deterministic Imperial/Metric clearance conversion (+0.15 m
   dynamic bounce buffer), load limits, pier flood-scour closure, and OSRM truck bypass routing.
4. Emit your final output conforming strictly to `BridgeDispatchAdvisory`.
"""


def build_bridgespan_agent(
    model_name: str = DEFAULT_MODEL,
    api_base: str = DEFAULT_OLLAMA_BASE,
) -> Any:
    """Construct the Google ADK LlmAgent wired to Gemma/Gemini, civil safety tools, and JSON schema."""
    try:
        from google.adk.agents import LlmAgent
        from google.adk.models.lite_llm import LiteLlm

        llm = LiteLlm(model=model_name, api_base=api_base)
        return LlmAgent(
            name="BridgeSpanDispatcher",
            model=llm,
            instruction=SYSTEM_INSTRUCTION,
            tools=[
                get_bridge_structural_profile,
                get_live_river_scour_and_wind,
                compute_safe_bridge_dispatch,
            ],
            before_tool_callback=bridge_adk_before_tool_guardrail,
            output_schema=BridgeDispatchAdvisory,
            output_key="bridge_dispatch_advisory",
        )
    except Exception:
        return {
            "name": "BridgeSpanDispatcher",
            "model": model_name,
            "api_base": api_base,
            "tools": [
                "get_bridge_structural_profile",
                "get_live_river_scour_and_wind",
                "compute_safe_bridge_dispatch",
            ],
            "output_schema": "BridgeDispatchAdvisory",
        }


def run_bridgespan_dispatch(
    corridor_id: str = "BRG-001",
    vehicle_class: str = "13'-6\" Interstate Semi-Trailer",
    raw_vehicle_height: str = "13'-6\"",
    vehicle_gross_tons: float = 34.5,
    is_high_sided: bool = True,
    river_stage_surge_m: Optional[float] = None,
    wind_gust_kmh: Optional[float] = None,
    requested_speed_kmh: int = 80,
) -> BridgeDispatchAdvisory:
    """Execute the 3-step BridgeSpan civil safety pipeline and return a validated `BridgeDispatchAdvisory`."""
    spec = get_bridge_structural_profile(corridor_id)
    env = get_live_river_scour_and_wind(
        corridor_id,
        override_surge_m=river_stage_surge_m,
        override_wind_kmh=wind_gust_kmh,
    )

    tool_args: Dict[str, Any] = {
        "corridor_id": spec["corridor_id"],
        "raw_vehicle_height": raw_vehicle_height,
        "vehicle_gross_tons": vehicle_gross_tons,
        "is_high_sided": is_high_sided,
        "river_stage_surge_m": env["river_stage_surge_m"],
        "wind_gust_kmh": env["wind_gust_kmh"],
        "requested_speed_kmh": requested_speed_kmh,
    }
    bridge_adk_before_tool_guardrail(compute_safe_bridge_dispatch, tool_args, None)

    result = compute_safe_bridge_dispatch(**tool_args)
    dec = result["decision"]
    passed = not (
        dec["height_interlock_tripped"]
        or dec["weight_interlock_tripped"]
        or dec["scour_interlock_tripped"]
    )

    return BridgeDispatchAdvisory(
        corridor_id=spec["corridor_id"],
        bridge_name=spec["bridge_name"],
        vehicle_class=vehicle_class,
        dispatch_status=dec["dispatch_status"],
        approved_speed_kmh=dec["approved_speed_kmh"],
        assigned_route_label=result["assigned_route_label"],
        route_distance_km=result["route_distance_km"],
        extra_detour_km=result["extra_detour_km"],
        effective_clearance_margin_m=dec["effective_clearance_margin_m"],
        guardrail_interlock_passed=passed,
        vms_sign_banner=result["vms_sign_banner"],
        engineering_summary=" | ".join(dec["guardrail_notes"]),
        tools_invoked=[
            "get_bridge_structural_profile",
            "get_live_river_scour_and_wind",
            "compute_safe_bridge_dispatch",
        ],
    )
