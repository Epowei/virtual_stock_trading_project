from django.db import models
from django.contrib.auth.models import User


class Stock(models.Model):
    symbol = models.CharField(max_length=10, unique=True)
    company_name = models.CharField(max_length=255)
    last_price = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    last_updated = models.DateTimeField(null=True)

    def __str__(self):
        return f"{self.symbol} - {self.company_name}"


class Portfolio(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='portfolios')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    cash_balance = models.DecimalField(max_digits=15, decimal_places=2, default=10000.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.user.username}"
    
    def total_stock_value(self):
        """Calculate the total value of all stocks in this portfolio"""
        return sum(position.current_value() for position in self.positions.all())
    
    def total_value(self):
        """Calculate the total portfolio value (cash + stocks)"""
        return self.cash_balance + self.total_stock_value()


class Position(models.Model):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='positions')
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='positions')
    quantity = models.PositiveIntegerField(default=0)
    average_buy_price = models.DecimalField(max_digits=15, decimal_places=2)

    class Meta:
        unique_together = ('portfolio', 'stock')

    def __str__(self):
        return f"{self.portfolio.name} - {self.stock.symbol} ({self.quantity})"
    
    def current_value(self):
        """Calculate the current value of this position"""
        return self.quantity * self.stock.last_price if self.stock.last_price else 0
    
    def profit_loss(self):
        """Calculate the profit/loss for this position"""
        if not self.stock.last_price:
            return 0
        return (self.stock.last_price - self.average_buy_price) * self.quantity


class Transaction(models.Model):
    BUY = 'buy'
    SELL = 'sell'
    TRANSACTION_TYPES = [
        (BUY, 'Buy'),
        (SELL, 'Sell'),
    ]
    
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='transactions')
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=4, choices=TRANSACTION_TYPES)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=15, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.transaction_type} {self.quantity} {self.stock.symbol} @ {self.price}"
    
    def total_amount(self):
        """Calculate the total transaction amount"""
        return self.quantity * self.price


class PortfolioSnapshot(models.Model):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='snapshots')
    date = models.DateField()
    total_value = models.DecimalField(max_digits=15, decimal_places=2)
    
    class Meta:
        unique_together = ('portfolio', 'date')
    
    def __str__(self):
        return f"{self.portfolio.name} - {self.date} (${self.total_value})"
