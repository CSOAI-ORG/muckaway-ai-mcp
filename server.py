"""
Muckaway.AI MCP Server - Waste Logistics AI
Built by MEOK AI Labs | https://muckaway.ai

UK waste removal, skip hire, haulage costing, waste classification,
disposal facility lookup, and Waste Transfer Note generation.
Covers Environmental Protection Act 1990 and Duty of Care regulations.
"""

import math
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "muckaway-ai")

# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------
_RATE_LIMITS = {
    "free": {"requests_per_hour": 60},
    "pro": {"requests_per_hour": 10000},
}
_request_log: list[float] = []
_tier = "free"


def _check_rate_limit() -> bool:
    now = time.time()
    _request_log[:] = [t for t in _request_log if now - t < 3600]
    if len(_request_log) >= _RATE_LIMITS[_tier]["requests_per_hour"]:
        return False
    _request_log.append(now)
    return True


# ---------------------------------------------------------------------------
# UK postcode validation
# ---------------------------------------------------------------------------
_UK_POSTCODE_RE = re.compile(
    r"^[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}$", re.IGNORECASE
)


def _validate_postcode(postcode: str) -> bool:
    return bool(_UK_POSTCODE_RE.match(postcode.strip()))


# ---------------------------------------------------------------------------
# Skip size data - real UK industry figures
# ---------------------------------------------------------------------------
_SKIP_SIZES = {
    "4yd": {
        "name": "4 Yard Mini Skip",
        "capacity_cubic_yards": 4,
        "capacity_cubic_metres": 3.06,
        "typical_weight_tonnes": 0.5,
        "max_weight_tonnes": 4.0,
        "dimensions_m": {"length": 1.8, "width": 0.9, "height": 0.9},
        "hire_price_gbp": {"low": 180, "mid": 230, "high": 290},
        "permit_cost_gbp": 65,
        "typical_uses": ["bathroom refit", "small garden clearance", "single room clearout"],
        "equivalent_bin_bags": 30,
    },
    "6yd": {
        "name": "6 Yard Builders Skip",
        "capacity_cubic_yards": 6,
        "capacity_cubic_metres": 4.59,
        "typical_weight_tonnes": 1.0,
        "max_weight_tonnes": 6.0,
        "dimensions_m": {"length": 2.4, "width": 1.2, "height": 1.2},
        "hire_price_gbp": {"low": 220, "mid": 280, "high": 360},
        "permit_cost_gbp": 65,
        "typical_uses": ["kitchen refit", "medium garden clearance", "garage clearout"],
        "equivalent_bin_bags": 50,
    },
    "8yd": {
        "name": "8 Yard Builders Skip",
        "capacity_cubic_yards": 8,
        "capacity_cubic_metres": 6.12,
        "typical_weight_tonnes": 1.5,
        "max_weight_tonnes": 8.0,
        "dimensions_m": {"length": 3.7, "width": 1.7, "height": 1.2},
        "hire_price_gbp": {"low": 280, "mid": 350, "high": 450},
        "permit_cost_gbp": 65,
        "typical_uses": ["house renovation", "large garden clearance", "construction waste"],
        "equivalent_bin_bags": 70,
    },
    "12yd": {
        "name": "12 Yard Maxi Skip",
        "capacity_cubic_yards": 12,
        "capacity_cubic_metres": 9.17,
        "typical_weight_tonnes": 2.5,
        "max_weight_tonnes": 12.0,
        "dimensions_m": {"length": 3.7, "width": 1.7, "height": 1.8},
        "hire_price_gbp": {"low": 350, "mid": 430, "high": 550},
        "permit_cost_gbp": 65,
        "typical_uses": ["large renovation", "commercial clearance", "demolition"],
        "equivalent_bin_bags": 100,
    },
    "16yd": {
        "name": "16 Yard Enclosed Skip",
        "capacity_cubic_yards": 16,
        "capacity_cubic_metres": 12.23,
        "typical_weight_tonnes": 3.0,
        "max_weight_tonnes": 16.0,
        "dimensions_m": {"length": 4.2, "width": 1.8, "height": 2.1},
        "hire_price_gbp": {"low": 380, "mid": 480, "high": 600},
        "permit_cost_gbp": 85,
        "typical_uses": ["light bulky waste", "cardboard", "insulation", "plastics"],
        "equivalent_bin_bags": 130,
    },
    "20yd": {
        "name": "20 Yard Roll-On Roll-Off",
        "capacity_cubic_yards": 20,
        "capacity_cubic_metres": 15.29,
        "typical_weight_tonnes": 4.0,
        "max_weight_tonnes": 10.0,
        "dimensions_m": {"length": 5.5, "width": 2.4, "height": 1.5},
        "hire_price_gbp": {"low": 400, "mid": 520, "high": 680},
        "permit_cost_gbp": 85,
        "typical_uses": ["site clearance", "commercial waste", "industrial projects"],
        "equivalent_bin_bags": 170,
    },
    "40yd": {
        "name": "40 Yard Roll-On Roll-Off",
        "capacity_cubic_yards": 40,
        "capacity_cubic_metres": 30.58,
        "typical_weight_tonnes": 8.0,
        "max_weight_tonnes": 16.0,
        "dimensions_m": {"length": 6.1, "width": 2.4, "height": 2.6},
        "hire_price_gbp": {"low": 500, "mid": 650, "high": 850},
        "permit_cost_gbp": 85,
        "typical_uses": ["major demolition", "large commercial clearance", "industrial waste"],
        "equivalent_bin_bags": 340,
    },
}

