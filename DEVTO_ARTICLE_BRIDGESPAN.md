---
title: "Why Trucks Keep Hitting 11-Foot-8 Bridges — And How I Built BridgeSpan AI with Gemma 4 & Google ADK to Stop Them"
published: false
description: "How I built an open-source heavy-freight bridge strike, axle-load, and flood-scour safety agent using Gemma 4, Google ADK, OSRM routing, and 4,800+ real FHWA NBI + OSM bridges."
tags: ai, googlecloud, opensource, python
canonical_url: https://github.com/RobinaMirbahar/bridgespan-ai
cover_image: https://raw.githubusercontent.com/RobinaMirbahar/bridgespan-ai/main/assets/bridgespan_banner.jpg
---

**Author:** Robina Mirbahar  
*AI/ML Google Developer Expert (GDE) | Google Cloud Champion Innovator | WTM Ambassador*  
*GitHub Repository:* [RobinaMirbahar/bridgespan-ai](https://github.com/RobinaMirbahar/bridgespan-ai)  
*Live Streamlit App:* [bridgespan-ai-mvhoucpfp2n5o25dewb2hi.streamlit.app](https://bridgespan-ai-mvhoucpfp2n5o25dewb2hi.streamlit.app)  
*Kaggle Open Dataset:* [BridgeSpan Bridge Strike, Load & Scour Dataset](https://www.kaggle.com/datasets/robinamirbahar/bridgespan-global-bridge-strike-load-scour)  

---

Everyone on the internet has watched viral videos of box trucks and semi-trailers getting their roofs peeled back like sardine cans by Durham's notorious **11-Foot-8+8 ("Can Opener")** rail trestle, Boston's **Storrow Drive**, or Melbourne's **Montague Street 3.0 m overpass**.

Behind the memes is a massive, expensive civil-engineering failure mode:
- In the US and UK alone, **thousands of low-clearance bridge strikes** occur every year, halting commuter rail corridors above and costing millions in girder repairs.
- Even worse—and far less visible—**underwater hydraulic pier scour** during flash-flood surges is the **#1 cause of highway bridge collapse in the United States** (accounting for over 50% of structural failures tracked under FHWA Item 113).
- Meanwhile, heavy mobile cranes (`42 t`) and loaded semi-trailers (`34.5 t`) regularly cross historic trusses or stone-arch parkways rated for `15 t` to `22.5 t`.

If you ask a standard LLM navigation chatbot *"Can my 13'-6\" truck clear that 3.89 m overpass?"* or *"Is Chain Bridge safe right now?"*, a single unit-conversion hallucination or ignored river-gauge surge turns into a physical catastrophe.

To solve this properly, I built and open-sourced **BridgeSpan AI**—a global physical-infrastructure safety agent powered by **Google's open-weights Gemma 4**, the **Google Agent Development Kit (ADK)**, **OSRM heavy-truck routing**, and a **4,809-span real-world dataset** assembled from the 2024 US DOT Federal Highway Administration (FHWA) National Bridge Inventory, OpenStreetMap, USGS river gauges, and Copernicus GloFAS.

![BridgeSpan AI Live Tactical Global Console](https://raw.githubusercontent.com/RobinaMirbahar/bridgespan-ai/main/assets/bridgespan_console_live.jpg)

In this article, I will walk through the exact failure modes of raw LLMs on civil-infrastructure math, how I wired deterministic 4-gate safety interlocks into Google ADK, how I collected the real global dataset, and how to deploy the tactical operator console serverlessly on **Google Cloud Run**.

---

## Why Raw LLMs Fail on Physical Bridge Safety

When I tested unguarded prompts on real bridge-dispatch scenarios, three failure patterns appeared immediately:

1. **Imperial (`ft-in`) vs. Metric (`m`) Arithmetic Traps:** North American trailers declare height in feet and inches (`13'-6"` = `4.115 m`), while many urban underpasses in Europe, Australia, Azerbaijan, and Pakistan post signs in meters (`3.95 m` or `3.0 m`). Worse, safe civil clearance requires a mandatory **`0.15 m` (`6 in`) dynamic suspension bounce & asphalt-overlay buffer**. An LLM that compares `4.11 m` against `4.15 m` without the bounce buffer approves a roof strike at highway speed.
2. **Silent Structural Overload:** A `12'-0"` mobile crane (`42.0 metric tons`) easily clears a `14'-2"` historic steel truss vertically—so height-only checks wave it through—even when the span's **FHWA Item 064 Operating Rating** is capped at `22.5 metric tons`.
3. **Blindness to Live River Pier Scour:** During heavy rain or monsoon surges, a bridge deck looks dry and unobstructed on GPS maps while fast-moving water erodes riverbed sediment from beneath **FHWA Item 113 scour-critical** pier footings.

---

## System Architecture: Cognitive Reasoning + Deterministic Hard Gates

In safety-critical physical engineering, **an LLM should orchestrate tools and explain telemetry—never hold unchecked authority over structural limits.**

Here is the architecture I implemented in [`RobinaMirbahar/bridgespan-ai`](https://github.com/RobinaMirbahar/bridgespan-ai):

```plaintext
┌──────────────────────────────────────────────────────────────────────┐
│           BridgeSpan AI Tactical Global Operator Console             │
│    8 Global Spans (US • AU • AZ • PK) • Dark CartoDB + OSRM Vector   │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│            Google ADK LlmAgent (Gemma 4 via LiteLLM)                 │
│  1. get_bridge_structural_profile() -> Clearance, Item 064, Item 113 │
│  2. get_live_river_scour_and_wind() -> USGS 15-min + GloFAS Gusts    │
│  3. compute_safe_bridge_dispatch()  -> Hard Civil Interlock Engine   │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│          4-Gate Deterministic Civil Safety Interlocks (Python)       │
│  • GATE 01 (Clearance): parse_height_m + 0.15m bounce > posted_m     │
│  • GATE 02 (Axle Mass): gross_tons > FHWA Item 064 operating_tons    │
│  • GATE 03 (Pier Scour): Item 113 critical & surge >= +1.80m -> LOCK │
│  • GATE 04 (Crosswind): high-sided & gust >= 65 km/h -> CLAMP 50km/h │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│        Validated Pydantic v2 Output (`BridgeDispatchAdvisory`)       │
│     Roadside LED VMS Gantry Banner + Green OSRM Safe Truck Bypass    │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 1. Killing the #1 Cause of Bridge Strikes: Deterministic `ft-in` ⇄ `m` Parsing

Instead of letting an LLM convert `"13'-6\""` or `"12'4\""` in token space, `bridgespan_agent/guardrails.py` parses every Imperial and Metric notation deterministically and adds the `0.15 m` (`6 in`) dynamic suspension bounce margin before evaluating clearance:

```python
import re

DYNAMIC_BOUNCE_BUFFER_M = 0.15  # Mandatory 6-inch suspension bounce & repaving buffer

def parse_height_to_meters(raw_height: str | float) -> float:
    """Deterministically parse '13'-6\"', '13ft 6in', '3.89 m', or '389 cm' into meters."""
    text = str(raw_height or "").strip().lower()

    imp_match = re.match(
        r"^\s*(\d+(?:\.\d+)?)\s*(?:'|ft|feet|foot)\s*[-\s]*(\d+(?:\.\d+)?)?\s*(?:\"|''|in|inch|inches)?\s*$",
        text,
    )
    if imp_match:
        feet = float(imp_match.group(1))
        inches = float(imp_match.group(2)) if imp_match.group(2) is not None else 0.0
        if inches >= 12.0:
            raise ValueError(f"Invalid inches ({inches}) in {raw_height!r}")
        return round((feet * 12.0 + inches) * 0.0254, 3)

    # Metric meters / centimeters handling ...
```

When a driver declares `13'-6"` (`4.115 m`) approaching Durham's Gregson Street trestle (`12'-4"` / `3.76 m`), the guardrail computes:

$$\text{Margin} = 3.76\text{ m} - (4.115\text{ m} + 0.15\text{ m}) = -0.505\text{ m}$$

Gate 01 trips immediately (`DIVERT_OVERHEIGHT_STRIKE_PREVENTED`), triggers the roadside LED Variable Message Sign (`🚨 OVERHEIGHT 13'-6" (4.12m) — DIVERT RIGHT NOW`), and switches the map vector onto the verified **OSRM high-clearance arterial bypass**.

---

## 2. Enforcing Structural Mass, Pier Flood-Scour & Crosswind Clamps

Inside `evaluate_bridge_interlocks()`, all four civil-engineering invariants execute in strict safety priority order:

```python
if scour_tripped:          # Item 113 scour-critical pier + >= 1.80 m river stage surge
    status = "CLOSE_BRIDGE_SCOUR_INTERLOCK"
    use_detour = True
elif height_tripped:       # Vehicle height + 0.15 m bounce > posted clearance
    status = "DIVERT_OVERHEIGHT_STRIKE_PREVENTED"
    use_detour = True
elif weight_tripped:       # Gross vehicle tons > FHWA Item 064 operating rating
    status = "DIVERT_OVERWEIGHT_LOAD_LIMIT"
    use_detour = True
elif wind_tripped:         # High-sided trailer + >= 65 km/h deck gust (e.g., Baku Khazri)
    status = "PROCEED_CLAMP_SPEED_50KMH"
    use_detour = False
    approved_speed = 50
else:
    status = "CLEAR_PRIMARY_ROUTE"
```

I also attached a Google ADK `before_tool_callback` (`bridge_adk_before_tool_guardrail`) directly to the `LlmAgent` so out-of-bounds tool arguments are sanitized before tool execution, and every final response is validated against the Pydantic v2 `BridgeDispatchAdvisory` schema.

---

## 3. Assembling a 100% Real Global Dataset (Zero Synthetic Toy Rows)

A safety benchmark is only as credible as its underlying physical data. Rather than inventing fake bridges, I wrote an automated multi-source ingestion pipeline (`collect_bridgespan_dataset.py`) pulling from **5 authoritative public APIs** and published the full corpus on Kaggle:

👉 **[BridgeSpan Bridge Strike, Load & Scour Dataset on Kaggle](https://www.kaggle.com/datasets/robinamirbahar/bridgespan-global-bridge-strike-load-scour)**

| Table | Records | Real Public Source |
| :--- | ---: | :--- |
| `fhwa_nbi_2024_hazard_bridges.csv` | **4,500** | Official 2024 US DOT **FHWA National Bridge Inventory** (`NC`, `NY`, `MA`, `PA`, `DC`, `MD`) with exact clearances, tonnage ratings & Item 113 scour codes |
| `osm_global_low_clearance_bridges.csv` | **309** | **OpenStreetMap Overpass API** low-clearance spans across the US, UK, Australia, Pakistan, and Azerbaijan with verbatim `maxheight` tags |
| `usgs_live_river_scour_telemetry.csv` | **1,436** | **USGS NWIS** 15-minute instantaneous river stage (`00065`) & discharge (`00060`) time series |
| `global_glofas_flood_and_wind_daily.csv` | **360** | **Copernicus GloFAS** river discharge + **Open-Meteo** 10m crosswind gusts & rainfall across 8 global corridors |
| `bridgespan_dispatch_benchmark_80.csv` | **80** | Verified 80-scenario heavy-truck benchmark with real **OSRM** primary vs. safe bypass distances (`8/8` `pytest` suite verifies 100% agreement) |

---

## 4. Designing a Tactical Deep-Tech Global Console

Civil dispatchers and fleet operators need zero-clutter situational awareness across continents—whether monitoring **Durham's 11-Foot-8+8 trestle**, **Washington D.C.'s Potomac Chain Bridge**, **Melbourne's Montague Street 3.0 m light-rail bridge**, **Baku's Bilajari overpass under 78 km/h Caspian *Khazri* gales**, or **Karachi's Nazimabad monsoon corridor**.

I built the frontend in Streamlit (`app.py`) with a matte-obsidian deep-tech visual language:
- **1-Click Global Span Matrix** switching seamlessly across the US, Australia, Azerbaijan, and Pakistan (plus a `🌍 GLOBAL WORLD VIEW` toggle).
- **Live CartoDB Dark Matter + OSRM Vector Map** rendering blocked spans as dashed crimson polylines and verified heavy-truck detours as glowing emerald routes—requiring **zero paid map API keys**.
- **4-Gate Deterministic Interlock Readout** paired with the **Gemma 4 + ADK Engineering Copilot** for interactive root-cause inspection.

---

## 5. Run Locally or Deploy Scale-to-Zero on Google Cloud Run

You can clone and run the entire system locally in under a minute (no API keys required for deterministic dispatch, telemetry explorer, and live OSRM map routing):

```bash
git clone https://github.com/RobinaMirbahar/bridgespan-ai.git
cd bridgespan-ai
pip install -r requirements.txt

# Verify all 80 benchmark scenarios & unit-conversion guardrails
pytest -v

# Launch the tactical operator console
streamlit run app.py
```

And because the repo ships with a production `Dockerfile`, deploying to **Google Cloud Run** with scale-to-zero (`$0` idle cost) takes a single command:

```bash
gcloud run deploy bridgespan-ai \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --min-instances 0
```

---

## Key Takeaways for Agent Builders

1. **Never Let Tokens Do Safety Math Alone:** Unit conversions (`13'-6"` -> `4.115 m`), structural load ratings, and flood-scour thresholds belong in deterministic Python interlocks tested by `pytest`—with the LLM handling tool orchestration and human-readable synthesis.
2. **Real Public Infrastructure APIs Are Goldmines:** Combining FHWA NBI, OpenStreetMap Overpass, USGS 15-minute water telemetry, Copernicus GloFAS, and OSRM gives your AI agents authentic physical grounding without spending a cent on proprietary data feeds.
3. **Open-Weights + Serverless Scales Cleanly:** Pairing **Gemma 4** and **Google ADK** with **Google Cloud Run** keeps infrastructure telemetry sovereign, auditable, and cost-efficient.

---

⭐ **Star & Fork the Code on GitHub:** [github.com/RobinaMirbahar/bridgespan-ai](https://github.com/RobinaMirbahar/bridgespan-ai)  
📊 **Explore the Dataset on Kaggle:** [kaggle.com/datasets/robinamirbahar/bridgespan-global-bridge-strike-load-scour](https://www.kaggle.com/datasets/robinamirbahar/bridgespan-global-bridge-strike-load-scour)  

*What physical-world infrastructure problem would you put deterministic AI guardrails in front of next? Drop your thoughts in the comments—and stay tuned for Part 2 (**FloodCrest AI**), where I tackle urban cloudburst spillways and commuter underpass flash-flood countdowns!*
