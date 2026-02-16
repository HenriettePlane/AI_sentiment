"""Pipeline orchestrator: extract → transform → load → cleanup."""

import logging
import sys
from datetime import date, timedelta

from pipeline.extract import extract
from pipeline.transform import transform
from pipeline.load import load
from pipeline.cleanup import cleanup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def run(start_date: date | None = None, end_date: date | None = None) -> None:
    """Run the full pipeline."""
    logger.info("Pipeline starting")

    raw_df = extract(start_date, end_date)
    clean_df = transform(raw_df)
    loaded = load(clean_df)
    cleanup()

    logger.info("Pipeline complete — %d rows loaded", loaded)


def main() -> None:
    """Entry point with optional CLI backfill args: start_date end_date."""
    start = end = None
    if len(sys.argv) >= 3:
        start = date.fromisoformat(sys.argv[1])
        end = date.fromisoformat(sys.argv[2])
        logger.info("Backfill mode: %s to %s", start, end)
    run(start, end)


if __name__ == "__main__":
    main()
