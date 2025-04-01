# Virtual Stock Trading API

A Django REST API that simulates stock trading with real-time market data. Users can create portfolios, buy/sell virtual stocks, and track their performance over time.

## Project Structure

```text
virtual_stock_trading/
│
├── api/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── static/
│   │   ├── api/
│   │   │   ├── css/
│   │   │   │   └── styles.css
│   │   │   └── images/
│   │   │       └── stock-chart.jpg
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── templates/                          
│   │   └── api/
│   │       ├── base.html                   
│   │       ├── home.html                   
│   │       ├── portfolio_list.html         
│   │       ├── portfolio_detail.html     
│   │       └── watchlist.html 
│   ├── urls.py
│   └── services/
│       ├── __init__.py
│       ├── __pycache__/
│       ├── portfolio_service.py
│       ├── stock_service.py
│       └── trading_service.py
│
├── staticfiles/         # Collected static files for production
│   ├── admin/
│   ├── api/
│   ├── rest_framework/
│   └── staticfiles.json
│
├── virtual_stock_trading/
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
├── manage.py
├── requirements.txt                     
└── .env                           # Environment variables (not in version control)   
```
## Features

- User authentication and portfolio management
- Real-time stock data via Finnhub API
- Buy/sell operations with transaction history
- Portfolio performance tracking
- RESTful API design with Django REST Framework
- Live Stock price ticker

## Setup and Installation

1. Clone the repository
2. Create a virtual environment:

```python
python -m venv stock 
source stock/bin/activate
```
3. Install dependencies:
`pip install -r requirements.txt`

4. Set up environment variables:
```bash
# Create .env file in the project root
echo "SECRET_KEY=your_secret_key_here
FINNHUB_API_KEY=your_alpha_vantage_api_key
DEBUG=True" > .env
```

5. Run migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```

6. Run the development server:
```bash
python manage.py runserver
```

<br>

## Navigation
The application has several key pages:

* Home `(/)`: Landing page with project overview
* Login `(/login/)`: User login page
* Register `(/register/)`: New user registration
* Portfolios `(/portfolios/)`: List of user portfolios
* Portfolio Detail `(/portfolios/<id>/)`: Details of a specific portfolio
* Stock Watchlist `(/watchlist/)`: Search and explore stocks

<br>

## User Registration & Authentication
__Registration Process__
1. Visit the registration page at `/register/`
2. Fill in username, email, and password
3. Submit the form to create your account
4. You'll be automatically logged in and redirected to the portfolios page

__Authentication__

* The platform uses Django's built-in authentication system
* Session-based authentication for the web interface
* Token-based authentication for the API endpoints
* API requests must include an Authorization header with a valid token

## API Endpoints

__Authentication__
* `POST /api-auth/login/`: Log in and receive an authentication token
* `POST /api-auth/logout/`: Log out and invalidate token

__Portfolios__

* `GET /api/portfolios/`: List all portfolios for the authenticated user
* `POST /api/portfolios/`: Create a new portfolio
* `GET /api/portfolios/{id}/`: Retrieve a specific portfolio
* `PUT /api/portfolios/{id}/`: Update a portfolio
* `DELETE /api/portfolios/{id}/`: Delete a portfolio
* `GET /api/portfolios/{id}/performance/`: Get historical performance data

__Positions__
* `GET /api/positions/`: List all positions
* `POST /api/positions/`: Create a new position
* `GET /api/positions/{id}/`: Get details of a specific position
* `DELETE /api/positions/{id}/`: Close a position

__Transactions__
* `GET /api/transactions/`: List all transactions
* `POST /api/transactions/`: Create a new transaction
* `GET /api/transactions/{id}/`: Get details of a specific transaction

__Stocks__
* `GET /stocks/{symbol}/price/`: Get current price data for a stock
* `GET /api/stocks/search/?q={query}`: Search for stocks

__Deployment on Render__

1. Create a new account on Render

2. Create a new Web Service:
    * Connect your GitHub repository
    * Set the build command: `pip install -r requirements.txt`
    * Set the start command: `gunicorn virtual_stock_trading.wsgi:application`

3. Add environment variables:
    * `SECRET_KEY:` Your Django secret key
    * `FINNHUB_API_KEY:` Your Finnhub API key
    * `DEBUG`: Set to False for production
    * `ALLOWED_HOSTS`: Add your Render domain, e.g., your-app.onrender.com
    * `DATABASE_URL`: This will be automatically added if you use Render's PostgreSQL

4. Set up a PostgreSQL database:
    * Create a new PostgreSQL instance on Render
    * Link it to your web service

5. Deploy the application:
    * Render will automatically deploy your application
    * Monitor the deployment logs for any issues

### Technologies Used
* __Backend__: Django, Django REST Framework
* __Database:__ PostgreSQL
* __Stock Data:__ Alpha Vantage API
* __Frontend__: HTML, CSS, Bootstrap, JavaScript
* __Deployment__: Render


### Contributing
1. Fork the repository
2. Create your feature branch: git checkout -b feature/your-feature
3. Commit your changes: git commit -m 'Add your feature'
4. Push to the branch: git push origin feature/your-feature
5. Submit a pull request

### Acknowledgements
* Finnhub.io for providing stock market data
* Django and Django REST Framework
* Bootstrap for the UI components