# ---------------------------------------------------------------------------
# Waste type classifications - per Environmental Protection Act 1990
# ---------------------------------------------------------------------------
_WASTE_TYPES = {
    "general": {
        "name": "General / Mixed Waste",
        "ewc_chapter": "20 - Municipal wastes",
        "description": "Household and commercial mixed waste not separately collected",
        "examples": ["furniture", "carpets", "textiles", "mixed packaging", "general rubbish"],
        "disposal_method": "Energy from Waste (EfW) or landfill",
        "hazardous": False,
        "requires_special_handling": False,
        "landfill_tax_band": "standard",
        "landfill_tax_per_tonne_gbp": 103.70,
        "recycling_target_pct": 50,
        "regulations": [
            "Environmental Protection Act 1990 s.34 (Duty of Care)",
            "Waste (England and Wales) Regulations 2011",
            "Landfill Tax (standard rate) applies",
        ],
    },
    "heavy_inert": {
        "name": "Heavy / Inert Waste",
        "ewc_chapter": "17 - Construction and demolition wastes",
        "description": "Non-reactive construction materials: soil, rubble, concrete, bricks",
        "examples": ["concrete", "bricks", "tiles", "soil", "stone", "rubble", "ceramics"],
        "disposal_method": "Recycling (crushing/screening) or inert landfill",
        "hazardous": False,
        "requires_special_handling": False,
        "landfill_tax_band": "lower",
        "landfill_tax_per_tonne_gbp": 3.25,
        "recycling_target_pct": 90,
        "regulations": [
            "Environmental Protection Act 1990 s.34",
            "Landfill Tax (lower rate) for qualifying inert waste",
            "CL:AIRE Definition of Waste: Development Industry Code of Practice",
            "Must not be mixed with non-inert waste to qualify for lower rate",
        ],
    },
    "hazardous": {
        "name": "Hazardous Waste",
        "ewc_chapter": "Various (marked with asterisk *)",
        "description": "Waste displaying hazardous properties (HP1-HP15)",
        "examples": [
            "asbestos", "lead paint", "chemicals", "solvents", "contaminated soil",
            "fluorescent tubes", "batteries", "oil/fuel", "pesticides",
        ],
        "disposal_method": "Licensed hazardous waste facility only",
        "hazardous": True,
        "requires_special_handling": True,
        "landfill_tax_band": "standard",
        "landfill_tax_per_tonne_gbp": 103.70,
        "recycling_target_pct": 0,
        "regulations": [
            "Hazardous Waste (England and Wales) Regulations 2005",
            "Consignment note required for EVERY movement",
            "Must use licensed hazardous waste carrier",
            "Pre-acceptance testing required at disposal facility",
            "Cannot be mixed with non-hazardous waste (s.18 prohibition)",
            "Producer must register as hazardous waste producer if >500kg/year",
            "Asbestos: Control of Asbestos Regulations 2012 also applies",
        ],
    },
    "recyclable": {
        "name": "Recyclable Waste",
        "ewc_chapter": "Various recyclable codes",
        "description": "Clean, segregated materials suitable for recycling",
        "examples": [
            "clean timber", "metal/scrap", "plasterboard (segregated)",
            "cardboard", "plastic packaging", "glass", "paper",
        ],
        "disposal_method": "Materials Recovery Facility (MRF) or direct recycling",
        "hazardous": False,
        "requires_special_handling": False,
        "landfill_tax_band": "N/A - should not go to landfill",
        "landfill_tax_per_tonne_gbp": 0,
        "recycling_target_pct": 95,
        "regulations": [
            "Waste (England and Wales) Regulations 2011 - TEEP test applies",
            "Separate collection required where technically, environmentally and economically practicable",
            "Plasterboard must be kept separate from biodegradable waste",
            "WEEE Regulations 2013 for electrical items",
        ],
    },
    "green": {
        "name": "Green / Garden Waste",
        "ewc_chapter": "20 02 - Garden and park wastes",
        "description": "Biodegradable garden and park waste",
        "examples": ["grass cuttings", "hedge trimmings", "branches", "leaves", "weeds", "plants"],
        "disposal_method": "Composting (in-vessel or open windrow) or anaerobic digestion",
        "hazardous": False,
        "requires_special_handling": False,
        "landfill_tax_band": "standard (if landfilled - avoid)",
        "landfill_tax_per_tonne_gbp": 103.70,
        "recycling_target_pct": 100,
        "regulations": [
            "Environmental Protection Act 1990 s.34",
            "Environmental Permitting (England and Wales) Regulations 2016",
            "Landfill Directive: biodegradable waste diversion targets",
            "Japanese knotweed: controlled waste, must go to licensed facility",
            "Giant hogweed: Schedule 9 Wildlife and Countryside Act 1981",
        ],
    },
}

