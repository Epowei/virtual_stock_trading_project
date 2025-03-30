from celery import shared_task
from .services.portfolio_service import PortfolioService
import logging

logger = logging.getLogger(__name__)

@shared_task
def create_daily_portfolio_snapshots():
    """
    Celery task to create daily snapshots of all portfolios.
    """
    try:
        snapshot_count = PortfolioService.create_daily_snapshots()
        logger.info(f"Created {snapshot_count} portfolio snapshots")
        return snapshot_count
    except Exception as e:
        logger.error(f"Error creating portfolio snapshots: {str(e)}")
        raise