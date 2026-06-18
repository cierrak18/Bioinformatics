"""
external.py
================================================
Part 4 - External Registry Lookup Stubs (Tier 3 Classification)

These functions are placeholders. Each one represents a real external
API that can be queried when field signatures and value patterns
are not enough to classify an object.

All external calls must go through enterprise-approved, credentialed
API clients before being used in production.
"""

from typing import Dict, Any, Tuple
from ingest import DataIngester
from classify import build_tracked_object
from core import (
    TrackedObject, PopulationAggregate,
    Location, MovementRecord, TimePeriod, Anomaly, AnomalyType
)
from typing import List, Dict, Any, Optional
import pandas as pd
from datetime import date

def resolve_with_registries(raw: Dict[str, Any]) -> Tuple[str, float, str]:
    """
    Attempts to classify an object using external registries.
    Returns (label, confidence, notes).

    Each block below is a stub — replace with real API calls
    once credentials are available.
    """

    # ── Vehicle: NHTSA vPIC VIN decoder ──────────────────────────────────────
    # https://vpic.nhtsa.dot.gov/api/
    if "vin" in raw:
        # Real call: GET https://vpic.nhtsa.dot.gov/api/vehicles/decodevin/{vin}?format=json
        # Parse response to confirm vehicle type, make, model, year
        return "Vehicle", 0.65, "VIN present — NHTSA lookup recommended"

    # ── Vessel: MarineTraffic / VesselFinder AIS ──────────────────────────────
    # https://servicedocs.marinetraffic.com/
    # https://api.vesselfinder.com/docs/
    if "mmsi" in raw or "imo" in raw:
        # Real call: GET https://services.marinetraffic.com/api/exportvessel/v:8/{api_key}/mmsi:{mmsi}
        return "Vessel", 0.65, "MMSI/IMO present — AIS registry lookup recommended"

    # ── Aircraft: OpenSky Network ─────────────────────────────────────────────
    # https://opensky-network.org/data/api
    if "icao24" in raw or "callsign" in raw:
        # Real call: GET https://opensky-network.org/api/states/all?icao24={icao24}
        return "Aircraft", 0.65, "ICAO24/callsign present — OpenSky lookup recommended"

    # ── Location: GADM / OpenStreetMap Nominatim ──────────────────────────────
    # https://nominatim.org/
    if "gadm_id" in raw:
        return "PopulationAggregate", 0.75, "GADM ID confirmed"

    # Nothing resolved
    return "Unknown", 0.0, "No external hints found"


"""
pipeline.py
================================================
 Main Pipeline Runner

Wires together all modules:
  ingest.py → classify.py → core.py (motion) → anomaly detection

Run this file to process a dataset end-to-end.
"""




# ── MOTION BUILDER ────────────────────────────────────────────────────────────

def build_movement_record(obj: TrackedObject, row: Dict[str, Any]) -> MovementRecord:
    """
    Constructs a MovementRecord from a classified object and its raw row data.
    For PopulationAggregate objects (Facebook data), displacement is derived
    from the distance band fractions rather than GPS coordinates.
    """
    record = MovementRecord(object_id=obj.object_id)

    # For coordinate-based data (vessels, vehicles, devices)
    if "lat" in row and "lon" in row:
        record.observed_positions.append({
            "lat":       row["lat"],
            "lon":       row["lon"],
            "timestamp": row.get("timestamp") or row.get("ds"),
        })
        record.position_confidence = "exact"

    # For population aggregate data (Facebook movement distribution)
    elif isinstance(obj, PopulationAggregate):
        # Displacement is represented by the distance band fractions
        # pct_0km = stayed home, pct_100km_plus = long distance movement
        pct_0km        = row.get("pct_0km", 0) or 0
        pct_100km_plus = row.get("pct_100km_plus", 0) or 0

        # Weighted mobility score as a proxy for displacement
        weights = {
            "pct_0km":        0.0,
            "pct_0_10km":     5.0,     # midpoint of band in km
            "pct_10_100km":   55.0,
            "pct_100km_plus": 150.0,
        }
        mobility_score = sum(
            max(0, row.get(col, 0) or 0) * weight
            for col, weight in weights.items()
        )

        record.displacement_km     = round(mobility_score, 2)
        record.position_confidence = "county-level"
        record.trajectory          = f"0km:{pct_0km:.2%} | 100km+:{pct_100km_plus:.2%}"

    return record


# ── ANOMALY DETECTION ─────────────────────────────────────────────────────────