# ---------------------------------------------------------------------------
# Transport vehicle data
# ---------------------------------------------------------------------------
_VEHICLES = {
    "grab_lorry": {
        "name": "Grab Lorry (8-wheeler)",
        "capacity_tonnes": 16,
        "capacity_m3": 10,
        "rate_per_mile_gbp": 4.50,
        "base_charge_gbp": 180,
        "max_range_miles": 50,
        "notes": "Self-loading via hydraulic grab. No skip needed. Ideal for bulk loose waste.",
        "fuel_consumption_mpg": 6,
    },
    "skip_lorry": {
        "name": "Skip Lorry (REL / chain lift)",
        "capacity_tonnes": 8,
        "capacity_m3": 8,
        "rate_per_mile_gbp": 3.20,
        "base_charge_gbp": 120,
        "max_range_miles": 80,
        "notes": "Delivers and collects skips up to 16yd. Standard skip hire vehicle.",
        "fuel_consumption_mpg": 7,
    },
    "tipper": {
        "name": "Tipper Lorry (6/8-wheeler)",
        "capacity_tonnes": 20,
        "capacity_m3": 12,
        "rate_per_mile_gbp": 3.80,
        "base_charge_gbp": 150,
        "max_range_miles": 100,
        "notes": "Hydraulic tipping body. Best for soil, aggregates, demolition waste.",
        "fuel_consumption_mpg": 5,
    },
    "ro_ro_lorry": {
        "name": "Roll-On Roll-Off Lorry",
        "capacity_tonnes": 16,
        "capacity_m3": 40,
        "rate_per_mile_gbp": 5.00,
        "base_charge_gbp": 220,
        "max_range_miles": 60,
        "notes": "Delivers/collects 20yd and 40yd roll-on containers.",
        "fuel_consumption_mpg": 5,
    },
}

# ---------------------------------------------------------------------------
# Licensed disposal facilities (sample data by region)
# ---------------------------------------------------------------------------
_DISPOSAL_FACILITIES = [
    {
        "name": "Beddington ERF",
        "operator": "Viridor",
        "type": "Energy from Waste",
        "accepts": ["general", "recyclable"],
        "region": "South London",
        "postcode_prefix": ["SM", "CR", "SW", "SE"],
        "permit_number": "EPR/VP3036RL",
        "capacity_tonnes_per_year": 302000,
    },
    {
        "name": "Edmonton EcoPark",
        "operator": "North London Waste Authority",
        "type": "Energy from Waste",
        "accepts": ["general"],
        "region": "North London",
        "postcode_prefix": ["N", "EN", "E"],
        "permit_number": "EPR/BV7822IC",
        "capacity_tonnes_per_year": 700000,
    },
    {
        "name": "Colnbrook Landfill",
        "operator": "Grundon",
        "type": "Landfill (non-hazardous)",
        "accepts": ["general", "heavy_inert"],
        "region": "West London / Berkshire",
        "postcode_prefix": ["SL", "UB", "TW"],
        "permit_number": "EPR/DP3532DE",
        "capacity_tonnes_per_year": 250000,
    },
    {
        "name": "Packington Landfill",
        "operator": "SITA UK",
        "type": "Landfill (non-hazardous)",
        "accepts": ["general", "heavy_inert"],
        "region": "West Midlands",
        "postcode_prefix": ["B", "CV", "WS", "WV"],
        "permit_number": "EPR/BP3934DN",
        "capacity_tonnes_per_year": 400000,
    },
    {
        "name": "Pinden Quarry",
        "operator": "Gallagher Group",
        "type": "Inert Landfill / Recycling",
        "accepts": ["heavy_inert"],
        "region": "Kent",
        "postcode_prefix": ["DA", "ME", "TN", "CT"],
        "permit_number": "EPR/FB3107LJ",
        "capacity_tonnes_per_year": 150000,
    },
    {
        "name": "Ling Hall Landfill",
        "operator": "FCC Environment",
        "type": "Hazardous Waste Landfill",
        "accepts": ["hazardous"],
        "region": "Warwickshire",
        "postcode_prefix": ["CV", "B", "LE", "NN"],
        "permit_number": "EPR/LP3433LS",
        "capacity_tonnes_per_year": 50000,
    },
    {
        "name": "Biffa Leicester MRF",
        "operator": "Biffa",
        "type": "Materials Recovery Facility",
        "accepts": ["recyclable"],
        "region": "East Midlands",
        "postcode_prefix": ["LE", "NG", "DE", "NN"],
        "permit_number": "EPR/GP3139XJ",
        "capacity_tonnes_per_year": 120000,
    },
    {
        "name": "TEG Todmorden Composting",
        "operator": "TEG Group",
        "type": "Composting Facility",
        "accepts": ["green"],
        "region": "Yorkshire / Lancashire",
        "postcode_prefix": ["OL", "HX", "BD", "BB", "HD"],
        "permit_number": "EPR/AB1234CD",
        "capacity_tonnes_per_year": 45000,
    },
    {
        "name": "Cory Riverside ERF",
        "operator": "Cory Environmental",
        "type": "Energy from Waste",
        "accepts": ["general"],
        "region": "South East London",
        "postcode_prefix": ["SE", "DA", "BR"],
        "permit_number": "EPR/SP3330ZK",
        "capacity_tonnes_per_year": 785000,
    },
    {
        "name": "Greater Manchester WDA Transfer Station",
        "operator": "Suez",
        "type": "Waste Transfer Station",
        "accepts": ["general", "recyclable", "green"],
        "region": "Greater Manchester",
        "postcode_prefix": ["M", "OL", "SK", "BL", "WN"],
        "permit_number": "EPR/KP3831JN",
        "capacity_tonnes_per_year": 200000,
    },
    {
        "name": "Avonmouth ERF",
        "operator": "Viridor",
        "type": "Energy from Waste",
        "accepts": ["general"],
        "region": "Bristol / South West",
        "postcode_prefix": ["BS", "BA", "GL"],
        "permit_number": "EPR/MP3935TF",
        "capacity_tonnes_per_year": 320000,
    },
    {
        "name": "Severnside Hazardous Waste Facility",
        "operator": "Augean",
        "type": "Hazardous Waste Treatment",
        "accepts": ["hazardous"],
        "region": "South West",
        "postcode_prefix": ["BS", "BA", "GL", "SN"],
        "permit_number": "EPR/NP3234HW",
        "capacity_tonnes_per_year": 30000,
    },
]


