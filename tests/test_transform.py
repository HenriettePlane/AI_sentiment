"""Tests for pipeline.transform module."""

import pandas as pd
import pytest

from pipeline.transform import (
    parse_tone,
    parse_locations,
    select_most_specific,
    select_most_mentioned,
    parse_date,
    parse_themes,
    transform,
)


# --- parse_tone ---

def test_parse_tone_normal():
    assert parse_tone("-3.45,2.1,1.0,5.2,20.0,10.0,100") == pytest.approx(-3.45)


def test_parse_tone_positive():
    assert parse_tone("5.67,1.0,2.0,3.0,4.0,5.0,50") == pytest.approx(5.67)


def test_parse_tone_none():
    assert parse_tone(None) is None


def test_parse_tone_empty():
    assert parse_tone("") is None


# --- parse_locations ---

SINGLE_LOCATION = "4#Tokyo, Tokyo, Japan#JA#JA40#35.6895#139.6917#-1234567"
MULTI_LOCATIONS = (
    "1#Japan#JA##35.6895#139.6917#JA;"
    "4#Tokyo, Tokyo, Japan#JA#JA40#35.6895#139.6917#-123;"
    "1#Japan#JA##35.6895#139.6917#JA;"
    "5#Shibuya, Tokyo, Japan#JA#JA40#35.662#139.7038#-456"
)


def test_parse_locations_single():
    locs = parse_locations(SINGLE_LOCATION)
    assert len(locs) == 1
    assert locs[0]["type"] == 4
    assert locs[0]["country_code"] == "JA"
    assert locs[0]["name"] == "Tokyo, Tokyo, Japan"


def test_parse_locations_multi():
    locs = parse_locations(MULTI_LOCATIONS)
    assert len(locs) == 4
    assert locs[3]["type"] == 5


def test_parse_locations_empty():
    assert parse_locations(None) == []
    assert parse_locations("") == []


def test_parse_locations_malformed():
    assert parse_locations("garbage#data") == []


# --- select_most_specific ---

def test_select_most_specific():
    locs = parse_locations(MULTI_LOCATIONS)
    best = select_most_specific(locs)
    assert best["type"] == 5
    assert best["name"] == "Shibuya, Tokyo, Japan"


def test_select_most_specific_empty():
    assert select_most_specific([]) is None


# --- select_most_mentioned ---

def test_select_most_mentioned():
    locs = parse_locations(MULTI_LOCATIONS)
    most = select_most_mentioned(locs)
    # Japan (type 1) appears twice
    assert most["country_code"] == "JA"
    assert most["name"] == "Japan"


def test_select_most_mentioned_single():
    locs = parse_locations(SINGLE_LOCATION)
    most = select_most_mentioned(locs)
    assert most["name"] == "Tokyo, Tokyo, Japan"


# --- parse_date ---

def test_parse_date_normal():
    assert parse_date(20250615123456) == "2025-06-15"


def test_parse_date_string():
    assert parse_date("20250101000000") == "2025-01-01"


def test_parse_date_none():
    assert parse_date(None) is None


def test_parse_date_short():
    assert parse_date(12345) is None


# --- parse_themes ---

def test_parse_themes():
    raw = "TAX_FNCACT_ARTIFICIAL_INTELLIGENCE,100;ECON_COST,200;TAX_FNCACT_ARTIFICIAL_INTELLIGENCE,300"
    result = parse_themes(raw)
    assert "TAX_FNCACT_ARTIFICIAL_INTELLIGENCE" in result
    assert "ECON_COST" in result
    # Deduplication: AI theme should appear only once
    assert result.count("TAX_FNCACT_ARTIFICIAL_INTELLIGENCE") == 1


def test_parse_themes_empty():
    assert parse_themes(None) == []
    assert parse_themes("") == []


# --- transform (integration) ---

def test_transform_basic():
    raw = pd.DataFrame([{
        "url": "https://example.com/article1",
        "extras": "<PAGE_TITLE>AI Boom</PAGE_TITLE>",
        "raw_locations": "1#United States#US##39.8282#-98.5795#US",
        "raw_tone": "-2.5,1.0,2.0,3.0,4.0,5.0,50",
        "raw_date": 20250615120000,
        "raw_themes": "TAX_FNCACT_ARTIFICIAL_INTELLIGENCE,100",
    }])
    result = transform(raw)
    assert len(result) == 1
    assert result.iloc[0]["title"] == "AI Boom"
    assert result.iloc[0]["avg_tone"] == pytest.approx(-2.5)
    assert result.iloc[0]["mentioned_country_code"] == "US"


def test_transform_drops_missing_country():
    raw = pd.DataFrame([{
        "url": "https://example.com/no-location",
        "extras": None,
        "raw_locations": "",
        "raw_tone": "1.0,1.0,1.0,1.0,1.0,1.0,50",
        "raw_date": 20250615120000,
        "raw_themes": "TAX_FNCACT_ARTIFICIAL_INTELLIGENCE,100",
    }])
    result = transform(raw)
    assert len(result) == 0


def test_transform_deduplicates():
    row = {
        "url": "https://example.com/dup",
        "extras": None,
        "raw_locations": "1#Germany#GM##51.1657#10.4515#GM",
        "raw_tone": "3.0,1.0,1.0,1.0,1.0,1.0,50",
        "raw_date": 20250615120000,
        "raw_themes": "TAX_FNCACT_ARTIFICIAL_INTELLIGENCE,100",
    }
    raw = pd.DataFrame([row, row])
    result = transform(raw)
    assert len(result) == 1


def test_transform_empty():
    result = transform(pd.DataFrame())
    assert result.empty
