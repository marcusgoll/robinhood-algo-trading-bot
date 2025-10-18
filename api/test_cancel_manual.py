"""Manual test of order cancellation functionality."""
import sys
from pathlib import Path

# Add api directory to path
api_dir = Path(__file__).parent
sys.path.insert(0, str(api_dir))

from uuid import uuid4
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Import models first to register them
from app.models import Base, Order, OrderType, OrderStatus, Fill, ExecutionLog, ExecutionAction
from app.main import app
from app.core.database import get_db

# Create test database
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Create tables
print("Creating tables...")
Base.metadata.create_all(bind=test_engine)
print(f"Tables created: {list(Base.metadata.tables.keys())}")

# Create a test session
db = TestSessionLocal()

try:
    # Create a pending order
    trader_id = uuid4()
    print(f"\n1. Creating PENDING order for trader {trader_id}")
    order = Order(
        trader_id=trader_id,
        symbol="AAPL",
        quantity=100,
        order_type=OrderType.MARKET,
        price=None,
        status=OrderStatus.PENDING,
        filled_quantity=0,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    print(f"   Order created: {order.id}, status={order.status}")

    # Setup test client
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    # Test cancelling the order
    print(f"\n2. Cancelling order {order.id}")
    response = client.post(
        f"/api/v1/orders/{order.id}/cancel",
        headers={"Authorization": f"Bearer {trader_id}"},
    )

    print(f"   Response status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Order status after cancel: {data['status']}")
        print(f"   ✓ SUCCESS: Order cancelled successfully")
    else:
        print(f"   ✗ FAILED: {response.json()}")

    # Verify in database
    db.expire(order)
    db.refresh(order)
    print(f"\n3. Database verification:")
    print(f"   Order status in DB: {order.status}")

    # Check execution log
    logs = db.query(ExecutionLog).filter_by(order_id=order.id).all()
    print(f"   Execution logs: {len(logs)} entries")
    for log in logs:
        print(f"     - {log.action}: {log.reason}")

finally:
    db.close()

print("\n✓ Manual test completed")
