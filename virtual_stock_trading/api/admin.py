from django.contrib import admin
from .models import Stock, Portfolio, Position, Transaction, PortfolioSnapshot

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'company_name', 'last_price', 'last_updated')
    search_fields = ('symbol', 'company_name')

@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'cash_balance', 'created_at')
    list_filter = ('user',)
    search_fields = ('name', 'user__username')

@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ('portfolio', 'stock', 'quantity', 'average_buy_price')
    list_filter = ('portfolio', 'stock')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('portfolio', 'stock', 'transaction_type', 'quantity', 'price', 'timestamp')
    list_filter = ('portfolio', 'stock', 'transaction_type')
    date_hierarchy = 'timestamp'

@admin.register(PortfolioSnapshot)
class PortfolioSnapshotAdmin(admin.ModelAdmin):
    list_display = ('portfolio', 'date', 'total_value')
    list_filter = ('portfolio', 'date')
    date_hierarchy = 'date'
