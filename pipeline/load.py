"""Load transformed data into Supabase."""

import logging
import math

import pandas as pd
from supabase import create_client

from config.settings import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

logger = logging.getLogger(__name__)

BATCH_SIZE = 500


def _sanitize_record(record: dict) -> dict:
    """Replace NaN/inf with None for JSON serialization."""
    clean = {}
    for k, v in record.items():
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            clean[k] = None
        else:
            clean[k] = v
    return clean


def load(df: pd.DataFrame) -> int:
    """Upsert articles into Supabase in batches.

    Returns:
        Number of rows upserted.
    """
    if df.empty:
        logger.info("No data to load")
        return 0

    client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    records = [_sanitize_record(r) for r in df.to_dict(orient="records")]

    total = 0
    for i in range(0, len(records), BATCH_SIZE):
        batch = records[i : i + BATCH_SIZE]
        client.table("articles").upsert(
            batch, on_conflict="url,published_date"
        ).execute()
        total += len(batch)
        logger.info("Upserted batch %d–%d", i, i + len(batch))

    logger.info("Loaded %d total rows", total)
    return total
