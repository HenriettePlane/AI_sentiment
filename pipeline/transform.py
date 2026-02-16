"""Transform raw GDELT GKG data into clean article records."""

import logging
from collections import Counter

import pandas as pd

logger = logging.getLogger(__name__)


def parse_tone(raw_tone: str | None) -> float | None:
    """Extract avg_tone (first CSV value) from V2Tone string."""
    if not raw_tone:
        return None
    try:
        return float(raw_tone.split(",")[0])
    except (ValueError, IndexError):
        return None


def parse_locations(raw_locations: str | None) -> list[dict]:
    """Parse V2Locations semicolon-separated string into list of location dicts.

    Each entry format: type#name#country_code#adm1_code#lat#lon#feature_id
    """
    if not raw_locations:
        return []

    locations = []
    for entry in raw_locations.split(";"):
        parts = entry.split("#")
        if len(parts) < 6:
            continue
        try:
            loc = {
                "type": int(parts[0]),
                "name": parts[1],
                "country_code": parts[2] if parts[2] else None,
                "adm1_code": parts[3] if parts[3] else None,
                "lat": float(parts[4]) if parts[4] else None,
                "lon": float(parts[5]) if parts[5] else None,
            }
            locations.append(loc)
        except (ValueError, IndexError):
            continue
    return locations


def select_most_specific(locations: list[dict]) -> dict | None:
    """Pick location with highest type value (most granular)."""
    if not locations:
        return None
    return max(locations, key=lambda loc: loc["type"])


def select_most_mentioned(locations: list[dict]) -> dict | None:
    """Pick the most frequently appearing location by (country_code, name)."""
    if not locations:
        return None
    counts = Counter((loc["country_code"], loc["name"]) for loc in locations)
    most_common_key = counts.most_common(1)[0][0]
    for loc in locations:
        if (loc["country_code"], loc["name"]) == most_common_key:
            return loc
    return None


def parse_date(raw_date) -> str | None:
    """Convert YYYYMMDDHHMMSS integer/string to YYYY-MM-DD."""
    if raw_date is None:
        return None
    s = str(int(raw_date))
    if len(s) < 8:
        return None
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}"


def parse_themes(raw_themes: str | None) -> list[str]:
    """Split V2Themes on semicolons and strip offset suffixes."""
    if not raw_themes:
        return []
    themes = []
    for t in raw_themes.split(";"):
        t = t.strip()
        if t:
            # Strip trailing offset like ",123"
            name = t.split(",")[0]
            if name:
                themes.append(name)
    return list(dict.fromkeys(themes))  # deduplicate, preserve order


def _extract_title(extras: str | None, url: str | None) -> str | None:
    """Try to extract title from GKG Extras field; fall back to URL."""
    if extras and isinstance(extras, str):
        # Extras often contains: <PAGE_TITLE>title here</PAGE_TITLE>
        start = extras.find("<PAGE_TITLE>")
        if start != -1:
            start += len("<PAGE_TITLE>")
            end = extras.find("</PAGE_TITLE>", start)
            if end != -1:
                title = extras[start:end].strip()
                if title:
                    return title
    return url


def _location_columns(loc: dict | None, prefix: str) -> dict:
    """Flatten a location dict into prefixed columns."""
    if loc is None:
        return {
            f"{prefix}_location_type": None,
            f"{prefix}_location_name": None,
            f"{prefix}_country_code": None,
            f"{prefix}_adm1_code": None,
            f"{prefix}_latitude": None,
            f"{prefix}_longitude": None,
        }
    return {
        f"{prefix}_location_type": loc["type"],
        f"{prefix}_location_name": loc["name"],
        f"{prefix}_country_code": loc["country_code"],
        f"{prefix}_adm1_code": loc["adm1_code"],
        f"{prefix}_latitude": loc["lat"],
        f"{prefix}_longitude": loc["lon"],
    }


def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Transform raw GDELT extraction into clean article records."""
    if df.empty:
        return pd.DataFrame()

    records = []
    for _, row in df.iterrows():
        avg_tone = parse_tone(row.get("raw_tone"))
        published_date = parse_date(row.get("raw_date"))
        if avg_tone is None or published_date is None:
            continue

        locations = parse_locations(row.get("raw_locations"))
        specific = select_most_specific(locations)
        mentioned = select_most_mentioned(locations)

        # Skip rows with no country code at all
        spec_cc = specific["country_code"] if specific else None
        ment_cc = mentioned["country_code"] if mentioned else None
        if not spec_cc and not ment_cc:
            continue

        source_name = row.get("url", "")
        if source_name and isinstance(source_name, str):
            # Extract domain from URL
            try:
                from urllib.parse import urlparse
                source_name = urlparse(source_name).netloc or source_name
            except Exception:
                pass

        record = {
            "url": row.get("url"),
            "title": _extract_title(row.get("extras"), row.get("url")),
            "source_name": source_name,
            "avg_tone": avg_tone,
            "published_date": published_date,
            "themes": parse_themes(row.get("raw_themes")),
            **_location_columns(specific, "specific"),
            **_location_columns(mentioned, "mentioned"),
        }
        records.append(record)

    if not records:
        return pd.DataFrame()

    result = pd.DataFrame(records)
    result.drop_duplicates(subset=["url", "published_date"], keep="first", inplace=True)
    logger.info("Transformed %d records", len(result))
    return result