def detect_anomalies(
    record: MovementRecord,
    baseline_mean: float,
    baseline_std: float,
    threshold_z: float = 2.0
) -> List[Anomaly]:
    """
    Compares a movement record against a baseline and flags deviations.
    For population data, the baseline is the average mobility score
    for that region over the baseline period.
    """
    anomalies = []

    if record.displacement_km is None or baseline_std == 0:
        return anomalies

    z_score = (record.displacement_km - baseline_mean) / baseline_std

    if abs(z_score) >= threshold_z:
        anomaly_type = (
            AnomalyType.UNEXPECTED_DISPLACEMENT if z_score > 0
            else AnomalyType.STATIONARY_TOO_LONG
        )
        anomalies.append(Anomaly(
            object_id           = record.object_id,
            record_id           = record.record_id,
            anomaly_type        = anomaly_type,
            deviation_score     = round(abs(z_score), 3),
            baseline_reference  = "baseline_period",
            affected_attributes = ["displacement_km"],
            notes               = f"z={z_score:.2f} vs baseline mean={baseline_mean:.2f}km"
        ))

    return anomalies


# ── FULL PIPELINE ─────────────────────────────────────────────────────────────

def run_pipeline(
    input_folder:   str,
    country_filter: Optional[str] = None,
    output_file:    str = "pmmr_output.csv"
) -> pd.DataFrame:
    """
    Runs the full PMMR pipeline end-to-end:
      1. Ingest files from folder
      2. Classify each row → TrackedObject
      3. Build MovementRecord per object
      4. Detect anomalies
      5. Return results as DataFrame

    Example — Taiwan population data (replicates original script behavior):
        df = run_pipeline(
            input_folder   = "C:/path/to/datasets",
            country_filter = "TWN",
            output_file    = "taiwan_movement_merged.csv"
        )

    Example — Maritime data, no country filter:
        df = run_pipeline(
            input_folder = "C:/path/to/ais_data",
            output_file  = "maritime_output.csv"
        )
    """
    # ── Step 1: Ingest ────────────────────────────────────────────────────────
    ingester = DataIngester(
        input_path     = input_folder,
        country_filter = country_filter,
        file_pattern   = "*.csv"
    )
    df = ingester.read_all()

    # ── Step 2 & 3: Classify + build movement records ─────────────────────────
    results = []
    objects: Dict[str, TrackedObject] = {}
    records: List[MovementRecord]     = []

    for _, row in df.iterrows():
        raw = row.to_dict()
        obj = build_tracked_object(raw)
        objects[obj.object_id] = obj
        record = build_movement_record(obj, raw)
        records.append(record)

        results.append({
            "object_id":            obj.object_id,
            "object_type":          obj.object_type,
            "classification_conf":  obj.metadata.get("classification_confidence"),
            "flagged_unknown":      isinstance(obj, type) and obj.object_type == "UnknownObject",
            "displacement_km":      record.displacement_km,
            "position_confidence":  record.position_confidence,
            "date":                 raw.get("ds") or raw.get("timestamp"),
            "source_dataset":       obj.source_dataset,
        })

    # ── Step 4: Anomaly detection (requires baseline — placeholder values) ────
    # In production, baseline_mean and baseline_std would be computed
    # from historical data for each object's region and time period.
    PLACEHOLDER_BASELINE_MEAN = 15.0    # km — replace with real baseline
    PLACEHOLDER_BASELINE_STD  = 8.0     # km — replace with real baseline

    anomaly_counts = {}
    for record in records:
        anoms = detect_anomalies(
            record,
            baseline_mean = PLACEHOLDER_BASELINE_MEAN,
            baseline_std  = PLACEHOLDER_BASELINE_STD,
        )
        anomaly_counts[record.object_id] = len(anoms)

    # ── Step 5: Compile output ────────────────────────────────────────────────
    result_df = pd.DataFrame(results)
    result_df["anomaly_count"] = result_df["object_id"].map(anomaly_counts).fillna(0).astype(int)
    result_df = result_df.sort_values("date").reset_index(drop=True)

    ingester.save(result_df, output_file)

    print(f"\n── Pipeline Summary ────────────────────────────")
    print(f"  Total objects processed : {len(objects)}")
    print(f"  Movement records built  : {len(records)}")
    print(f"  Anomalies flagged       : {result_df['anomaly_count'].sum()}")
    print(f"  Unknown objects         : {result_df[result_df['object_type'] == 'UnknownObject'].shape[0]}")
    print(f"───────────────────────────────────────────────")

    return result_df


# ── ENTRY POINT ───────────────────────────────────────────────────────────────

if __name__ == "__main__":

    # Taiwan population movement — same behavior as the original filter script
    df = run_pipeline(
        input_folder   = "C:/Users/641808/OneDrive - BOOZ ALLEN HAMILTON/Documents/RIIA DRI/Datasets",
        country_filter = "TWN",
        output_file    = "taiwan_movement_merged.csv"
    )

    print("\nPreview:")
    print(df.head(10).to_string(index=False))
