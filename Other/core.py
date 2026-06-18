"""
core.py
================================================
Part 3 - Identity & Behavior Layer Class Definitions

Identity layer:  TrackedObject (base) + subclasses
Behavior layer:  Location, MovementRecord, TimePeriod, Anomaly

These classes are intentionally generic. They do not know about
Facebook data, Taiwan, or any specific dataset. That knowledge
lives in ingest.py and classify.py.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import uuid


# ── ENUMS ─────────────────────────────────────────────────────────────────────

class PolygonLevel(int, Enum):
    COUNTRY = 0
    STATE   = 1
    COUNTY  = 2

class AnomalyType(str, Enum):
    UNEXPECTED_DISPLACEMENT = "unexpected_displacement"
    STATIONARY_TOO_LONG     = "stationary_too_long"
    CROSSED_BOUNDARY        = "crossed_boundary"
    DENSITY_CHANGE          = "density_change"
    PATH_DEVIATION          = "path_deviation"
    PROXIMITY_BREACH        = "proximity_breach"
    IMPOSSIBLE_SPEED        = "impossible_speed"

class FlowDirection(str, Enum):
    INTERNAL     = "internal"
    CROSS_BORDER = "cross_border"
    UNKNOWN      = "unknown"


# ══════════════════════════════════════════════════════════════════════════════
# IDENTITY LAYER — what the thing IS
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class TrackedObject:
    """
    Base class for any object that can be tracked.
    Holds only what is universally true across all trackable things.
    Subclasses add the identifiers specific to their type.
    """
    object_id:      str
    object_type:    str
    source_dataset: str
    metadata:       Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "TrackedObject":
        """
        Generic fallback constructor. Subclasses override this
        to map their specific fields from raw data.
        """
        return cls(
            object_id      = str(
                raw.get("object_id") or
                raw.get("id") or
                raw.get("gadm_id") or
                raw.get("mmsi") or
                raw.get("vin") or
                raw.get("device_id") or
                f"auto-{str(uuid.uuid4())[:8]}"
            ),
            object_type    = cls.__name__,
            source_dataset = str(raw.get("source_dataset", "unknown")),
            metadata       = {"raw": raw}
        )

    def __repr__(self):
        return f"<{self.object_type} id={self.object_id}>"


# ── SUBCLASSES ────────────────────────────────────────────────────────────────

@dataclass
class Person(TrackedObject):
    name:                   Optional[str]       = None
    nationality:            Optional[str]       = None
    ssn_or_national_id:     Optional[str]       = None  # PII — handle per policy
    social_media_handles:   List[str]           = field(default_factory=list)
    age_range:              Optional[str]       = None
    affiliation:            Optional[str]       = None

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "Person":
        base = TrackedObject.from_dict.__func__(cls, raw)
        base.name               = raw.get("name")
        base.nationality        = raw.get("nationality")
        base.ssn_or_national_id = raw.get("ssn") or raw.get("national_id")
        base.age_range          = raw.get("age_range")
        base.affiliation        = raw.get("affiliation")
        return base


@dataclass
class Vehicle(TrackedObject):
    vin:                Optional[str] = None
    license_plate:      Optional[str] = None
    vehicle_type:       Optional[str] = None
    registered_country: Optional[str] = None
    operator:           Optional[str] = None

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "Vehicle":
        base = TrackedObject.from_dict.__func__(cls, raw)
        base.vin                = raw.get("vin")
        base.license_plate      = raw.get("license_plate")
        base.vehicle_type       = raw.get("vehicle_type")
        base.registered_country = raw.get("registered_country") or raw.get("country")
        base.operator           = raw.get("operator")
        return base


@dataclass
class Vessel(TrackedObject):
    imo_number:     Optional[str]   = None
    mmsi:           Optional[str]   = None
    vessel_name:    Optional[str]   = None
    flag_state:     Optional[str]   = None
    vessel_type:    Optional[str]   = None
    tonnage:        Optional[float] = None
    operator:       Optional[str]   = None

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "Vessel":
        base = TrackedObject.from_dict.__func__(cls, raw)
        base.imo_number  = raw.get("imo") or raw.get("imo_number")
        base.mmsi        = raw.get("mmsi")
        base.vessel_name = raw.get("vessel_name") or raw.get("name")
        base.flag_state  = raw.get("flag_state") or raw.get("country")
        base.vessel_type = raw.get("vessel_type")
        base.tonnage     = raw.get("tonnage")
        base.operator    = raw.get("operator")
        return base


@dataclass
class PopulationAggregate(TrackedObject):
    """
    Represents a population group defined by an administrative boundary.
    This is the object type used for the Facebook Movement Distribution data.
    The 'object_id' maps to gadm_id.
    """
    gadm_id:              Optional[str] = None
    gadm_name:            Optional[str] = None
    country:              Optional[str] = None
    polygon_level:        Optional[int] = None
    estimated_population: Optional[int] = None
    sample_size:          Optional[int] = None

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "PopulationAggregate":
        base = TrackedObject.from_dict.__func__(cls, raw)
        base.gadm_id              = raw.get("gadm_id")
        base.gadm_name            = raw.get("gadm_name")
        base.country              = raw.get("country")
        base.polygon_level        = raw.get("polygon_level")
        base.estimated_population = raw.get("estimated_population")
        base.sample_size          = raw.get("facebook_user_sample_size") or raw.get("sample_size")
        return base


@dataclass
class Cargo(TrackedObject):
    lot_number:           Optional[str]   = None
    commodity_type:       Optional[str]   = None
    weight:               Optional[float] = None
    origin_manifest:      Optional[str]   = None
    associated_vessel_id: Optional[str]   = None

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "Cargo":
        base = TrackedObject.from_dict.__func__(cls, raw)
        base.lot_number           = raw.get("lot_number") or raw.get("lot")
        base.commodity_type       = raw.get("commodity_type") or raw.get("commodity")
        base.weight               = raw.get("weight")
        base.origin_manifest      = raw.get("manifest") or raw.get("origin_manifest")
        base.associated_vessel_id = raw.get("vessel_id") or raw.get("associated_vessel_id")
        return base


@dataclass
class Device(TrackedObject):
    device_id:            Optional[str] = None
    device_type:          Optional[str] = None
    associated_person_id: Optional[str] = None
    signal_type:          Optional[str] = None

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "Device":
        base = TrackedObject.from_dict.__func__(cls, raw)
        base.device_id            = raw.get("device_id") or raw.get("beacon_id")
        base.device_type          = raw.get("device_type")
        base.associated_person_id = raw.get("person_id") or raw.get("associated_person_id")
        base.signal_type          = raw.get("signal_type")
        return base


@dataclass
class UnknownObject(TrackedObject):
    """
    Fallback for unclassified data. Raw fields are preserved so the
    object can be promoted to a typed subclass later by an analyst.
    Motion analysis still runs on UnknownObject instances.
    """
    classification_confidence: float = 0.0
    classifier_notes:          str   = ""
    flagged_for_review:        bool  = True

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "UnknownObject":
        base = TrackedObject.from_dict.__func__(cls, raw)
        base.flagged_for_review = True
        return base


# ══════════════════════════════════════════════════════════════════════════════
# BEHAVIOR LAYER — what the thing DOES
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class Location:
    """
    Where something is, at whatever level of precision the data provides.
    All fields except location_id are optional — not every dataset gives
    coordinates, and not every dataset gives admin area labels.
    """
    location_id:          str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    label:                Optional[str]   = None    # city, region name, port, etc.
    country:              Optional[str]   = None
    admin_level:          Optional[str]   = None    # country / state / county / coordinates-only
    centroid_lat:         Optional[float] = None
    centroid_lon:         Optional[float] = None
    boundary_geometry:    Optional[str]   = None    # GeoJSON or WKT
    proximity_to_center:  Optional[float] = None    # km from defined reference point
    reference_frame:      Optional[str]   = None    # what the proximity is measured from
    context_density:      Optional[str]   = None    # populated / sparse / maritime-busy / etc.

    def has_coordinates(self) -> bool:
        return self.centroid_lat is not None and self.centroid_lon is not None

    def __repr__(self):
        if self.has_coordinates():
            return f"<Location {self.label or self.location_id} ({self.centroid_lat:.4f}, {self.centroid_lon:.4f})>"
        return f"<Location {self.label or self.location_id} [no coordinates]>"


@dataclass
class MovementRecord:
    """
    A sequence of observed positions for one tracked object over time.
    The object_id links back to a TrackedObject — this layer does not
    need to know what type of object it is.
    """
    record_id:              str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    object_id:              str = ""
    observed_positions:     List[Dict[str, Any]] = field(default_factory=list)  # list of {lat, lon, timestamp}
    origin_location_id:     Optional[str]   = None
    destination_location_id: Optional[str]  = None
    displacement_km:        Optional[float] = None
    displacement_direction: Optional[str]   = None
    speed:                  Optional[float] = None
    trajectory:             Optional[str]   = None      # path description or encoded polyline
    position_confidence:    Optional[str]   = None      # "exact", "county-level", "city-level"

    @property
    def is_stationary(self) -> bool:
        """Returns True if no meaningful displacement was recorded."""
        return self.displacement_km is not None and self.displacement_km < 0.1

    def __repr__(self):
        return (f"<MovementRecord object={self.object_id} "
                f"positions={len(self.observed_positions)} "
                f"displacement={self.displacement_km}km>")


@dataclass
class TimePeriod:
    """
    A defined window for grouping observations and establishing baselines.
    Unchanged from the original design — time is universal.
    """
    period_id:   str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    start_date:  Optional[date] = None
    end_date:    Optional[date] = None
    label:       Optional[str]  = None      # e.g. "Q1 2026", "Post-Election Window"
    period_type: str = "daily"              # daily / weekly / monthly / custom

    def contains_date(self, d: date) -> bool:
        if self.start_date and self.end_date:
            return self.start_date <= d <= self.end_date
        return False

    def __repr__(self):
        return f"<TimePeriod {self.label or self.period_id} {self.start_date} → {self.end_date}>"


@dataclass
class Anomaly:
    """
    A detected deviation from expected behavior.
    Works for any object type — the anomaly_type enum describes what happened,
    the affected_attributes field says which data fields triggered it.
    """
    anomaly_id:          str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    object_id:           str = ""
    record_id:           Optional[str]        = None
    detected_at:         datetime             = field(default_factory=datetime.now)
    anomaly_type:        AnomalyType          = AnomalyType.UNEXPECTED_DISPLACEMENT
    deviation_score:     float                = 0.0     # z-score or normalized 0–1
    baseline_reference:  Optional[str]        = None    # e.g. "2025-Q4 average"
    affected_attributes: List[str]            = field(default_factory=list)
    auto_detected:       bool                 = True
    analyst_reviewed:    bool                 = False
    notes:               Optional[str]        = None

    def __repr__(self):
        return (f"<Anomaly {self.anomaly_id} | {self.anomaly_type.value} | "
                f"object={self.object_id} | score={self.deviation_score:.2f}>")
