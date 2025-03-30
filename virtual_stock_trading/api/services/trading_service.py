from django.db import transaction
from django.utils import timezone
from ..models import Portfolio, Stock, Position, Transaction
from .stock_service import StockService

class TradingService:
    @classmethod
    def execute_buy(cls, portfolio, stock_symbol, quantity):
        """
        Execute a buy order for the specified stock and quantity.
        
        Args:
            portfolio: Portfolio object
            stock_symbol: Stock symbol to buy
            quantity: Number of shares to buy
            
        Returns:
            Transaction object if successful, None otherwise
        
        Raises:
            ValueError: If the order cannot be executed due to validation errors
        """
        # Validate inputs
        if quantity <= 0:
            raise ValueError("Quantity must be a positive integer")
        
        # Get current stock price
        stock_data = StockService.get_stock_data(stock_symbol)
        if not stock_data:
            raise ValueError(f"Could not fetch current price for {stock_symbol}")
        
        # Get or create stock object
        try:
            stock = Stock.objects.get(symbol=stock_symbol.upper())
        except Stock.DoesNotExist:
            stock = Stock(
                symbol=stock_symbol.upper(),
                company_name=stock_data.company_name,
                last_price=stock_data.last_price,
                last_updated=stock_data.last_updated
            )
            stock.save()
        
        # Calculate total cost
        total_cost = quantity * stock.last_price
        
        # Check if user has enough funds
        if portfolio.cash_balance < total_cost:
            raise ValueError(f"Insufficient funds. You need ${total_cost} to complete this purchase.")
            
        # Execute order with atomic transaction
        with transaction.atomic():
            # Update portfolio cash balance
            portfolio.cash_balance -= total_cost
            portfolio.save()
            
            # Update or create position
            try:
                position = Position.objects.get(portfolio=portfolio, stock=stock)
                # Calculate new average price
                total_shares = position.quantity + quantity
                total_investment = (position.average_buy_price * position.quantity) + total_cost
                new_avg_price = total_investment / total_shares
                
                position.quantity = total_shares
                position.average_buy_price = new_avg_price
                position.save()
            except Position.DoesNotExist:
                position = Position(
                    portfolio=portfolio,
                    stock=stock,
                    quantity=quantity,
                    average_buy_price=stock.last_price
                )
                position.save()
            
            # Create transaction record
            transaction = Transaction(
                portfolio=portfolio,
                stock=stock,
                transaction_type=Transaction.BUY,
                quantity=quantity,
                price=stock.last_price
            )
            transaction.save()
            
            return transaction
    
    @classmethod
    def execute_sell(cls, portfolio, stock_symbol, quantity):
        """
        Execute a sell order for the specified stock and quantity.
        
        Args:
            portfolio: Portfolio object
            stock_symbol: Stock symbol to sell
            quantity: Number of shares to sell
            
        Returns:
            Transaction object if successful, None otherwise
            
        Raises:
            ValueError: If the order cannot be executed due to validation errors
        """
        # Validate inputs
        if quantity <= 0:
            raise ValueError("Quantity must be a positive integer")
        
        # Get current stock price
        stock_data = StockService.get_stock_data(stock_symbol)
        if not stock_data:
            raise ValueError(f"Could not fetch current price for {stock_symbol}")
        
        # Get stock object
        try:
            stock = Stock.objects.get(symbol=stock_symbol.upper())
        except Stock.DoesNotExist:
            raise ValueError(f"You don't own any shares of {stock_symbol}")
        
        # Check if user has the position and enough shares
        try:
            position = Position.objects.get(portfolio=portfolio, stock=stock)
        except Position.DoesNotExist:
            raise ValueError(f"You don't own any shares of {stock_symbol}")
        
        if position.quantity < quantity:
            raise ValueError(f"You only have {position.quantity} shares to sell")
        
        # Calculate sale amount
        sale_amount = quantity * stock.last_price
        
        # Execute order with atomic transaction
        with transaction.atomic():
            # Update portfolio cash balance
            portfolio.cash_balance += sale_amount
            portfolio.save()
            
            # Update position
            position.quantity -= quantity
            if position.quantity == 0:
                position.delete()
            else:
                position.save()
            
            # Create transaction record
            transaction = Transaction(
                portfolio=portfolio,
                stock=stock,
                transaction_type=Transaction.SELL,
                quantity=quantity,
                price=stock.last_price
            )
            transaction.save()
            
            return transaction