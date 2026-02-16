"""Delete articles older than the retention window."""

import logging
from datetime import date, timedelta

from supabase import create_client

from config.settings import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, RETENTION_DAYS

logger = logging.getLogger(__name__)


def cleanup() -> None:
    """Delete articles where published_date < today - RETENTION_DAYS."""
    cutoff = date.today() - timedelta(days=RETENTION_DAYS)
    logger.info("Deleting articles older than %s (retention=%d days)", cutoff, RETENTION_DAYS)

    client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    result = (
        client.table("articles")
        .delete()
        .lt("published_date", cutoff.isoformat())
        .execute()
    )

    deleted = len(result.data) if result.data else 0
    logger.info("Deleted %d old articles", deleted)
