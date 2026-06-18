"""
classify.py
================================================
Part 2 -Object Classification Pipeline

Takes a normalized row of data (a dictionary of fields) and determines
what kind of object it represents. Returns a typed TrackedObject subclass
instance ready for motion analysis.

This is the layer that sits between ingest.py and core.py.
It answers the question: "what IS this thing?"

Classification runs in four tiers:
  Tier 1 — Field name signatures
  Tier 2 — Value pattern matching (regex)
  Tier 3 — External registry lookup (stubs)
  Tier 4 — UnknownObject fallback
"""

import re
import uuid
from typing import Dict, Any, Tuple, Optional
from core import (
    TrackedObject, Person, Vehicle, Vessel,
    PopulationAggregate, Cargo, Device, UnknownObject
)


# ── TIER 1: FIELD SIGNATURES ──────────────────────────────────────────────────
# If these field names appear in the data, we can be reasonably confident
# about the object type without even looking at the values.

FIELD_SIGNATURES: Dict[str, set] = {
    "Vessel":              {"imo", "mmsi", "vessel_name", "flag_state"},
    "Vehicle":             {"vin", "license_plate", "vehicle_type"},
    "Person":              {"ssn", "passport", "name", "social_media"},
    "PopulationAggregate": {"gadm_id", "polygon_level"},
    "Device":              {"device_id", "signal_type", "beacon_id"},
    "Cargo":               {"lot_number", "manifest", "commodity_type"},
}

# How many signature fields need to match to count as a hit
SIGNATURE_THRESHOLD = 1  # even one strong field is enough for some types


# ── TIER 2: VALUE PATTERNS ────────────────────────────────────────────────────
# If field names aren't obvious, the values themselves may reveal the type.
# Each pattern is a regex applied against all values in the row.

VALUE_PATTERNS: Dict[str, list] = {
    # VIN: 17 chars, excludes I, O, Q
    "Vehicle": [
        r"\b[A-HJ-NPR-Z0-9]{17}\b"
    ],
    # MMSI: exactly 9 digits | IMO: "IMO" prefix + 7 digits
    "Vessel": [
        r"\b\d{9}\b",
        r"\bIMO\d{7}\b"
    ],
    # US SSN format — treat as PII, handle per data privacy policy
    "Person": [
        r"\b\d{3}-\d{2}-\d{4}\b"
    ],
    # MAC address format — likely a device
    "Device": [
        r"\b([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b"
    ],
    # GADM ID format: letters.numbers.numbers_numbers
    "PopulationAggregate": [
        r"\b[A-Z]{2,3}\.\d+\.\d+_\d+\b"
    ],
}


# ── CLASS REGISTRY ────────────────────────────────────────────────────────────
# Maps the string label from the classifier to the actual Python class.
# To add a new object type, add the subclass to core.py and register it here.

CLASS_REGISTRY: Dict[str, type] = {
    "Vessel":              Vessel,
    "Vehicle":             Vehicle,
    "Person":              Person,
    "PopulationAggregate": PopulationAggregate,
    "Device":              Device,
    "Cargo":               Cargo,
    "Unknown":             UnknownObject,
}


# ── OBJECTCLASSIFIER ──────────────────────────────────────────────────────────

class ObjectClassifier:
    """
    Runs the four-tier classification pipeline on a single row of data.
    Returns a (label, confidence, notes) tuple.

    Confidence is a rough 0.0–1.0 score:
      0.80+ = high confidence (field signature match)
      0.65–0.79 = medium confidence (pattern or external match)
      0.40–0.64 = low confidence (partial match)
      below 0.40 = unknown, flag for review
    """

    @staticmethod
    def classify(raw_fields: Dict[str, Any]) -> Tuple[str, float, str]:
        keys = {k.lower().strip() for k in raw_fields.keys()}

        # ── Tier 1: Field signatures ──────────────────────────────────────────
        best_label = None
        best_score = 0

        for label, sig in FIELD_SIGNATURES.items():
            matches = sig & keys
            if len(matches) >= SIGNATURE_THRESHOLD:
                score = len(matches) / len(sig)     # more matches = higher confidence
                if score > best_score:
                    best_score = score
                    best_label = label
                    best_notes = f"Field signature match: {matches}"

        if best_label:
            return best_label, round(0.60 + best_score * 0.20, 2), best_notes

        # ── Tier 2: Value pattern matching ────────────────────────────────────
        text_blob = " ".join(str(v) for v in raw_fields.values())

        for label, patterns in VALUE_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, text_blob):
                    return label, 0.70, f"Value pattern match: {pat}"

        # ── Tier 3: External registry lookup (stubs) ──────────────────────────
        # NOTE: Real network calls go here. Must use approved, credentialed API clients.
        # See external.py for stubs.
        from external import resolve_with_registries
        label, conf, notes = resolve_with_registries(raw_fields)
        if label != "Unknown":
            return label, conf, notes

        # ── Tier 4: Unknown fallback ──────────────────────────────────────────
        # Data is not discarded. UnknownObject still gets processed by the
        # motion layer. An analyst can promote it later once identified.
        return "Unknown", 0.30, "No signature, pattern, or registry match — flagged for review"


# ── BUILD FUNCTION ────────────────────────────────────────────────────────────

def build_tracked_object(raw_fields: Dict[str, Any]) -> TrackedObject:
    """
    The main entry point for this module.
    Takes a raw row of data, classifies it, and returns the correct
    TrackedObject subclass with fields populated from the raw data.

    Usage:
        from classify import build_tracked_object
        obj = build_tracked_object({"gadm_id": "TWN.1.1_1", "country": "TWN", ...})
        # returns a PopulationAggregate instance
    """
    label, confidence, notes = ObjectClassifier.classify(raw_fields)
    cls = CLASS_REGISTRY.get(label, UnknownObject)
    obj = cls.from_dict(raw_fields)

    # Store classification metadata regardless of type
    obj.metadata["classification_label"]      = label
    obj.metadata["classification_confidence"] = confidence
    obj.metadata["classification_notes"]      = notes

    # Flag unknowns explicitly
    if label == "Unknown":
        obj.flagged_for_review = True

    return obj


# ── PROMOTE UNKNOWN ───────────────────────────────────────────────────────────

def promote_unknown(obj: UnknownObject, target_type: str) -> TrackedObject:
    """
    Allows an analyst to promote an UnknownObject to a typed subclass
    after manual review. Preserves original raw fields and classification history.

    Usage:
        promoted = promote_unknown(unknown_obj, "Vessel")
    """
    if target_type not in CLASS_REGISTRY:
        raise ValueError(f"Unknown target type: {target_type}. "
                         f"Valid types: {list(CLASS_REGISTRY.keys())}")

    cls = CLASS_REGISTRY[target_type]
    raw = obj.metadata.get("raw", {})
    promoted = cls.from_dict(raw)

    # Preserve history
    promoted.metadata["promoted_from"]          = "UnknownObject"
    promoted.metadata["original_confidence"]    = obj.metadata.get("classification_confidence")
    promoted.metadata["promoted_by"]            = "analyst"

    print(f"  ✓ Promoted {obj.object_id} from UnknownObject → {target_type}")
    return promoted
