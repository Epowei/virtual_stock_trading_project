from django.shortcuts import render
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from django.contrib.auth.models import User
from .models import Stock, Portfolio, Position, Transaction, PortfolioSnapshot
from .serializers import (
    StockSerializer, PortfolioSerializer, PortfolioDetailSerializer,
    PositionSerializer, TransactionSerializer, UserSerializer
)
from .services.stock_service import StockService
from django.contrib.auth.forms import UserCreationForm
from django.views.generic.edit import CreateView
from django.urls import reverse_lazy
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect
from datetime import datetime
import random  # Add this import
import decimal
from decimal import Decimal  # Add this import at the top of the file


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only allowed to the owner
        # Check if the object has a user attribute or is owned by a portfolio with a user
        if hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'portfolio'):
            return obj.portfolio.user == request.user
        return False


class StockViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for stocks.
    Provides read-only access to stock data.
    """
    queryset = Stock.objects.all()
    serializer_class = StockSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['symbol', 'company_name']
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        Search for stocks by keyword through Alpha Vantage API.
        """
        query = request.query_params.get('q', '')
        if not query:
            return Response({'error': 'Please provide a search query'}, status=status.HTTP_400_BAD_REQUEST)
        
        results = StockService.search_stocks(query)
        return Response(results)
    
    @action(detail=True, methods=['get'])
    def price(self, request, pk=None):
        """
        Get the latest price for a stock.
        """
        stock = self.get_object()
        updated_stock = StockService.get_stock_data(stock.symbol)
        
        if not updated_stock:
            return Response(
                {'error': f'Unable to fetch current price for {stock.symbol}'}, 
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        return Response({
            'symbol': updated_stock.symbol,
            'company_name': updated_stock.company_name,
            'price': updated_stock.last_price,
            'last_updated': updated_stock.last_updated
        })


class PortfolioViewSet(viewsets.ModelViewSet):
    """
    API endpoint for portfolios.
    Allows CRUD operations on portfolios owned by the user.
    """
    serializer_class = PortfolioSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    
    def get_queryset(self):
        return Portfolio.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return PortfolioDetailSerializer
        return PortfolioSerializer
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """
        Get portfolio summary including total value and performance.
        """
        portfolio = self.get_object()
        
        # Get latest snapshot for comparison if available
        latest_snapshot = portfolio.snapshots.order_by('-date').first()
        previous_value = latest_snapshot.total_value if latest_snapshot else portfolio.cash_balance
        
        current_value = portfolio.total_value()
        change = current_value - previous_value
        percent_change = (change / previous_value * 100) if previous_value else 0
        
        return Response({
            'id': portfolio.id,
            'name': portfolio.name,
            'cash_balance': portfolio.cash_balance,
            'total_stock_value': portfolio.total_stock_value(),
            'total_value': current_value,
            'change': change,
            'percent_change': percent_change,
            'position_count': portfolio.positions.count(),
        })
    
    @action(detail=True, methods=['get'])
    def transactions(self, request, pk=None):
        """
        Get all transactions for a portfolio.
        """
        portfolio = self.get_object()
        transactions = portfolio.transactions.all().order_by('-timestamp')
        page = self.paginate_queryset(transactions)
        
        if page is not None:
            serializer = TransactionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = TransactionSerializer(transactions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def performance(self, request, pk=None):
        """
        Get historical performance data for a portfolio.
        """
        portfolio = self.get_object()
        snapshots = portfolio.snapshots.all().order_by('date')
        
        data = [{
            'date': snapshot.date,
            'value': snapshot.total_value
        } for snapshot in snapshots]
        
        # Add current value as last point
        from datetime import date
        data.append({
            'date': date.today(),
            'value': portfolio.total_value()
        })
        
        return Response(data)


class PositionViewSet(viewsets.ModelViewSet):
    """
    API endpoint for positions.
    """
    serializer_class = PositionSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    
    def get_queryset(self):
        portfolio_id = self.kwargs.get('portfolio_pk')
        if portfolio_id:
            portfolio = get_object_or_404(Portfolio, id=portfolio_id, user=self.request.user)
            return Position.objects.filter(portfolio=portfolio)
        return Position.objects.filter(portfolio__user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        """
        Creating positions directly is not allowed. Use buy/sell transactions instead.
        """
        return Response(
            {"error": "Positions cannot be created directly. Place a buy order instead."},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    def update(self, request, *args, **kwargs):
        """
        Updating positions directly is not allowed. Use buy/sell transactions instead.
        """
        return Response(
            {"error": "Positions cannot be updated directly. Place buy/sell orders instead."},
            status=status.HTTP_400_BAD_REQUEST
        )


class TransactionViewSet(viewsets.ModelViewSet):
    """
    API endpoint for transactions.
    Allows creating new buy/sell transactions.
    """
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    
    def get_queryset(self):
        portfolio_id = self.kwargs.get('portfolio_pk')
        if portfolio_id:
            portfolio = get_object_or_404(Portfolio, id=portfolio_id, user=self.request.user)
            return Transaction.objects.filter(portfolio=portfolio)
        return Transaction.objects.filter(portfolio__user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        portfolio_id = request.data.get('portfolio') or self.kwargs.get('portfolio_pk')
        if not portfolio_id:
            return Response(
                {"error": "Portfolio ID is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            portfolio = Portfolio.objects.get(id=portfolio_id, user=request.user)
        except Portfolio.DoesNotExist:
            return Response(
                {"error": "Portfolio not found or access denied"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Extract and validate transaction details
        stock_symbol = request.data.get('stock_symbol')
        transaction_type = request.data.get('transaction_type')
        quantity = request.data.get('quantity')
        
        if not all([stock_symbol, transaction_type, quantity]):
            return Response(
                {"error": "Stock symbol, transaction type, and quantity are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            quantity = int(quantity)
            if quantity <= 0:
                raise ValueError
        except (ValueError, TypeError):
            return Response(
                {"error": "Quantity must be a positive integer"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if transaction_type not in [Transaction.BUY, Transaction.SELL]:
            return Response(
                {"error": f"Transaction type must be either '{Transaction.BUY}' or '{Transaction.SELL}'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get current stock data
        stock_data = StockService.get_stock_data(stock_symbol)
        if not stock_data:
            return Response(
                {"error": f"Could not fetch current price for {stock_symbol}"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        # Get stock object from database
        try:
            stock = Stock.objects.get(symbol=stock_symbol.upper())
        except Stock.DoesNotExist:
            # Create new stock if it doesn't exist
            stock = Stock(
                symbol=stock_symbol.upper(),
                company_name=stock_data.company_name,
                last_price=stock_data.last_price,
                last_updated=stock_data.last_updated
            )
            stock.save()
        
        # Execute the transaction with database transaction for atomicity
        with transaction.atomic():
            # Check if the user has enough cash for buy or enough shares for sell
            position = None
            try:
                position = Position.objects.get(portfolio=portfolio, stock=stock)
            except Position.DoesNotExist:
                if transaction_type == Transaction.SELL:
                    return Response(
                        {"error": f"You don't own any shares of {stock.symbol}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            total_cost = quantity * stock.last_price
            
            if transaction_type == Transaction.BUY:
                if portfolio.cash_balance < total_cost:
                    return Response(
                        {"error": "Insufficient funds to complete transaction"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Update portfolio cash balance
                portfolio.cash_balance -= total_cost
                portfolio.save()
                
                # Update or create position
                if position:
                    # Calculate new average buy price
                    total_shares = position.quantity + quantity
                    total_investment = (position.average_buy_price * position.quantity) + total_cost
                    new_avg_price = total_investment / total_shares
                    
                    position.quantity = total_shares
                    position.average_buy_price = new_avg_price
                    position.save()
                else:
                    position = Position(
                        portfolio=portfolio,
                        stock=stock,
                        quantity=quantity,
                        average_buy_price=stock.last_price
                    )
                    position.save()
            
            elif transaction_type == Transaction.SELL:
                if position.quantity < quantity:
                    return Response(
                        {"error": f"You only have {position.quantity} shares to sell"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Update portfolio cash balance
                portfolio.cash_balance += total_cost
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
                transaction_type=transaction_type,
                quantity=quantity,
                price=stock.last_price
            )
            transaction.save()
            
            return Response(
                TransactionSerializer(transaction).data,
                status=status.HTTP_201_CREATED
            )


class RegisterView(CreateView):
    form_class = UserCreationForm
    template_name = 'api/register.html'
    success_url = reverse_lazy('login')

class CustomLoginView(LoginView):
    template_name = 'api/login.html'
    redirect_authenticated_user = True

class CustomLogoutView(LogoutView):
    next_page = 'login'

def home_view(request):
    """Home page view"""
    return render(request, 'api/home.html')

@login_required
def portfolio_list_view(request):
    """View to display all portfolios for the current user"""
    # Handle portfolio creation from the form
    if request.method == 'POST':
        name = request.POST.get('name')
        cash_balance = request.POST.get('cash_balance')
        
        if name and cash_balance:
            try:
                cash_balance = float(cash_balance)
                portfolio = Portfolio.objects.create(
                    user=request.user,
                    name=name,
                    cash_balance=cash_balance
                )
                messages.success(request, f"Portfolio '{name}' created successfully!")
                return redirect('portfolio_detail', pk=portfolio.id)
            except ValueError:
                messages.error(request, "Invalid cash balance amount.")
        else:
            messages.error(request, "Please provide both name and initial balance.")
    
    # Get all user portfolios with calculated fields
    portfolios = Portfolio.objects.filter(user=request.user)
    
    # Add calculated fields to each portfolio
    for portfolio in portfolios:
        # Calculate total value (cash + positions)
        positions_value = sum(position.quantity * position.stock.last_price
                             for position in portfolio.positions.all()
                             if position.stock.last_price)
        portfolio.total_value = portfolio.cash_balance + positions_value
        
        # Calculate profit/loss if we have portfolio snapshots
        # This is simplified - in reality you'd compare with the first snapshot
        # or initial investment
        portfolio.profit_loss = portfolio.total_value - portfolio.cash_balance
        if portfolio.cash_balance > 0:
            portfolio.profit_loss_percentage = (portfolio.profit_loss / portfolio.cash_balance) * 100
        else:
            portfolio.profit_loss_percentage = 0
    
    return render(request, 'api/portfolio_list.html', {'portfolios': portfolios})

@login_required
def portfolio_detail_view(request, pk):
    """View to display portfolio details"""
    portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)
    positions = portfolio.positions.all()
    transactions = portfolio.transactions.order_by('-timestamp')[:10]  # Last 10 transactions
    
    return render(request, 'api/portfolio_detail.html', {
        'portfolio': portfolio,
        'positions': positions,
        'transactions': transactions,
    })

@login_required
def watchlist_view(request):
    """View to display and manage stock watchlist"""
    # For simplicity, we'll just show stock search functionality here
    query = request.GET.get('q', '')
    results = []
    
    if query:
        results = StockService.search_stocks(query)
    
    return render(request, 'api/watchlist.html', {
        'query': query,
        'results': results,
    })

@api_view(['GET'])
def stock_price_view(request, symbol):
    """Get the current price for a stock"""
    price_data = StockService.get_stock_data(symbol)
    if price_data:
        return Response({
            'price': price_data.get('price', 0),
            'change': price_data.get('change', 0),
            'change_percent': price_data.get('change_percent', 0),
            'updated_at': price_data.get('updated_at', datetime.now().isoformat())
        })
    
    # If we can't get real data, return mock data for the ticker to display
    return Response({
        'price': 100 + (ord(symbol[0]) % 100),  # Generate mock price based on first letter
        'change': random.uniform(-5, 5),
        'change_percent': random.uniform(-2, 2),
        'updated_at': datetime.now().isoformat()
    })

@login_required
def portfolio_adjust_cash_view(request, pk):
    """Handle deposits and withdrawals for a portfolio"""
    import decimal  # Add this import here
    
    portfolio = get_object_or_404(Portfolio, id=pk, user=request.user)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        try:
            amount = Decimal(request.POST.get('amount', 0))
            note = request.POST.get('note', '')
            
            if amount <= 0:
                messages.error(request, "Amount must be positive.")
                return redirect('portfolio_detail', pk=portfolio.id)
                
            if action == 'deposit':
                # Add to cash balance
                portfolio.cash_balance += amount
                messages.success(request, f"Successfully deposited ${amount:.2f} to your portfolio.")
                
                # Create a transaction record - use only fields that exist in the model
                Transaction.objects.create(
                    portfolio=portfolio,
                    transaction_type='deposit',
                    quantity=1,  # Not applicable for deposits
                    price=amount,
                    # Remove total_amount and notes if they don't exist
                )
                
            elif action == 'withdraw':
                # Check if there's enough cash
                if amount > portfolio.cash_balance:
                    messages.error(request, f"Insufficient funds. Your available cash balance is ${portfolio.cash_balance:.2f}.")
                    return redirect('portfolio_detail', pk=portfolio.id)
                
                # Subtract from cash balance
                portfolio.cash_balance -= amount
                messages.success(request, f"Successfully withdrew ${amount:.2f} from your portfolio.")
                
                # Create a transaction record - use only fields that exist in the model
                Transaction.objects.create(
                    portfolio=portfolio,
                    transaction_type='withdraw',
                    quantity=1,  # Not applicable for withdrawals
                    price=amount,
                    # Remove total_amount and notes if they don't exist
                )
            else:
                messages.error(request, "Invalid action.")
                return redirect('portfolio_detail', pk=portfolio.id)
            
            # Save the portfolio
            portfolio.save()
            
        except (ValueError, decimal.InvalidOperation) as e:
            messages.error(request, f"Invalid amount: {str(e)}")
    
    return redirect('portfolio_detail', pk=portfolio.id)