# ===========================================================================
# MCP Tools
# ===========================================================================


@mcp.tool()
def estimate_waste_volume(
    length_m: float,
    width_m: float,
    depth_m: float,
    waste_type: str = "general",
    compaction_factor: float = 1.0) -> dict:
    """Estimate waste volume from dimensions and recommend skip size.

    Calculates cubic metres from length x width x depth, applies a compaction
    factor, and recommends the most cost-effective skip size. Includes estimated
    weight based on waste type density.

    Args:
        length_m: Length in metres.
        width_m: Width in metres.
        depth_m: Depth/height in metres.
        waste_type: Type of waste (general, heavy_inert, hazardous, recyclable, green).
            Affects weight estimate.
        compaction_factor: Multiplier for loose/bulky waste (1.0 = as measured,
            1.3 = loose rubble, 0.7 = compacted). Default 1.0.

    Returns:
        Volume in cubic metres, estimated weight, recommended skip size, and pricing.
    """
    if not _check_rate_limit():
        return {"error": "Rate limit exceeded. Upgrade at https://muckaway.ai/pricing"}

    if any(d <= 0 for d in [length_m, width_m, depth_m]):
        return {"error": "All dimensions must be positive numbers."}

    raw_volume = length_m * width_m * depth_m
    adjusted_volume = raw_volume * compaction_factor

    # Density estimates (tonnes per cubic metre) by waste type
    densities = {
        "general": 0.15,
        "heavy_inert": 1.5,
        "hazardous": 0.8,
        "recyclable": 0.10,
        "green": 0.25,
    }
    density = densities.get(waste_type, 0.15)
    estimated_weight = adjusted_volume * density

    # Find best-fit skip
    recommended = None
    alternatives = []
    for size_id, skip in sorted(_SKIP_SIZES.items(), key=lambda x: x[1]["capacity_cubic_metres"]):
        if skip["capacity_cubic_metres"] >= adjusted_volume and estimated_weight <= skip["max_weight_tonnes"]:
            if recommended is None:
                recommended = {"size": size_id, **skip}
            else:
                alternatives.append({"size": size_id, "name": skip["name"], "capacity_m3": skip["capacity_cubic_metres"]})
                if len(alternatives) >= 2:
                    break

    # If no single skip fits, calculate multiple skips needed
    multiple_skips = None
    if recommended is None:
        largest = _SKIP_SIZES["40yd"]
        skips_needed = math.ceil(adjusted_volume / largest["capacity_cubic_metres"])
        multiple_skips = {
            "skip_size": "40yd",
            "quantity": skips_needed,
            "total_capacity_m3": skips_needed * largest["capacity_cubic_metres"],
            "estimated_cost_gbp": {
                "low": skips_needed * largest["hire_price_gbp"]["low"],
                "high": skips_needed * largest["hire_price_gbp"]["high"],
            },
        }

    return {
        "input_dimensions_m": {"length": length_m, "width": width_m, "depth": depth_m},
        "raw_volume_m3": round(raw_volume, 2),
        "compaction_factor": compaction_factor,
        "adjusted_volume_m3": round(adjusted_volume, 2),
        "waste_type": waste_type,
        "density_tonnes_per_m3": density,
        "estimated_weight_tonnes": round(estimated_weight, 2),
        "recommended_skip": recommended,
        "alternatives": alternatives if alternatives else None,
        "multiple_skips_needed": multiple_skips,
        "notes": [
            "Weight estimate is approximate - actual density varies by material",
            "Heavy/inert waste (soil, rubble) is much denser than general waste",
            "Overloading a skip is illegal - do not fill above the rim",
            "Mixed waste costs more to dispose of than segregated waste",
        ],
        "powered_by": "muckaway.ai",
    }


