"""Debug script to test order submission."""
import sys
sys.path.insert(0, 'D:/Coding/Stocks')

import uuid
import json
from decimal import Decimal
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from api.app.main import app
from api.app.models.base import BaseModel as Base
from api.app.core.database import get_db

# Test database setup
TEST_DATABASE_URL = 'sqlite:///:memory:'
test_engine = create_engine(TEST_DATABASE_URL, connect_args={'check_same_thread': False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

Base.metadata.create_all(bind=test_engine)
session = TestSessionLocal()

def override_get_db():
    try:
        yield session
    finally:
        pass

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

trader_id = uuid.uuid4()
mock_trader = Mock()
mock_trader.available_balance = Decimal('10000.00')
mock_trader.daily_losses = Decimal('0.00')
mock_trader.daily_loss_limit = Decimal('5000.00')
mock_trader.current_position = 0
mock_trader.max_position_size = 1000

mock_exchange = Mock()
mock_exchange.get_current_price.return_value = Decimal('150.00')

print(f"Testing with trader_id: {trader_id}")

with patch('api.app.routes.orders.trader_repository') as mock_trader_repo, \
     patch('api.app.routes.orders.exchange_adapter', mock_exchange):
    mock_trader_repo.get_by_id.return_value = mock_trader

    print(f"Mock trader repo configured: {mock_trader_repo}")
    print(f"Mock exchange configured: {mock_exchange}")

    response = client.post(
        '/api/v1/orders',
        json={
            'symbol': 'AAPL',
            'quantity': 100,
            'order_type': 'MARKET',
            'price': None,
            'stop_loss': 145.50,
            'take_profit': 155.00,
        },
        headers={'Authorization': f'Bearer {trader_id}'},
    )

    print(f'\nStatus: {response.status_code}')
    print(f'Response: {json.dumps(response.json(), indent=2)}')
