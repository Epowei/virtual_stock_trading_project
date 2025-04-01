from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Stock, Portfolio, Position, Transaction, PortfolioSnapshot

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

class StockSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        fields = ['id', 'symbol', 'company_name', 'last_price', 'last_updated']

class PositionSerializer(serializers.ModelSerializer):
    stock = StockSerializer(read_only=True)
    stock_symbol = serializers.CharField(write_only=True, required=False)
    current_value = serializers.SerializerMethodField()
    profit_loss = serializers.SerializerMethodField()
    
    class Meta:
        model = Position
        fields = ['id', 'stock', 'stock_symbol', 'quantity', 'average_buy_price', 
                  'current_value', 'profit_loss']
        read_only_fields = ['id', 'average_buy_price']
    
    def get_current_value(self, obj):
        return obj.current_value()
    
    def get_profit_loss(self, obj):
        return obj.profit_loss()

class TransactionSerializer(serializers.ModelSerializer):
    stock_symbol = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = Transaction
        fields = ['id', 'portfolio', 'stock', 'transaction_type', 'quantity', 'price', 'timestamp', 'stock_symbol']
        read_only_fields = ['id', 'timestamp']
    
    def create(self, validated_data):
        # Extract and remove stock_symbol if it exists
        stock_symbol = validated_data.pop('stock_symbol', None)
        
        # If stock_symbol was provided, get or create the stock
        if stock_symbol:
            stock, created = Stock.objects.get_or_create(
                symbol=stock_symbol,
                defaults={
                    'company_name': stock_symbol,
                    'last_price': validated_data.get('price', 0),
                    'last_updated': timezone.now()
                }
            )
            validated_data['stock'] = stock
            
        return super().create(validated_data)

class PortfolioSerializer(serializers.ModelSerializer):
    total_value = serializers.SerializerMethodField()
    
    class Meta:
        model = Portfolio
        fields = ['id', 'name', 'description', 'cash_balance', 
                  'created_at', 'updated_at', 'total_value']
    
    def get_total_value(self, obj):
        return obj.total_value()

class PortfolioDetailSerializer(PortfolioSerializer):
    positions = PositionSerializer(many=True, read_only=True)
    
    class Meta(PortfolioSerializer.Meta):
        fields = PortfolioSerializer.Meta.fields + ['positions']

class PortfolioSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortfolioSnapshot
        fields = ['id', 'portfolio', 'date', 'total_value']
        read_only_fields = ['id']