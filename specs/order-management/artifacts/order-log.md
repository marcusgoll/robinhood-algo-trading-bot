# Order log format

## Overview
- **File**: `logs/orders.jsonl`
- **Format**: One JSON object per line (JSON Lines)
- **Purpose**: Immutable audit trail for every submission, cancellation, and status sync event handled by `OrderManager`

## Common fields
| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | string (ISO 8601) | When the log entry was written |
| `session_id` | string | UUID generated when the bot boots |
| `bot_version` | string | Semantic identifier for the running bot |
| `config_hash` | string | Stable hash of key risk settings to help reproduce behaviour |
| `action` | string | `submit`, `cancel`, `status`, or `status_error` |
| `strategy_name` | string \/ null | Strategy associated with the order (if known) |
| `order_id` | string | Broker-supplied identifier |
| `symbol` | string | Uppercase ticker symbol |
| `side` | string | `BUY` or `SELL` |
| `limit_price` | string | Decimal represented as string to avoid floating precision loss |
| `quantity` | integer | Requested share quantity |
| `execution_mode` | string | `PAPER` or `LIVE` |
| `submitted_at` | string | Original submission timestamp from the gateway |
| `status` | string | Optional field set for `submit`/`status` events (e.g., `confirmed`, `filled`) |
| `error` | string | Present only for `status_error` events |

## Sample entry
```json
{"timestamp":"2025-10-10T18:05:12.437Z","session_id":"61c5a3d2-1c7f-4b7a-9aad-b854f3a48e47","bot_version":"1.0.0","config_hash":"af9218d90564c87a","action":"submit","strategy_name":"manual","order_id":"4108fb07-6c66-4c3e-a9a2-40b3486bfe2b","symbol":"TSLA","side":"BUY","limit_price":"249.93","quantity":5,"execution_mode":"LIVE","submitted_at":"2025-10-10T18:05:12.394Z","status":"confirmed"}
```

## Operational guidance
- Rotate or archive `logs/orders.jsonl` alongside other trading logs (daily rotation recommended in live trading). 
- Protect the file with the same access controls as `logs/trades.jsonl`; it contains material non-public information. 
- If the file is ever manually truncated, capture the event in the runbook and snapshot the previous contents for audit continuity.
