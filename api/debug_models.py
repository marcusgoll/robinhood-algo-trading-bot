"""Debug script to verify models load correctly."""
import sys
from pathlib import Path

# Add api directory to path
api_dir = Path(__file__).parent
sys.path.insert(0, str(api_dir))

# Import models
from app.models.base import Base
from app.models import Order, Fill, ExecutionLog

print("Models imported successfully")
print("Base.metadata tables:", list(Base.metadata.tables.keys()))

# Try creating an engine
from sqlalchemy import create_engine
engine = create_engine("sqlite:///:memory:")
Base.metadata.create_all(engine)
print("Tables created:", list(engine.table_names()))
