import os
import requests
import logging
from django.utils import timezone
from datetime import timedelta, datetime
from ..models import Stock
from dotenv import load_dotenv
import random

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class StockService:
    BASE_URL = "https://www.alphavantage.co/query"
    API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY', "demo")
    
    @classmethod
    def get_stock_data(cls, symbol):
        """Fetch real-time stock data from Alpha Vantage"""
        try:
            params = {
                "function": "GLOBAL_QUOTE",
                "symbol": symbol,
                "apikey": cls.API_KEY
            }
            response = requests.get(cls.BASE_URL, params=params)
            data = response.json()
            
            if "Global Quote" in data and data["Global Quote"]:
                quote = data["Global Quote"]
                return {
                    'symbol': quote.get("01. symbol"),
                    'price': float(quote.get("05. price", 0)),
                    'change': float(quote.get("09. change", 0)),
                    'change_percent': float(quote.get("10. change percent", "0%").rstrip('%')),
                    'updated_at': datetime.now().isoformat()
                }
                
            # For development/testing when API calls are limited:
            # Return mock data if actual API call fails
            return {
                'symbol': symbol,
                'price': cls._get_mock_price(symbol),
                'change': cls._get_mock_change(),
                'change_percent': cls._get_mock_change_percent(),
                'updated_at': datetime.now().isoformat()
            }
                
        except Exception as e:
            logger.exception(f"Error fetching stock data for {symbol}: {str(e)}")
            return None

    @classmethod
    def _get_mock_price(cls, symbol):
        """Generate a consistent mock price based on the symbol (for testing)"""
        # Use the sum of ASCII values in the symbol to generate a base price
        base_price = sum(ord(c) for c in symbol) / 3
        # Add some randomization but keep it within a small range
        return round(base_price + (random.random() * 2 - 1), 2)

    @classmethod
    def _get_mock_change(cls):
        """Generate a random price change (for testing)"""
        return round(random.uniform(-5, 5), 2)

    @classmethod
    def _get_mock_change_percent(cls):
        """Generate a random percent change (for testing)"""
        return round(random.uniform(-3, 3), 2)

    @classmethod
    def get_company_name(cls, symbol):
        """Fetch company name from Alpha Vantage"""
        try:
            params = {
                "function": "OVERVIEW",
                "symbol": symbol,
                "apikey": cls.API_KEY
            }
            response = requests.get(cls.BASE_URL, params=params)
            data = response.json()
            
            if "Name" in data:
                return data["Name"]
            return None
        except Exception as e:
            logger.exception(f"Error fetching company name for {symbol}: {str(e)}")
            return None
    
    @classmethod
    def search_stocks(cls, query):
        """Search for stocks by keyword or symbol"""
        try:
            params = {
                "function": "SYMBOL_SEARCH",
                "keywords": query,
                "apikey": cls.API_KEY
            }
            response = requests.get(cls.BASE_URL, params=params)
            data = response.json()
            
            if "bestMatches" in data:
                results = []
                for match in data["bestMatches"]:
                    results.append({
                        "symbol": match.get("1. symbol", ""),
                        "name": match.get("2. name", ""),
                        "type": match.get("3. type", ""),
                        "region": match.get("4. region", ""),
                    })
                return results
            return []
        except Exception as e:
            logger.exception(f"Error searching stocks: {str(e)}")
            return []