"""Unit & benchmark verification suite for BridgeSpan AI deterministic civil guardrails."""

import csv
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from bridgespan_agent.agent import build_bridgespan_agent, run_bridgespan_dispatch
from bridgespan_agent.guardrails import (
    evaluate_bridge_interlocks,
    meters_to_ft_in,
    parse_height_to_meters,
)


def test_imperial_and_metric_height_parsing() -> None:
    assert parse_height_to_meters("13'-6\"") == pytest.approx(4.115, abs=0.01)
    assert parse_height_to_meters("12'4\"") == pytest.approx(3.759, abs=0.01)
    assert parse_height_to_meters("13ft 6in") == pytest.approx(4.115, abs=0.01)
    assert parse_height_to_meters("3.89 m") == pytest.approx(3.89, abs=0.005)
    assert parse_height_to_meters("389 cm") == pytest.approx(3.89, abs=0.005)
    assert meters_to_ft_in(3.76) == "12'-4\""


def test_invalid_height_rejected() -> None:
    with pytest.raises(ValueError):
        parse_height_to_meters("12'-14\"")  # >= 12 inches invalid
    with pytest.raises(ValueError):
        parse_height_to_meters("0.4 m")     # below physical vehicle height


def test_durham_11ft8_strike_prevented() -> None:
    advisory = run_bridgespan_dispatch(
        corridor_id="BRG-001",
        raw_vehicle_height="13'-6\"",
        vehicle_gross_tons=34.5,
        is_high_sided=True,
        river_stage_surge_m=0.1,
        wind_gust_kmh=25.0,
    )
    assert advisory.dispatch_status == "DIVERT_OVERHEIGHT_STRIKE_PREVENTED"
    assert not advisory.guardrail_interlock_passed
    assert advisory.extra_detour_km > 0


def test_potomac_pier_scour_emergency_closure() -> None:
    advisory = run_bridgespan_dispatch(
        corridor_id="BRG-003",
        raw_vehicle_height="8'-8\"",
        vehicle_gross_tons=4.2,
        is_high_sided=False,
        river_stage_surge_m=2.25,
        wind_gust_kmh=30.0,
    )
    assert advisory.dispatch_status == "CLOSE_BRIDGE_SCOUR_INTERLOCK"
    assert not advisory.guardrail_interlock_passed


def test_susquehanna_tonnage_overload_diverted() -> None:
    advisory = run_bridgespan_dispatch(
        corridor_id="BRG-007",
        raw_vehicle_height="12'-0\"",
        vehicle_gross_tons=42.0,
        is_high_sided=False,
        river_stage_surge_m=0.2,
        wind_gust_kmh=20.0,
    )
    assert advisory.dispatch_status == "DIVERT_OVERWEIGHT_LOAD_LIMIT"
    assert not advisory.guardrail_interlock_passed


def test_baku_khazri_crosswind_speed_clamp() -> None:
    advisory = run_bridgespan_dispatch(
        corridor_id="BRG-006",
        raw_vehicle_height="3.80 m",
        vehicle_gross_tons=24.0,
        is_high_sided=True,
        river_stage_surge_m=0.0,
        wind_gust_kmh=78.0,
    )
    assert advisory.dispatch_status == "PROCEED_CLAMP_SPEED_50KMH"
    assert advisory.approved_speed_kmh == 50
    assert advisory.guardrail_interlock_passed


def test_adk_agent_builder_smoke() -> None:
    agent_obj = build_bridgespan_agent()
    assert agent_obj is not None


def test_100_percent_agreement_with_80_scenario_benchmark() -> None:
    bench_path = Path(__file__).resolve().parent.parent / "dataset" / "bridgespan_dispatch_benchmark_80.csv"
    assert bench_path.exists()
    with bench_path.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 80

    for row in rows:
        is_high_sided = row["vehicle_class"] in {
            "13'-6\" Interstate Semi-Trailer",
            "Double-Deck Refrigerated Box Truck",
        }
        dec = evaluate_bridge_interlocks(
            corridor_id=row["corridor_code"],
            posted_clearance_m=float(row["posted_clearance_m"]),
            operating_limit_tons=float(row["operating_limit_tons"]),
            scour_critical=(row["scour_critical_foundation"] == "True"),
            raw_vehicle_height=row["driver_declared_height"],
            vehicle_gross_tons=float(row["vehicle_gross_tons"]),
            is_high_sided=is_high_sided,
            river_stage_surge_m=float(row["river_stage_surge_m"]),
            wind_gust_kmh=float(row["wind_gust_kmh"]),
        )
        assert dec.dispatch_status == row["gold_dispatch_decision"], f"Mismatch on {row['scenario_id']}"
