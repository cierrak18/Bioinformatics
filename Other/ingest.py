"""
ingest.py
================================================
This module reads ANY dataset, normalizes it into a standard format,
and hands it off to the classifier to determine what kind of objects
are in the data.

This module does:
    - Read CSV, JSON, or other file types from a folder
    - Normalize all field names and values
    - Detect what schema the data appears to follow
    - Hand each row to ObjectClassifier (classify.py)
    - Return a list of TrackedObject instances ready for motion analysis

The Taiwan filtering behavior is preserved — it is now one option
among many, handled by passing a country filter argument.

Issues currently arising:
    - Exception has occurred: _ArrayMemoryError
Unable to allocate 1.36 GiB for an array with shape (182450596,) and data type float64
    - Breakpoint: normalize
    
"""

import pandas as pd
import glob
import os
import json
import pathlib
from typing import Iterator, Dict, Any, Optional, List
from datetime import datetime


# ── CONFIGURATION ─────────────────────────────────────────────────────────────
# These were hardcoded in the original script.
# Now they are arguments so the same ingester works for any dataset.

DEFAULT_INPUT_FOLDER = "C:/Users/641808/OneDrive - BOOZ ALLEN HAMILTON/Documents/RIIA DRI/Datasets"
DEFAULT_OUTPUT_FILE  = "movement_merged.csv"


# ── KNOWN SCHEMA SIGNATURES ───────────────────────────────────────────────────
# The ingester uses these to detect what kind of data it is reading
# before the classifier runs. This is Tier 1 of the classification pipeline.

SCHEMA_SIGNATURES = {
    "people_movement": {
        "required": {"gadm_id", "country", "home_to_ping_distance_category", "distance_category_ping_fraction"},
        "optional": {"gadm_name", "polygon_level", "ds"}
    },
    "ais_maritime": {
        "required": {"mmsi", "lat", "lon"},
        "optional": {"imo", "vessel_name", "speed", "timestamp", "flag_state"}
    },
    "vehicle_tracking": {
        "required": {"vin", "lat", "lon"},
        "optional": {"license_plate", "timestamp", "speed", "vehicle_type"}
    },
    "generic_coordinates": {
        "required": {"lat", "lon"},
        "optional": {"timestamp", "id", "speed", "label"}
    },
}
"""cargo_tracking, device_tracking, person_movement...."""

# Distance category mapping — carried over from the original Taiwan script
DISTANCE_CATEGORY_MAP = {
    "0":         "pct_0km",
    "(0, 10)":   "pct_0_10km",
    "[10, 100)": "pct_10_100km",
    "100+":      "pct_100km_plus",
    "0km":       "pct_0km",
    "(0,10)":    "pct_0_10km",
    "[10,100)":  "pct_10_100km",
}


# ── DATAINGESTER CLASS ────────────────────────────────────────────────────────