@mcp.tool()
def get_skip_pricing(
    skip_size: str,
    on_road: bool = False,
    hire_days: int = 14,
    region: str = "london") -> dict:
    """Return skip hire pricing by size with permit costs.

    Covers all standard UK skip sizes from 4yd mini to 40yd roll-on.
    Includes council permit costs for road/pavement placement and
    regional price variations.

    Args:
        skip_size: Skip size code (4yd, 6yd, 8yd, 12yd, 16yd, 20yd, 40yd).
        on_road: Whether the skip will be placed on a public road/pavement
            (requires council permit). Default False (placed on private land).
        hire_days: Number of hire days. Standard is 14. Extended hire
            incurs daily surcharge.
        region: Pricing region (london, south_east, midlands, north, scotland, wales).

    Returns:
        Detailed pricing breakdown including hire, permit, and VAT.
    """
    if not _check_rate_limit():
        return {"error": "Rate limit exceeded."}

    skip = _SKIP_SIZES.get(skip_size)
    if not skip:
        return {
            "error": f"Unknown skip size '{skip_size}'.",
            "available_sizes": list(_SKIP_SIZES.keys()),
        }

    # Regional price multipliers
    region_multipliers = {
        "london": 1.25,
        "south_east": 1.10,
        "midlands": 1.00,
        "north": 0.90,
        "scotland": 0.95,
        "wales": 0.92,
    }
    multiplier = region_multipliers.get(region.lower(), 1.0)

    base_price = round(skip["hire_price_gbp"]["mid"] * multiplier, 2)

    # Extended hire surcharge (over 14 days)
    overage_days = max(0, hire_days - 14)
    daily_surcharge = round(base_price * 0.03, 2)  # ~3% per extra day
    overage_charge = round(overage_days * daily_surcharge, 2)

    # Permit cost for road placement
    permit_cost = skip["permit_cost_gbp"] if on_road else 0

    subtotal = base_price + overage_charge + permit_cost
    vat = round(subtotal * 0.20, 2)

    return {
        "skip": {
            "size": skip_size,
            "name": skip["name"],
            "capacity_m3": skip["capacity_cubic_metres"],
            "max_weight_tonnes": skip["max_weight_tonnes"],
            "dimensions_m": skip["dimensions_m"],
            "equivalent_bin_bags": skip["equivalent_bin_bags"],
        },
        "pricing": {
            "base_hire": base_price,
            "hire_days_included": 14,
            "extra_days": overage_days,
            "daily_surcharge": daily_surcharge if overage_days > 0 else 0,
            "overage_charge": overage_charge,
            "permit_cost": permit_cost,
            "permit_required": on_road,
            "subtotal": round(subtotal, 2),
            "vat_20pct": vat,
            "total_inc_vat": round(subtotal + vat, 2),
            "currency": "GBP",
        },
        "region": region,
        "price_range_gbp": {
            "low": round(skip["hire_price_gbp"]["low"] * multiplier, 2),
            "high": round(skip["hire_price_gbp"]["high"] * multiplier, 2),
        },
        "permit_info": {
            "required": on_road,
            "cost": permit_cost,
            "processing_days": "3-5 working days",
            "notes": [
                "Permit required for ANY placement on public highway, footpath, or verge",
                "Council may refuse permit near junctions, bus stops, or restricted areas",
                "Skip must have lights, reflectors, and markings when on road (Builders' Skips (Markings) Regulations 1984)",
                "Permit holder is responsible for any damage to highway",
            ] if on_road else ["No permit needed for private land placement"],
        },
        "typical_uses": skip["typical_uses"],
        "powered_by": "muckaway.ai",
    }


