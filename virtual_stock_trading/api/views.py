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
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.utils import timezone


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
        updated_stock = StockService.get_stock_price(stock.symbol)
        # updated_stock = StockService.get_stock_data(stock.symbol)
        
        if not updated_stock:
            return Response(
                {'error': f'Unable to fetch current price for {stock.symbol}'}, 
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        return Response({
            'symbol': stock.symbol,
            'company_name': stock.company_name,
            'price': updated_stock.get('price', 0),
            'last_updated': updated_stock.get('updated_at', datetime.now().isoformat())
        })
        
        # return Response({
        #     'symbol': updated_stock.symbol,
        #     'company_name': updated_stock.company_name,
        #     'price': updated_stock.last_price,
        #     'last_updated': updated_stock.last_updated
        # })


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
        if (portfolio_id):
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
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        portfolio_pk = self.kwargs.get('portfolio_pk')
        if portfolio_pk:
            return Transaction.objects.filter(portfolio_id=portfolio_pk)
        return Transaction.objects.none()
    
    def create(self, request, *args, **kwargs):
        print("Transaction create method called!")  # Debug log
        portfolio_pk = self.kwargs.get('portfolio_pk')
        
        try:
            # Get the portfolio and verify ownership
            portfolio = Portfolio.objects.get(id=portfolio_pk, user=request.user)
            
            # Extract data
            data = request.data
            symbol = data.get('stock_symbol')
            quantity = int(data.get('quantity', 0))
            price = float(data.get('price', 0))
            transaction_type = data.get('transaction_type', 'buy')
            
            # Get or create stock
            stock, created = Stock.objects.get_or_create(
                symbol=symbol,
                defaults={
                    'company_name': symbol,
                    'last_price': price,
                    'last_updated': timezone.now()
                }
            )
            
            # Calculate total
            total_cost = price * quantity
            
            # Check if portfolio has enough funds
            if transaction_type == 'buy' and portfolio.cash_balance < total_cost:
                return Response({"error": f"Insufficient funds. Need ${total_cost} but have ${portfolio.cash_balance}"}, status=400)
            
            # Create transaction record
            transaction = Transaction.objects.create(
                portfolio=portfolio,
                stock=stock,
                transaction_type=transaction_type,
                quantity=quantity,
                price=price
            )
            
            # Update portfolio balance
            if transaction_type == 'buy':
                portfolio.cash_balance -= total_cost
            else:  # sell
                portfolio.cash_balance += total_cost
            
            portfolio.save()
            
            # Update or create position
            if transaction_type == 'buy':
                position, created = Position.objects.get_or_create(
                    portfolio=portfolio,
                    stock=stock,
                    defaults={'quantity': 0, 'average_buy_price': 0}
                )
                
                # Update position
                if created:
                    position.quantity = quantity
                    position.average_buy_price = price
                else:
                    # Update average price
                    total_shares = position.quantity + quantity
                    position.average_buy_price = ((position.average_buy_price * position.quantity) + 
                                              (price * quantity)) / total_shares
                    position.quantity = total_shares
                
                position.save()
                
            return Response({
                "success": True,
                "message": f"Successfully purchased {quantity} shares of {symbol}",
                "transaction_id": transaction.id
            }, status=201)
            
        except Exception as e:
            print(f"Transaction error: {str(e)}")
            return Response({"error": str(e)}, status=400)


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
    query = request.GET.get('q', '')
    search_results = []
    
    if query:
        response = StockService.search_stocks(query)
        search_results = response.get('results', [])
        print(f"Found {len(search_results)} stocks matching '{query}'")
    
    # Get price data for popular stocks to display by default
    popular_symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'JPM', 'V', 'JNJ']
    popular_stocks = []
    
    for symbol in popular_symbols:
        price_data = StockService.get_stock_price(symbol)
        popular_stocks.append({
            'symbol': symbol,
            'price': price_data.get('price', 0)
        })
    
    # Get user's portfolios (add this line)
    # Use prefetch_related to optimize database queries
    user_portfolios = Portfolio.objects.filter(user=request.user)
    
    return render(request, 'api/watchlist.html', {
        'query': query,
        'results': search_results,
        'popular_stocks': popular_stocks,
        'portfolios': user_portfolios,  # Add portfolios to context
    })

@api_view(['GET'])
def stock_price_view(request, symbol):
    """Get the current price for a stock"""
    price_data = StockService.get_stock_price(symbol)
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

