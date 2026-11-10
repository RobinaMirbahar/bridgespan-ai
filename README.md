# 🌉 BridgeSpan AI — Heavy-Truck Bridge Strike, Axle Load & Flood-Scour Safety Agent

![BridgeSpan AI Cover](assets/bridgespan_banner.jpg)

[![Google ADK](https://img.shields.io/badge/Google_ADK-Agent_Framework-4285F4?logo=google)](https://google.github.io/adk-docs/)
[![Gemma 4 / Gemini](https://img.shields.io/badge/Model-Gemma_4_%2F_Gemini-0F9D58?logo=googlecloud)](https://ai.google.dev/gemma)
[![Cloud Run](https://img.shields.io/badge/Deploy-Google_Cloud_Run-FFCA28?logo=googlecloud)](https://cloud.google.com/run)
[![Kaggle Dataset](https://img.shields.io/badge/Kaggle_Dataset-BridgeSpan_10%2F10-20BEFF?logo=kaggle)](https://www.kaggle.com/datasets/robinamirbahar/bridgespan-global-bridge-strike-load-scour)

**Author:** Robina Mirbahar (*Google Developer Expert in AI/ML & Cloud*)

---

## 🚨 The Real-World Problem

Every year across the United States, Europe, Australia, and Asia, thousands of commercial semi-trailers, double-deck box trucks, and buses slam into low-clearance bridges—most famously Durham's **`11-foot-8+8` ("Can Opener") rail trestle**, Boston's **Storrow Drive**, New York's **Hutchinson River Parkway stone arches**, and Melbourne's **Montague Street 3.0 m overpass**. Beyond overhead strikes, **hydraulic pier scour** during flash-flood surges is the **#1 cause of highway bridge collapse in the United States** (FHWA Item 113), while overweight cranes and freight haulers routinely overstress aging load-posted trusses.

Raw LLM navigation assistants fail catastrophically on these physical constraints because they:
1. Hallucinate arithmetic across **Imperial (`13'-6"`, `12'-4"`) vs. Metric (`3.89 m`, `3.0 m`)** roadside signs and omit mandatory **`0.15 m` (`6 in`)** dynamic suspension bounce buffers.
2. Route heavy vehicles (`34.5 t`–`42.0 t`) across historic parkways or load-posted trusses (`15.0 t`–`22.5 t`).
3. Ignore live **USGS 15-minute river stage surges** acting on scour-critical bridge piers.

I built **BridgeSpan AI** to solve this end-to-end by pairing **Google ADK + Gemma / Gemini** with **deterministic civil-engineering safety interlocks**, **live OSRM heavy-truck detour geometry on an interactive Leaflet map**, and a **100% real multi-source benchmark dataset**.

---

## 🏗️ Architecture & Deterministic Civil Guardrails

```
Approaching Truck (ft-in or m height, gross tons) + Live USGS / GloFAS River & Wind Telemetry
                                      │
                                      ▼
                    ┌───────────────────────────────────┐
                    │   Google ADK LlmAgent (Gemma 3)   │
                    │  3-Step Tool Trajectory + Schema  │
                    └─────────────────┬─────────────────┘
                                      │
                                      ▼
       ┌──────────────────────────────────────────────────────────────┐
       │        Deterministic Civil Safety Guardrail Engine           │
       │  1. Pier Scour Closure: Item 113 + Surge >= 1.80 m -> CLOSE  │
       │  2. Strike Interlock: Height_m + 0.15m Bounce > Clearance    │
       │  3. Load Interlock: Gross Tons > FHWA Item 064 Operating t   │
       │  4. Crosswind Rollover: Gust >= 65 km/h -> Clamp 50 km/h     │
       └──────────────────────────────┬───────────────────────────────┘
                                      │
                                      ▼
     Live Leaflet + OSRM Green Safe Truck Bypass Map + LED Roadside VMS Sign
```

---

## 📊 Real Multi-Source Dataset (`dataset/`)

All 5 tables in `dataset/` were collected directly from authoritative public civil & hydrological APIs via `collect_bridgespan_dataset.py` and include complete column-level schemas in `dataset/dataset-metadata.json`:

| File | Rows | Real Upstream Source |
| :--- | ---: | :--- |
| `fhwa_nbi_2024_hazard_bridges.csv` | `4,500` | Official 2024 US DOT **FHWA National Bridge Inventory (NBI)** (`NC`, `NY`, `MA`, `PA`, `DC`, `MD`) |
| `osm_global_low_clearance_bridges.csv` | `309` | **OpenStreetMap Overpass API** global `maxheight` bridges (`US`, `UK`, `AU`, `PK`, `AZ`) |
| `usgs_live_river_scour_telemetry.csv` | `1,436` | **USGS NWIS** 15-minute instantaneous river stage (`00065`) & discharge (`00060`) |
| `global_glofas_flood_and_wind_daily.csv` | `360` | **Copernicus GloFAS** river discharge + **Open-Meteo** wind gusts & precipitation |
| `bridgespan_dispatch_benchmark_80.csv` | `80` | Verified 80-scenario heavy-truck benchmark with real **OSRM** primary vs. safe bypass distances |

---

## 🚀 Quickstart

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the deterministic civil guardrail & 80-scenario benchmark test suite
pytest -v

# 3. Launch the interactive BridgeSpan AI dashboard + live Leaflet/OSRM map
streamlit run app.py
```

### Deploy to Google Cloud Run (Scale-to-Zero)

```bash
gcloud run deploy bridgespan-ai \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --min-instances 0
```