class DataIngester:
    """
    Reads a file or folder of files and normalizes each row into
    a flat dictionary of fields. Detects the schema type so the
    classifier has a head start.

    Supported file types: csv, json
    Planned: ais (NMEA), gpx, xml
    """

    def __init__(
        self,
        input_path: str,
        country_filter: Optional[str] = None,   # e.g. "TWN" — replaces the hardcoded TWN filter
        file_pattern: str = "*.csv"
    ):
        self.input_path    = input_path
        self.country_filter = country_filter.upper() if country_filter else None
        self.file_pattern  = file_pattern
        self.detected_schema: Optional[str] = None
        self.files_processed = 0
        self.rows_loaded     = 0
        self.rows_filtered   = 0

    # ── PUBLIC INTERFACE ──────────────────────────────────────────────────────

    def read_all(self) -> pd.DataFrame:
        """
        Main entry point. Reads all files, applies optional country filter,
        normalizes fields, and returns a single merged DataFrame.

        This replaces the load_and_filter() + clean_and_pivot() functions
        from the original script, but keeps the same logic intact.
        """
        raw_frames = self.load_files()

        if not raw_frames:
            raise ValueError(
                f"No usable rows found in: {self.input_path}\n"
                f"Filter applied: country={self.country_filter or 'none'}"
            )

        merged = pd.concat(raw_frames, ignore_index=True)
        self.rows_loaded = len(merged)

        # Detect schema from column names
        self.detected_schema = self.detect_schema(set(merged.columns.str.lower()))
        print(f"\nDetected schema: {self.detected_schema or 'unknown'}")

        # Normalize based on detected schema
        normalized = self.normalize(merged)
        self.rows_filtered = len(normalized)

        self.print_summary()
        return normalized

    def read_as_dicts(self) -> Iterator[Dict[str, Any]]:
        """
        Yields one normalized row at a time as a dictionary.
        Used by the classifier to process rows individually.
        """
        df = self.read_all()
        for _, row in df.iterrows():
            yield row.to_dict()

    # ── FILE LOADING ──────────────────────────────────────────────────────────

    def load_files(self) -> List[pd.DataFrame]:
        """
        Detects whether input_path is a single file or a folder,
        then loads accordingly. Mirrors the glob logic in the original script.
        """
        p = pathlib.Path(self.input_path)

        if p.is_file():
            files = [str(p)]
        elif p.is_dir():
            files = glob.glob(os.path.join(self.input_path, self.file_pattern))
        else:
            raise FileNotFoundError(f"Path not found: {self.input_path}")

        if not files:
            raise FileNotFoundError(
                f"No files matching '{self.file_pattern}' in: {self.input_path}"
            )

        print(f"Found {len(files)} file(s). Loading...")
        frames = []

        for f in files:
            df = self.read_single_file(f)
            if df is None:
                continue

            # Apply country filter if specified
            if self.country_filter and "country" in df.columns:
                df = df[df["country"].str.upper() == self.country_filter].copy()
                if df.empty:
                    print(f"  – {os.path.basename(f)}: no rows matching country={self.country_filter}")
                    continue

            frames.append(df)
            self.files_processed += 1
            print(f"  ✓ {os.path.basename(f)}: {len(df)} rows loaded")

        return frames

    def read_single_file(self, filepath: str) -> Optional[pd.DataFrame]:
        """
        Reads one file. Handles encoding issues - try UTF-8 first, fall back to latin-1.
        """
        ext = pathlib.Path(filepath).suffix.lower()

        try:
            if ext == ".csv":
                try:
                    df = pd.read_csv(filepath, encoding="utf-8")
                except UnicodeDecodeError:
                    df = pd.read_csv(filepath, encoding="latin-1")

            elif ext == ".json":
                with open(filepath, encoding="utf-8") as f:
                    data = json.load(f)
                df = pd.DataFrame(data if isinstance(data, list) else [data])

            else:
                print(f"  ✗ {os.path.basename(filepath)}: unsupported type '{ext}' — skipping")
                return None

            # Standardize column names immediately on load
            df.columns = df.columns.str.strip().str.lower()
            return df

        except Exception as e:
            print(f"  ✗ {os.path.basename(filepath)}: ERROR — {e}")
            return None

    # ── SCHEMA DETECTION ──────────────────────────────────────────────────────

    def detect_schema(self, columns: set) -> Optional[str]:
        """
        Checks column names against known schema signatures.
        Returns the best match, or None if no match found.
        This is Tier 1 of the classification pipeline at the file level.
        """
        for schema_name, sig in SCHEMA_SIGNATURES.items():
            required = sig["required"]
            if required.issubset(columns):
                return schema_name
        return None

    # ── NORMALIZATION ─────────────────────────────────────────────────────────

    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Routes to the correct normalization function based on detected schema.
        If schema is unknown, applies generic normalization.
        build out vehicle tracking, device_tracking, generic_coordinates,...
        """
        if self.detected_schema == "people_movement":
            return self.normalize_people_movement(df)
        elif self.detected_schema == "ais_maritime":
            return self.normalize_ais(df)
        else:
            return self.normalize_generic(df)

    def normalize_people_movement(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalization logic carried directly over from the original script's
        clean_and_pivot() function. Handles encoding fixes, date parsing,
        distance category renaming, and pivoting.
        """
        # Fix encoding in region names (handles residual mojibake)
        if "gadm_name" in df.columns:
            df["gadm_name"] = (
                df["gadm_name"]
                .str.encode("latin-1", errors="ignore")
                .str.decode("utf-8", errors="ignore")
            )

        # Parse date column
        if "ds" in df.columns:
            df["ds"] = pd.to_datetime(df["ds"])

        # Normalize distance category labels
        if "home_to_ping_distance_category" in df.columns:
            df["home_to_ping_distance_category"] = (
                df["home_to_ping_distance_category"]
                .str.strip()
                .map(lambda x: DISTANCE_CATEGORY_MAP.get(x, x))
            )

        # Pivot: one row per (region × date)
        index_cols = [c for c in ["gadm_id", "gadm_name", "country", "polygon_level", "ds"] if c in df.columns]

        pivoted = df.pivot_table(
            index=index_cols,
            columns="home_to_ping_distance_category",
            values="distance_category_ping_fraction",
            aggfunc="first"
        ).reset_index()

        pivoted.columns.name = None

        # Ensure all 4 distance columns exist (even if some files don't have all categories)
        for col in ["pct_0km", "pct_0_10km", "pct_10_100km", "pct_100km_plus"]:
            if col not in pivoted.columns:
                pivoted[col] = float("nan")

        # Sort by date then region
        sort_cols = [c for c in ["ds", "gadm_id"] if c in pivoted.columns]
        pivoted = pivoted.sort_values(sort_cols).reset_index(drop=True)

        # Reorder columns
        base_cols  = [c for c in ["ds", "gadm_id", "gadm_name", "country", "polygon_level"] if c in pivoted.columns]
        dist_cols  = ["pct_0km", "pct_0_10km", "pct_10_100km", "pct_100km_plus"]
        other_cols = [c for c in pivoted.columns if c not in base_cols + dist_cols]
        pivoted = pivoted[base_cols + dist_cols + other_cols]

        return pivoted

    def normalize_ais(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalizes AIS maritime data into a standard format with
        consistent column names and parsed timestamps.
        """
        rename_map = {
            "latitude":  "lat",
            "longitude": "lon",
            "speed_knots": "speed",
            "time": "timestamp",
            "ts": "timestamp",
        }
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

        return df.sort_values("timestamp").reset_index(drop=True) if "timestamp" in df.columns else df

    def normalize_generic(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Minimal normalization for datasets with unknown schemas.
        Attempts to parse any column that looks like a date.
        Preserves all fields as-is.
        """
        for col in df.columns:
            if any(kw in col for kw in ["date", "time", "ts", "ds"]):
                try:
                    df[col] = pd.to_datetime(df[col], errors="coerce")
                except Exception:
                    pass
        return df
    """def cargo_tracking, device_tracking, person_movement.................................."""
    # ── OUTPUT ────────────────────────────────────────────────────────────────

    def save(self, df: pd.DataFrame, output_file: str = DEFAULT_OUTPUT_FILE) -> None:
        """
        Saves the normalized DataFrame to CSV.
        Uses utf-8-sig encoding for Excel compatibility,
        same as the original script.
        """
        df.to_csv(output_file, index=False, encoding="utf-8-sig")
        print(f"\n✅ Saved to: {output_file}")

    def print_summary(self) -> None:
        print(f"\n── Ingestion Summary ──────────────────────────")
        print(f"  Files processed : {self.files_processed}")
        print(f"  Rows loaded     : {self.rows_loaded}")
        print(f"  Rows after filter: {self.rows_filtered}")
        print(f"  Schema detected : {self.detected_schema or 'unknown'}")
        print(f"───────────────────────────────────────────────")


# ── MAIN — preserves the original script's behavior exactly ───────────────────

def main():
    """
    Running this file directly replicates the original Taiwan filter script
    exactly — same folder, same output file, same TWN filter.
    The only difference is the code is now part of the broader pipeline.
    """
    ingester = DataIngester(
        input_path     = DEFAULT_INPUT_FOLDER,
        country_filter = "TWN",         # same as original hardcoded filter
        file_pattern   = "*.csv"
    )

    df = ingester.read_all()

    print(f"\nDate range     : {df['ds'].min().date()} → {df['ds'].max().date()}")
    print(f"Unique regions : {df['gadm_id'].nunique()}")
    print(f"\nPreview:")
    print(df.head(10).to_string(index=False))

    ingester.save(df, DEFAULT_OUTPUT_FILE)


if __name__ == "__main__":
    main()
