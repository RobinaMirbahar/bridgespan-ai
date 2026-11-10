"""Pydantic v2 data contracts and structured dispatch output schemas for BridgeSpan AI."""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field

DispatchStatus = Literal[
    "CLEAR_PRIMARY_ROUTE",
    "PROCEED_CLAMP_SPEED_50KMH",
    "DIVERT_OVERHEIGHT_STRIKE_PREVENTED",
    "DIVERT_OVERWEIGHT_LOAD_LIMIT",
    "CLOSE_BRIDGE_SCOUR_INTERLOCK",
]


class BridgeCorridorSpec(BaseModel):
    """Verified structural & hydraulic parameters for a monitored bridge corridor."""

    corridor_id: str = Field(..., description="Unique corridor identifier (e.g., BRG-001).")
    bridge_name: str = Field(..., description="Official structure name and crossing.")
    city_country: str = Field(..., description="City and country of the bridge.")
    latitude: float = Field(..., description="Bridge GPS latitude.")
    longitude: float = Field(..., description="Bridge GPS longitude.")
    detour_waypoint_lat: float = Field(..., description="Safe high-clearance / high-load detour waypoint latitude.")
    detour_waypoint_lon: float = Field(..., description="Safe detour waypoint longitude.")
    origin_lat: float = Field(..., description="Corridor approach origin latitude.")
    origin_lon: float = Field(..., description="Corridor approach origin longitude.")
    dest_lat: float = Field(..., description="Corridor destination latitude.")
    dest_lon: float = Field(..., description="Corridor destination longitude.")
    posted_clearance_m: float = Field(
        ..., description="Minimum physical vertical clearance in meters (-1.0 if unrestricted)."
    )
    posted_sign_label: str = Field(..., description="Posted roadside clearance sign (e.g., 12'-4\" or 3.0 m).")
    operating_limit_tons: float = Field(..., gt=0, description="FHWA operating load rating in metric tons.")
    scour_critical: bool = Field(..., description="True if FHWA Item 113 scour-critical pier foundation.")
    usgs_site_id: Optional[str] = Field(default=None, description="Linked USGS 15-min river gauge site code.")
    primary_route_km: float = Field(..., gt=0, description="Direct route distance through bridge (km).")
    safe_detour_km: float = Field(..., gt=0, description="Verified OSRM safe truck bypass distance (km).")


class VehicleProfile(BaseModel):
    """Approaching commercial or emergency vehicle dimensions and axle/gross load."""

    vehicle_id: str = Field(..., description="Vehicle callsign or fleet ID.")
    vehicle_class: str = Field(..., description="Human-readable vehicle type.")
    raw_height_input: str = Field(
        ..., description="Driver-entered height in feet-inches (e.g., 13'-6\") or meters (e.g., 4.11 m)."
    )
    gross_weight_tons: float = Field(..., gt=0, le=150, description="Gross vehicle weight in metric tons.")
    is_high_sided: bool = Field(default=True, description="True if susceptible to crosswind rollover.")


class BridgeGuardrailDecision(BaseModel):
    """Deterministic civil-engineering safety interlock output (overrides any LLM guess)."""

    corridor_id: str
    parsed_vehicle_height_m: float
    parsed_vehicle_height_ft_in: str
    dynamic_bounce_buffer_m: float = 0.15
    effective_clearance_margin_m: Optional[float] = None
    height_interlock_tripped: bool
    weight_interlock_tripped: bool
    scour_interlock_tripped: bool
    wind_interlock_tripped: bool
    approved_speed_kmh: int = Field(..., ge=0, le=100)
    use_safe_detour: bool
    dispatch_status: DispatchStatus
    guardrail_notes: List[str]


class BridgeDispatchAdvisory(BaseModel):
    """Validated structured JSON dispatch advisory emitted to dashboard & roadside VMS boards."""

    corridor_id: str
    bridge_name: str
    vehicle_class: str
    dispatch_status: DispatchStatus
    approved_speed_kmh: int
    assigned_route_label: str
    route_distance_km: float
    extra_detour_km: float
    effective_clearance_margin_m: Optional[float]
    guardrail_interlock_passed: bool
    vms_sign_banner: str
    engineering_summary: str
    tools_invoked: List[str]