@mcp.tool()
def check_waste_type(
    description: str,
    materials: Optional[list[str]] = None) -> dict:
    """Classify waste type and return disposal requirements.

    Classifies waste as general, heavy/inert, hazardous, recyclable, or green
    waste based on description and materials. Returns applicable UK regulations,
    disposal methods, and landfill tax implications.

    Args:
        description: Description of the waste (e.g. "rubble from demolished wall",
            "old bathroom suite", "garden hedge trimmings").
        materials: Optional list of specific materials present (e.g.
            ["concrete", "bricks", "timber", "plasterboard"]).

    Returns:
        Waste classification, disposal requirements, regulations, and costs.
    """
    if not _check_rate_limit():
        return {"error": "Rate limit exceeded."}

    desc_lower = description.lower()
    materials_lower = [m.lower() for m in (materials or [])]
    all_text = desc_lower + " " + " ".join(materials_lower)

    # Hazardous detection keywords
    hazardous_keywords = [
        "asbestos", "lead paint", "chemical", "solvent", "oil", "fuel",
        "pesticide", "battery", "fluorescent", "mercury", "acid", "alkali",
        "paint stripper", "creosote", "tar", "bitumen", "contaminated",
    ]
    is_hazardous = any(kw in all_text for kw in hazardous_keywords)

    # Inert/heavy detection
    inert_keywords = [
        "concrete", "brick", "rubble", "soil", "earth", "stone", "gravel",
        "clay", "sand", "ceramic", "tile", "slate", "rock", "aggregate",
    ]
    is_inert = any(kw in all_text for kw in inert_keywords)

    # Green waste detection
    green_keywords = [
        "grass", "hedge", "branch", "leaf", "leaves", "garden", "tree",
        "shrub", "weed", "plant", "turf", "compost", "bark", "stump",
    ]
    is_green = any(kw in all_text for kw in green_keywords)

    # Recyclable detection
    recyclable_keywords = [
        "metal", "scrap", "cardboard", "plastic", "glass", "paper",
        "timber", "wood", "plasterboard", "aluminium", "steel", "copper",
    ]
    is_recyclable = any(kw in all_text for kw in recyclable_keywords)

    # Priority: hazardous > inert > green > recyclable > general
    if is_hazardous:
        classification = "hazardous"
    elif is_inert and not is_recyclable:
        classification = "heavy_inert"
    elif is_green and not is_inert:
        classification = "green"
    elif is_recyclable:
        classification = "recyclable"
    else:
        classification = "general"

    waste_info = _WASTE_TYPES[classification]

    # Check for mixed waste warnings
    warnings = []
    if is_hazardous and (is_inert or is_recyclable or is_green):
        warnings.append(
            "CRITICAL: Hazardous materials detected alongside non-hazardous waste. "
            "Hazardous waste MUST be segregated. Mixing is a criminal offence under "
            "Hazardous Waste Regulations 2005 s.18."
        )
    if is_inert and is_recyclable:
        warnings.append(
            "Mixed inert and recyclable waste detected. Segregating these will "
            "significantly reduce disposal costs (inert waste qualifies for lower "
            "landfill tax rate of GBP 3.25/tonne vs GBP 103.70/tonne)."
        )
    if "plasterboard" in all_text:
        warnings.append(
            "Plasterboard MUST be separated from biodegradable waste at landfill "
            "(produces hydrogen sulphide gas). Segregated plasterboard can be recycled."
        )

    return {
        "description": description,
        "materials_identified": materials,
        "classification": classification,
        "waste_info": waste_info,
        "warnings": warnings if warnings else None,
        "duty_of_care": {
            "regulation": "Environmental Protection Act 1990, Section 34",
            "obligations": [
                "Store waste safely and securely",
                "Only hand waste to an authorised person (licensed carrier)",
                "Provide an accurate description of the waste",
                "Complete a Waste Transfer Note for every transfer",
                "Retain Waste Transfer Notes for minimum 2 years (3 years for hazardous)",
                "Take reasonable steps to prevent illegal disposal",
            ],
        },
        "powered_by": "muckaway.ai",
    }