@csrf_exempt
def transaction_create_view(request):
    """Handle transaction creation via AJAX"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)
        
    try:
        data = json.loads(request.body)
        portfolio_id = data.get('portfolio_id', request.user.portfolios.first().id)
        symbol = data.get('stock_symbol')
        quantity = int(data.get('quantity', 0))
        price = float(data.get('price', 0))
        transaction_type = data.get('transaction_type')
        
        # Get or create the stock
        stock, created = Stock.objects.get_or_create(
            symbol=symbol,
            defaults={
                'company_name': symbol,  # Use symbol as name temporarily
                'last_price': price,
                'last_updated': timezone.now()
            }
        )
        
        # If stock exists but price is outdated, update it
        if not created:
            stock.last_price = price
            stock.last_updated = timezone.now()
            stock.save()
        
        # Get portfolio
        portfolio = Portfolio.objects.get(id=portfolio_id, user=request.user)
        
        # Process transaction based on type
        if transaction_type == 'buy':
            # Calculate total cost
            total_cost = price * quantity
            
            # Check if user has enough balance
            if portfolio.cash_balance < total_cost:
                return JsonResponse({'error': 'Insufficient funds'}, status=400)
                
            # Update portfolio balance
            portfolio.cash_balance -= total_cost
            portfolio.save()
            
            # Create transaction record
            transaction = Transaction.objects.create(
                portfolio=portfolio,
                stock=stock,
                transaction_type='buy',
                quantity=quantity,
                price=price
            )
            
            # Create or update position
            position, created = Position.objects.get_or_create(
                portfolio=portfolio,
                stock=stock,
                defaults={
                    'quantity': quantity,
                    'average_buy_price': price
                }
            )
            
            if not created:
                # Update existing position
                new_quantity = position.quantity + quantity
                position.average_buy_price = ((position.average_buy_price * position.quantity) + 
                                          (price * quantity)) / new_quantity
                position.quantity = new_quantity
                position.save()
                
        # For now, we only support buy
        else:
            return JsonResponse({'error': 'Unsupported transaction type'}, status=400)
            
        return JsonResponse({
            'success': True,
            'transaction_id': transaction.id,
            'new_cash_balance': float(portfolio.cash_balance)
        }, status=201)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from decimal import Decimal  # Add this import

@csrf_exempt  # Only for testing - use proper CSRF protection in production
def create_transaction_view(request, portfolio_id):
    """Direct view function for creating transactions"""
    if request.method != 'POST':
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)
    
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
        
    try:
        # Parse JSON body
        data = json.loads(request.body)
        symbol = data.get('stock_symbol')
        quantity = int(data.get('quantity', 0))
        price = float(data.get('price', 0))
        transaction_type = data.get('transaction_type', 'buy')
        
        # Convert price to Decimal to match model field type
        price_decimal = Decimal(str(price))  # Convert via string to avoid float precision issues
        
        # Get portfolio and verify ownership
        try:
            portfolio = Portfolio.objects.get(id=portfolio_id, user=request.user)
        except Portfolio.DoesNotExist:
            return JsonResponse({"error": f"Portfolio with ID {portfolio_id} not found or access denied"}, status=404)
            
        # Get or create stock
        stock, created = Stock.objects.get_or_create(
            symbol=symbol,
            defaults={
                'company_name': symbol,
                'last_price': price_decimal,  # Use decimal
                'last_updated': timezone.now()
            }
        )
        
        # Calculate total cost using Decimal
        total_cost = price_decimal * Decimal(quantity)
        
        # Check if portfolio has enough funds for buy
        if transaction_type == 'buy' and portfolio.cash_balance < total_cost:
            return JsonResponse({
                "error": f"Insufficient funds. Need ${total_cost:.2f} but have ${portfolio.cash_balance:.2f}"
            }, status=400)
            
        # Create transaction record
        transaction = Transaction.objects.create(
            portfolio=portfolio,
            stock=stock,
            transaction_type=transaction_type,
            quantity=quantity,
            price=price_decimal  # Use decimal
        )
        
        # Update portfolio balance
        if transaction_type == 'buy':
            portfolio.cash_balance -= total_cost
        else:  # sell
            portfolio.cash_balance += total_cost
        
        portfolio.save()
        
        # Update or create position
        if transaction_type == 'buy':
            position, created = Position.objects.get_or_create(
                portfolio=portfolio,
                stock=stock,
                defaults={'quantity': 0, 'average_buy_price': Decimal('0.00')}
            )
            
            # Update position
            if created:
                position.quantity = quantity
                position.average_buy_price = price_decimal
            else:
                # Update average price using Decimal
                total_shares = position.quantity + quantity
                position.average_buy_price = ((position.average_buy_price * Decimal(position.quantity)) + 
                                          (price_decimal * Decimal(quantity))) / Decimal(total_shares)
                position.quantity = total_shares
            
            position.save()
            
        return JsonResponse({
            "success": True,
            "message": f"Successfully purchased {quantity} shares of {symbol}",
            "transaction_id": transaction.id,
            "new_balance": float(portfolio.cash_balance)
        }, status=201)
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON data"}, status=400)
    except Exception as e:
        print(f"Transaction error: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)

@login_required
def stock_search_view(request):
    """API endpoint for searching stocks"""
    query = request.GET.get('q', '')
    if not query:
        return JsonResponse({'results': []})
    
    results = StockService.search_stocks(query)
    return JsonResponse({'results': results.get('results', [])})

from django.http import JsonResponse

@login_required
def stock_search_api_view(request):
    """API endpoint that returns stock search results as JSON"""
    query = request.GET.get('q', '')
    if not query:
        return JsonResponse({'results': []})
    
    response = StockService.search_stocks(query)
    results = response.get('results', [])
    
    # Log success for debugging
    print(f"API search found {len(results)} results for '{query}'")
    
    return JsonResponse({'results': results})