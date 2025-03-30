import logging
from datetime import date
from ..models import Portfolio, PortfolioSnapshot

logger = logging.getLogger(__name__)

class PortfolioService:
    @classmethod
    def create_daily_snapshots(cls):
        """
        Create daily snapshots of all portfolios.
        This can be scheduled to run once per day.
        """
        today = date.today()
        portfolios = Portfolio.objects.all()
        snapshot_count = 0
        
        for portfolio in portfolios:
            # Skip if a snapshot already exists for today
            if portfolio.snapshots.filter(date=today).exists():
                continue
            
            try:
                # Create a new snapshot
                total_value = portfolio.total_value()
                PortfolioSnapshot.objects.create(
                    portfolio=portfolio,
                    date=today,
                    total_value=total_value
                )
                snapshot_count += 1
            except Exception as e:
                logger.error(f"Error creating snapshot for portfolio {portfolio.id}: {str(e)}")
        
        return snapshot_count