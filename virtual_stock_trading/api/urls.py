from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from . import views

# API router
router = DefaultRouter()
router.register(r'stocks', views.StockViewSet)
router.register(r'portfolios', views.PortfolioViewSet, basename='portfolio')
router.register(r'positions', views.PositionViewSet, basename='position')
router.register(r'transactions', views.TransactionViewSet, basename='transaction')

# Create a nested router for transactions within portfolios
portfolio_router = routers.NestedSimpleRouter(router, r'portfolios', lookup='portfolio')
portfolio_router.register(r'transactions', views.TransactionViewSet, basename='portfolio-transactions')

# HTML/frontend views first (highest priority)
urlpatterns = [
    # HTML views
    path('', views.home_view, name='home'),
    path('portfolios/', views.portfolio_list_view, name='portfolio_list'),
    path('portfolios/<int:pk>/', views.portfolio_detail_view, name='portfolio_detail'),
    path('watchlist/', views.watchlist_view, name='watchlist'),
    
    # Authentication views
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('register/', views.RegisterView.as_view(), name='register'),
    
    # Stock price API endpoint
    path('stocks/<str:symbol>/price/', views.stock_price_view, name='stock-price'),
    
    # REST API endpoints with namespace to avoid conflicts
    path('api/', include((router.urls, 'api'))),
    path('api/', include(portfolio_router.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework_auth')),
    path('portfolios/<int:pk>/adjust-cash/', views.portfolio_adjust_cash_view, name='portfolio_adjust_cash'),
    path('transactions/create/', views.transaction_create_view, name='transaction_create'),
    path('transaction/<int:portfolio_id>/', views.create_transaction_view, name='create_transaction'),
    path('api/stocks/search/', views.stock_search_api_view, name='stock-search-api'),
]