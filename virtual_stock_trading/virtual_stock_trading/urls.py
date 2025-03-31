"""
URL configuration for virtual_stock_trading project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # Keep only one of these - this will make all routes accessible at root level
    path('', include('api.urls')),
]
