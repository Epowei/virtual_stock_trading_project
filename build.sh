#!/bin/bash
# Debug: show current directory structure
echo "Current directory: $(pwd)"
ls -la

# Navigate to project directory if needed
if [ -d "virtual_stock_trading" ]; then
    cd virtual_stock_trading
    echo "Changed to directory: $(pwd)"
fi

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate --noinput