@mcp.tool()
def calculate_transport(
    distance_miles: float,
    vehicle_type: str,
    waste_weight_tonnes: float,
    return_trip: bool = True,
    congestion_zone: bool = False,
    ulez: bool = False) -> dict:
    """Calculate haulage cost for waste transport.

    Pricing based on vehicle type, distance, waste weight, and London
    charges (congestion/ULEZ). Covers grab lorries, skip lorries, tippers,
    and roll-on roll-off vehicles.

    Args:
        distance_miles: One-way distance in miles.
        vehicle_type: Vehicle type (grab_lorry, skip_lorry, tipper, ro_ro_lorry).
        waste_weight_tonnes: Estimated weight of waste in tonnes.
        return_trip: Whether this is a return trip (default True).
        congestion_zone: Whether route enters London Congestion Charge zone.
        ulez: Whether route enters London ULEZ zone.

    Returns:
        Detailed haulage cost breakdown.
    """
    if not _check_rate_limit():
        return {"error": "Rate limit exceeded."}

    vehicle = _VEHICLES.get(vehicle_type)
    if not vehicle:
        return {
            "error": f"Unknown vehicle type '{vehicle_type}'.",
            "available_types": list(_VEHICLES.keys()),
        }

    if distance_miles <= 0:
        return {"error": "Distance must be positive."}

    if distance_miles > vehicle["max_range_miles"]:
        return {
            "error": f"Distance {distance_miles} miles exceeds max range for {vehicle['name']} ({vehicle['max_range_miles']} miles).",
            "suggestion": "Consider a transfer station closer to site, or use a different vehicle.",
        }

    if waste_weight_tonnes > vehicle["capacity_tonnes"]:
        return {
            "error": f"Weight {waste_weight_tonnes}t exceeds {vehicle['name']} capacity ({vehicle['capacity_tonnes']}t).",
            "suggestion": "Multiple trips required or use a larger vehicle.",
            "trips_needed": math.ceil(waste_weight_tonnes / vehicle["capacity_tonnes"]),
        }

    # Base calculation
    trips = 2 if return_trip else 1
    mileage_cost = distance_miles * vehicle["rate_per_mile_gbp"] * trips
    base = vehicle["base_charge_gbp"]
    subtotal = base + mileage_cost

    # London charges
    congestion_charge = 15.00 if congestion_zone else 0
    ulez_charge = 12.50 if ulez else 0  # Older non-compliant vehicles; most modern trucks are compliant

    # Fuel estimate
    fuel_litres = (distance_miles * trips) / vehicle["fuel_consumption_mpg"] * 4.546  # miles to litres
    fuel_cost = round(fuel_litres * 1.45, 2)  # GBP per litre diesel

    total = subtotal + congestion_charge + ulez_charge

    return {
        "vehicle": vehicle["name"],
        "vehicle_type": vehicle_type,
        "capacity_tonnes": vehicle["capacity_tonnes"],
        "waste_weight_tonnes": waste_weight_tonnes,
        "distance_miles": distance_miles,
        "return_trip": return_trip,
        "pricing": {
            "base_charge": base,
            "mileage_cost": round(mileage_cost, 2),
            "congestion_charge": congestion_charge,
            "ulez_charge": ulez_charge,
            "subtotal": round(total, 2),
            "vat_20pct": round(total * 0.20, 2),
            "total_inc_vat": round(total * 1.20, 2),
            "currency": "GBP",
        },
        "fuel_estimate": {
            "litres": round(fuel_litres, 1),
            "cost_gbp": fuel_cost,
        },
        "notes": [
            vehicle["notes"],
            "Prices exclude disposal/gate fees at tip",
            "Waiting time charged at GBP 45/hour after first 30 minutes",
            "Weekend/bank holiday surcharge: +50%",
        ],
        "powered_by": "muckaway.ai",
    }


@mcp.tool()
def find_nearest_tip(
    postcode: str,
    waste_type: str) -> dict:
    """Find nearest licensed waste disposal facilities by waste type and postcode.

    Searches UK licensed facilities that accept the specified waste type,
    matched by postcode area. Returns Environment Agency permit details.

    Args:
        postcode: UK postcode (e.g. "SE1 7PB", "M1 1AA", "BS1 4DJ").
        waste_type: Waste classification (general, heavy_inert, hazardous, recyclable, green).

    Returns:
        List of matching facilities with permit details and accepted waste types.
    """
    if not _check_rate_limit():
        return {"error": "Rate limit exceeded."}

    if not _validate_postcode(postcode):
        return {"error": f"Invalid UK postcode format: '{postcode}'. Expected format: 'SW1A 1AA'."}

    if waste_type not in _WASTE_TYPES:
        return {
            "error": f"Unknown waste type '{waste_type}'.",
            "available_types": list(_WASTE_TYPES.keys()),
        }

    # Extract postcode prefix (area letters)
    prefix = re.match(r"^([A-Z]{1,2})", postcode.strip().upper())
    if not prefix:
        return {"error": "Could not parse postcode area."}
    area = prefix.group(1)

    # Find matching facilities
    matches = []
    for facility in _DISPOSAL_FACILITIES:
        if waste_type in facility["accepts"]:
            # Check if any prefix matches
            if any(area.startswith(p) or p.startswith(area) for p in facility["postcode_prefix"]):
                matches.append(facility)

    # Also include facilities with broader coverage as fallback
    if not matches:
        for facility in _DISPOSAL_FACILITIES:
            if waste_type in facility["accepts"]:
                matches.append(facility)

    return {
        "postcode": postcode.strip().upper(),
        "postcode_area": area,
        "waste_type": waste_type,
        "waste_info": _WASTE_TYPES[waste_type]["name"],
        "facilities": matches[:5],
        "total_found": len(matches),
        "verification_note": (
            "Always verify facility acceptance criteria directly before transport. "
            "Pre-booking may be required. Check Environment Agency public register "
            "at https://environment.data.gov.uk/public-register/view/search-waste-operations "
            "for current permit status."
        ),
        "powered_by": "muckaway.ai",
    }


