import os
import requests
import logging
from django.utils import timezone
from datetime import timedelta, datetime
from ..models import Stock
from dotenv import load_dotenv
import random
import json
from decimal import Decimal

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class StockService:
    # Finnhub API configuration
    FINNHUB_BASE_URL = "https://finnhub.io/api/v1"
    FINNHUB_API_KEY = os.getenv('FINNHUB_API_KEY')
    
    # Mock data for development/testing or when API fails
    MOCK_STOCKS = {
        'AAPL': {'symbol': 'AAPL', 'name': 'Apple Inc.', 'type': 'Equity', 'region': 'United States', 'base_price': 175.23},
        'MSFT': {'symbol': 'MSFT', 'name': 'Microsoft Corporation', 'type': 'Equity', 'region': 'United States', 'base_price': 350.45},
        'GOOGL': {'symbol': 'GOOGL', 'name': 'Alphabet Inc.', 'type': 'Equity', 'region': 'United States', 'base_price': 140.78},
        'AMZN': {'symbol': 'AMZN', 'name': 'Amazon.com Inc.', 'type': 'Equity', 'region': 'United States', 'base_price': 180.14},
        'TSLA': {'symbol': 'TSLA', 'name': 'Tesla, Inc.', 'type': 'Equity', 'region': 'United States', 'base_price': 240.56},
        'META': {'symbol': 'META', 'name': 'Meta Platforms Inc.', 'type': 'Equity', 'region': 'United States', 'base_price': 330.21},
        'FB': {'symbol': 'FB', 'name': 'Meta Platforms Inc. (formerly Facebook)', 'type': 'Equity', 'region': 'United States', 'base_price': 330.21},
        'NVDA': {'symbol': 'NVDA', 'name': 'NVIDIA Corporation', 'type': 'Equity', 'region': 'United States', 'base_price': 450.87},
        'JPM': {'symbol': 'JPM', 'name': 'JPMorgan Chase & Co.', 'type': 'Equity', 'region': 'United States', 'base_price': 170.34},
        'V': {'symbol': 'V', 'name': 'Visa Inc.', 'type': 'Equity', 'region': 'United States', 'base_price': 250.12},
        'JNJ': {'symbol': 'JNJ', 'name': 'Johnson & Johnson', 'type': 'Equity', 'region': 'United States', 'base_price': 155.67},
        'WMT': {'symbol': 'WMT', 'name': 'Walmart Inc.', 'type': 'Equity', 'region': 'United States', 'base_price': 65.43},
        'IBM': {'symbol': 'IBM', 'name': 'International Business Machines', 'type': 'Equity', 'region': 'United States', 'base_price': 175.30}
    }
    
    # Common search terms mapped to ticker symbols
    SEARCH_ALIASES = {
        'NVIDIA': 'NVDA',
        'FACEBOOK': 'META',
        'GOOGLE': 'GOOGL',
        'AMAZON': 'AMZN',
        'APPLE': 'AAPL',
        'MICROSOFT': 'MSFT',
        'TESLA': 'TSLA',
    }

    @classmethod
    def use_mock_data(cls):
        """Determine whether to use mock data or real API"""
        # Use mock data if no API key or in testing mode
        return not cls.FINNHUB_API_KEY or os.getenv('USE_MOCK_DATA', 'False').lower() == 'true'

    @classmethod
    def search_stocks(cls, query):
        """
        Search for stocks using Finnhub API with fallback to mock data
        """
        print(f"StockService.search_stocks called with query: {query}")
        
        if not query:
            return {"results": []}
            
        # Use mock data if configured to do so
        if cls.use_mock_data():
            return cls._mock_search_stocks(query)
            
        try:
            # Make API request to Finnhub search endpoint
            url = f"{cls.FINNHUB_BASE_URL}/search"
            params = {
                'q': query,
                'token': cls.FINNHUB_API_KEY
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            # Check if we got valid results
            if 'result' in data and data['result']:
                results = []
                for item in data['result']:
                    # Filter to only include stocks (not ETFs or other types)
                    if 'type' in item and item['type'] == 'Common Stock':
                        results.append({
                            'symbol': item.get('symbol', ''),
                            'name': item.get('description', ''),
                            'type': 'Equity',
                            'region': item.get('exchange', 'United States')
                        })
                
                print(f"Finnhub API returned {len(results)} results for '{query}'")
                return {"results": results[:10]}  # Limit to 10 results
            else:
                print(f"No results from Finnhub for '{query}', falling back to mock data")
                return cls._mock_search_stocks(query)
                
        except Exception as e:
            print(f"Error in Finnhub search: {str(e)}")
            logger.exception(f"Finnhub API error: {str(e)}")
            # Fall back to mock data
            return cls._mock_search_stocks(query)

    @classmethod
    def _mock_search_stocks(cls, query):
        """Search for stocks using mock data"""
        print(f"Using mock data search for '{query}'")
        
        # Normalize the query
        query = query.strip().upper()
        results = []
        
        # Check if query is an exact stock ticker
        if query in cls.MOCK_STOCKS:
            results.append(cls.MOCK_STOCKS[query])
        
        # Check if query is a known company name
        elif query in cls.SEARCH_ALIASES:
            ticker = cls.SEARCH_ALIASES[query]
            results.append(cls.MOCK_STOCKS[ticker])
        
        # Otherwise do a partial match search
        else:
            for symbol, data in cls.MOCK_STOCKS.items():
                # Match on symbol
                if query in symbol:
                    results.append(data)
                # Match on name (case insensitive)
                elif query.lower() in data['name'].lower():
                    results.append(data)
        
        print(f"Mock data returned {len(results)} results for query '{query}'")
        return {"results": results}

    @classmethod
    def get_stock_price(cls, symbol):
        """
        Get current stock price using Finnhub API with fallback to mock data
        """
        symbol = symbol.upper()
        
        # Use mock data if configured to do so
        if cls.use_mock_data():
            return cls._mock_stock_price(symbol)
            
        try:
            # Make API request to Finnhub quote endpoint
            url = f"{cls.FINNHUB_BASE_URL}/quote"
            params = {
                'symbol': symbol,
                'token': cls.FINNHUB_API_KEY
            }
            
            response = requests.get(url, params=params, timeout=5)
            data = response.json()
            
            # Check if we got valid results
            if 'c' in data and data['c'] > 0:
                # Format the response
                return {
                    'symbol': symbol,
                    'price': data['c'],  # Current price
                    'change': data['d'],  # Change
                    'percent_change': data['dp'],  # Percent change
                    'high': data['h'],  # High price of the day
                    'low': data['l'],  # Low price of the day
                    'timestamp': datetime.fromtimestamp(data['t']).isoformat() 
                }
            else:
                print(f"No valid price data from Finnhub for {symbol}, using mock data")
                return cls._mock_stock_price(symbol)
                
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            # Return mock data on connection error
            price = Decimal(random.uniform(50, 500)).quantize(Decimal('0.01'))
            print(f"Error connecting to Finnhub API for {symbol}: {e}")
            return {
                'symbol': symbol,
                'price': float(price),
                'change': float(Decimal(random.uniform(-5, 5)).quantize(Decimal('0.01'))),
                'change_percent': float(Decimal(random.uniform(-3, 3)).quantize(Decimal('0.01'))),
                'updated_at': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"Error getting Finnhub price for {symbol}: {str(e)}")
            logger.exception(f"Finnhub API error for {symbol}: {str(e)}")
            # Fall back to mock data
            return cls._mock_stock_price(symbol)

    @classmethod
    def _mock_stock_price(cls, symbol):
        """Generate mock stock price data"""
        # Get the base price for this stock, or use a default
        stock_data = cls.MOCK_STOCKS.get(symbol, None)
        if stock_data:
            base_price = stock_data.get('base_price', 100.0)
        else:
            base_price = 100.0
        
        # Add some random variation (±2%)
        variation = base_price * random.uniform(-0.02, 0.02)
        price = round(base_price + variation, 2)
        
        # Generate mock change and percentage
        change = round(random.uniform(-5, 5), 2)
        percent_change = round(change / base_price * 100, 2)
        
        return {
            'symbol': symbol,
            'price': price,
            'change': change,
            'percent_change': percent_change,
            'high': round(price + random.uniform(0, 3), 2),
            'low': round(price - random.uniform(0, 3), 2),
            'timestamp': datetime.now().isoformat()
        }

    @classmethod
    def get_company_info(cls, symbol):
        """
        Get company information using Finnhub API with fallback to mock data
        """
        symbol = symbol.upper()
        
        # Use mock data if configured to do so
        if cls.use_mock_data():
            return cls._mock_company_info(symbol)
            
        try:
            # Make API request to Finnhub company profile endpoint
            url = f"{cls.FINNHUB_BASE_URL}/stock/profile2"
            params = {
                'symbol': symbol,
                'token': cls.FINNHUB_API_KEY
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            # Check if we got valid results
            if 'name' in data:
                return {
                    'symbol': symbol,
                    'name': data.get('name', ''),
                    'exchange': data.get('exchange', ''),
                    'industry': data.get('finnhubIndustry', ''),
                    'market_cap': data.get('marketCapitalization', 0),
                    'website': data.get('weburl', ''),
                    'logo': data.get('logo', ''),
                    'country': data.get('country', '')
                }
            else:
                print(f"No company info from Finnhub for {symbol}, using mock data")
                return cls._mock_company_info(symbol)
                
        except Exception as e:
            print(f"Error getting Finnhub company info for {symbol}: {str(e)}")
            logger.exception(f"Finnhub API error for {symbol}: {str(e)}")
            # Fall back to mock data
            return cls._mock_company_info(symbol)

    @classmethod
    def _mock_company_info(cls, symbol):
        """Generate mock company information"""
        stock_data = cls.MOCK_STOCKS.get(symbol, None)
        if not stock_data:
            return {
                'symbol': symbol,
                'name': f"{symbol} Inc.",
                'exchange': 'NYSE',
                'industry': 'Technology',
                'market_cap': 1000000000,
                'website': f"https://www.{symbol.lower()}.com",
                'logo': '',
                'country': 'United States'
            }
            
        return {
            'symbol': symbol,
            'name': stock_data.get('name', f"{symbol} Inc."),
            'exchange': 'NYSE',
            'industry': 'Technology',
            'market_cap': 1000000000,
            'website': f"https://www.{symbol.lower()}.com",
            'logo': '',
            'country': 'United States'
        }