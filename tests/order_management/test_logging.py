import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from src.trading_bot.order_management.manager import append_order_log
from src.trading_bot.order_management.models import OrderEnvelope


def test_append_order_log_writes_json(tmp_path: Path) -> None:
    log_path = tmp_path / "orders.jsonl"
    envelope = OrderEnvelope(
        order_id="abc",
        symbol="TSLA",
        side="BUY",
        quantity=5,
        limit_price=Decimal("249.93"),
        execution_mode="LIVE",
        submitted_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )

    append_order_log(
        log_path=log_path,
        session_id="session-123",
        bot_version="1.0.0",
        config_hash="deadbeef",
        action="submit",
        strategy_name="alpha",
        envelope=envelope,
        extra={"status": "queued"},
    )

    content = log_path.read_text().strip()
    data = json.loads(content)

    assert data["order_id"] == "abc"
    assert data["session_id"] == "session-123"
    assert data["limit_price"] == "249.93"
    assert data["action"] == "submit"
    assert data["strategy_name"] == "alpha"
    assert data["bot_version"] == "1.0.0"
    assert data["config_hash"] == "deadbeef"
    assert data["status"] == "queued"