@mcp.tool()
def generate_waste_transfer_note(
    producer_name: str,
    producer_address: str,
    carrier_name: str,
    carrier_licence_number: str,
    waste_description: str,
    waste_type: str,
    ewc_code: str = "",
    quantity_tonnes: float = 0,
    quantity_m3: float = 0,
    destination_name: str = "",
    destination_permit_number: str = "",
    sic_code: str = "",
    transfer_date: str = "") -> dict:
    """Generate a Waste Transfer Note with all legally mandatory fields.

    A Waste Transfer Note is required by law for EVERY transfer of
    controlled waste in England and Wales (Environmental Protection Act
    1990, Section 34; Environmental Protection (Duty of Care) Regulations
    1991). Must be retained for minimum 2 years.

    Args:
        producer_name: Name of waste producer (person/business generating the waste).
        producer_address: Address where waste was produced.
        carrier_name: Name of registered waste carrier.
        carrier_licence_number: Carrier's waste carrier licence number (CBDU/CBDL prefix).
        waste_description: Written description of the waste.
        waste_type: Classification (general, heavy_inert, hazardous, recyclable, green).
        ewc_code: European Waste Catalogue code (6 digits, e.g. "170101" for concrete).
            Leave blank for auto-suggestion.
        quantity_tonnes: Quantity in tonnes (provide either tonnes or m3).
        quantity_m3: Quantity in cubic metres.
        destination_name: Name of receiving facility.
        destination_permit_number: Receiving facility's Environment Agency permit number.
        sic_code: Standard Industrial Classification code of waste producer.
        transfer_date: Date of transfer (YYYY-MM-DD). Defaults to today.

    Returns:
        Complete Waste Transfer Note with all mandatory fields and reference number.
    """
    if not _check_rate_limit():
        return {"error": "Rate limit exceeded."}

    if not producer_name or not carrier_name:
        return {"error": "Producer name and carrier name are mandatory fields."}

    if not carrier_licence_number:
        return {
            "error": "Carrier waste licence number is mandatory. "
            "Check carrier registration at https://environment.data.gov.uk/public-register/view/search-waste-carriers-brokers"
        }

    # Auto-suggest EWC codes
    ewc_suggestions = {
        "general": "20 03 01 - Mixed municipal waste",
        "heavy_inert": "17 01 07 - Mixtures of concrete, bricks, tiles (non-hazardous)",
        "hazardous": "Varies - consult List of Wastes (England) Regulations 2005",
        "recyclable": "Varies by material (e.g. 17 02 01 wood, 17 04 05 iron/steel)",
        "green": "20 02 01 - Biodegradable garden and park waste",
    }

    if not ewc_code:
        ewc_code = ewc_suggestions.get(waste_type, "Consult EWC list")

    if not transfer_date:
        transfer_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    note_ref = f"WTN-{uuid.uuid4().hex[:10].upper()}"

    waste_info = _WASTE_TYPES.get(waste_type, _WASTE_TYPES["general"])

    # For hazardous waste, a consignment note is needed instead
    if waste_type == "hazardous":
        return {
            "warning": "HAZARDOUS WASTE requires a CONSIGNMENT NOTE, not a standard Waste Transfer Note.",
            "regulation": "Hazardous Waste (England and Wales) Regulations 2005",
            "requirements": [
                "Use Hazardous Waste Consignment Note (not standard WTN)",
                "Pre-notify the Environment Agency before first movement",
                "Producer must register premises if producing >500kg/year",
                "Consignment notes must be retained for 3 years (not 2)",
                "Use hazardous waste codes from List of Wastes Regulations 2005",
            ],
            "ea_contact": "Environment Agency: 03708 506 506",
            "powered_by": "muckaway.ai",
        }

    return {
        "waste_transfer_note": {
            "reference_number": note_ref,
            "date_of_transfer": transfer_date,
            "section_a_description_of_waste": {
                "written_description": waste_description,
                "ewc_code": ewc_code,
                "waste_classification": waste_info["name"],
                "quantity": {
                    "tonnes": quantity_tonnes if quantity_tonnes else "Not specified",
                    "cubic_metres": quantity_m3 if quantity_m3 else "Not specified",
                },
                "how_waste_is_contained": "Skip / Loose in vehicle / Bagged",
                "sic_code": sic_code if sic_code else "Not specified",
            },
            "section_b_transferor": {
                "name": producer_name,
                "address": producer_address,
                "capacity": "Waste Producer",
                "duty_of_care_declaration": (
                    "I confirm that I have fulfilled my duty of care under "
                    "Section 34 of the Environmental Protection Act 1990."
                ),
            },
            "section_c_transferee": {
                "carrier_name": carrier_name,
                "carrier_licence_number": carrier_licence_number,
                "licence_type": "Upper Tier" if carrier_licence_number.startswith("CBDU") else "Lower Tier",
            },
            "section_d_destination": {
                "facility_name": destination_name if destination_name else "To be confirmed",
                "permit_number": destination_permit_number if destination_permit_number else "To be confirmed",
            },
        },
        "legal_requirements": {
            "legislation": [
                "Environmental Protection Act 1990, Section 34",
                "Environmental Protection (Duty of Care) Regulations 1991 (as amended 2003)",
                "Waste (England and Wales) Regulations 2011",
            ],
            "retention_period": "Minimum 2 years from date of transfer",
            "copies_required": "Both transferor and transferee must retain signed copies",
            "penalties": "Failure to complete a WTN: unlimited fine on conviction",
        },
        "powered_by": "muckaway.ai",
    }


if __name__ == "__main__":
    mcp.run()
