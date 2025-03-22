from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'stocks', views.StockViewSet)
router.register(r'portfolios', views.PortfolioViewSet, basename='portfolio')
router.register(r'positions', views.PositionViewSet, basename='position')
router.register(r'transactions', views.TransactionViewSet, basename='transaction')

# Nested routes
portfolio_positions = views.PositionViewSet.as_view({
    'get': 'list',
})

portfolio_transactions = views.TransactionViewSet.as_view({
    'get': 'list',
    'post': 'create',
})

urlpatterns = [
    path('', include(router.urls)),
    path('api-auth/', include('rest_framework.urls')),
    
    # Nested routes for cleaner API design
    path('portfolios/<int:portfolio_pk>/positions/', portfolio_positions, name='portfolio-positions'),
    path('portfolios/<int:portfolio_pk>/transactions/', portfolio_transactions, name='portfolio-transactions'),
]