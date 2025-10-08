"""
Unit tests for AccountData service.

Tests:
- Data models (Position, AccountBalance, CacheEntry)
- Cache logic (hit, miss, stale, invalidation)
- API fetching (buying power, positions, balance, day trade count)
- P&L calculations
- Error handling

Constitution v1.0.0 - §Testing_Requirements: TDD approach (RED → GREEN → REFACTOR)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from decimal import Decimal


class TestDataModels:
    """Test suite for data model dataclasses."""

    def test_position_profit_calculation(self):
        """
        T006: Test Position calculates profit correctly.

        GIVEN: Position with gain ($150 → $155)
        WHEN: P&L calculated
        THEN: Profit is $50 (10 shares × $5 gain)
        """
        from src.trading_bot.account.account_data import Position

        position = Position(
            symbol="AAPL",
            quantity=10,
            average_buy_price=Decimal("150.00"),
            current_price=Decimal("155.00"),
            last_updated=datetime.utcnow()
        )

        # WHEN: P&L calculated
        profit_loss = position.profit_loss

        # THEN: Profit is $50
        assert profit_loss == Decimal("50.00")
        assert position.cost_basis == Decimal("1500.00")
        assert position.current_value == Decimal("1550.00")

    def test_position_loss_calculation(self):
        """
        T007: Test Position dataclass with loss calculation.

        GIVEN: Position with loss ($150 → $145)
        WHEN: P&L calculated
        THEN: Loss is -$50 (10 shares × $5 loss)
        """
        from src.trading_bot.account.account_data import Position

        position = Position(
            symbol="AAPL",
            quantity=10,
            average_buy_price=Decimal("150.00"),
            current_price=Decimal("145.00"),
            last_updated=datetime.utcnow()
        )

        # WHEN: P&L calculated
        profit_loss = position.profit_loss

        # THEN: Loss is -$50
        assert profit_loss == Decimal("-50.00")
        assert position.profit_loss < 0

    def test_position_pl_percentage_calculation(self):
        """
        T008: Test Position P&L percentage calculation.

        GIVEN: Position with $50 profit on $1500 cost basis
        WHEN: P&L percentage calculated
        THEN: Percentage is 3.33%
        """
        from src.trading_bot.account.account_data import Position

        position = Position(
            symbol="AAPL",
            quantity=10,
            average_buy_price=Decimal("150.00"),
            current_price=Decimal("155.00"),
            last_updated=datetime.utcnow()
        )

        # WHEN: P&L percentage calculated
        profit_loss_pct = position.profit_loss_pct

        # THEN: Percentage is approximately 3.33%
        assert profit_loss_pct == Decimal("3.333333333333333333333333333")  # (50/1500) * 100

    def test_account_balance_dataclass_fields(self):
        """
        T009: Test AccountBalance dataclass fields.

        GIVEN: AccountBalance with cash, equity, buying_power
        WHEN: Balance created
        THEN: All fields populated correctly
        """
        from src.trading_bot.account.account_data import AccountBalance

        balance = AccountBalance(
            cash=Decimal("5000.00"),
            equity=Decimal("12500.75"),
            buying_power=Decimal("10000.50"),
            last_updated=datetime.utcnow()
        )

        # THEN: All fields accessible
        assert balance.cash == Decimal("5000.00")
        assert balance.equity == Decimal("12500.75")
        assert balance.buying_power == Decimal("10000.50")
        assert isinstance(balance.last_updated, datetime)

    def test_cache_entry_dataclass_with_ttl(self):
        """
        T010: Test CacheEntry dataclass with TTL.

        GIVEN: CacheEntry with value, cached_at, ttl_seconds
        WHEN: Cache entry created
        THEN: All fields stored correctly
        """
        from src.trading_bot.account.account_data import CacheEntry

        cached_at = datetime.utcnow()
        cache_entry = CacheEntry(
            value={"buying_power": 10000.50},
            cached_at=cached_at,
            ttl_seconds=60
        )

        # THEN: All fields accessible
        assert cache_entry.value == {"buying_power": 10000.50}
        assert cache_entry.cached_at == cached_at
        assert cache_entry.ttl_seconds == 60


class TestCacheLogic:
    """Test suite for TTL-based caching."""

    def test_cache_miss_fetches_from_api(self):
        """
        T016: Test cache miss triggers API call.

        GIVEN: Empty cache
        WHEN: get_buying_power called
        THEN: API called and result returned
        """
        from src.trading_bot.account.account_data import AccountData

        with patch('robin_stocks.robinhood.account.load_account_profile') as mock_api:
            mock_api.return_value = {'buying_power': '10000.50'}
            mock_auth = Mock()

            account = AccountData(auth=mock_auth)

            # WHEN: get_buying_power called
            result = account.get_buying_power()

            # THEN: API called and result returned
            assert result == 10000.50
            mock_api.assert_called_once()

    def test_cache_hit_returns_cached_value(self):
        """
        T017: Test cache hit returns cached value.

        GIVEN: Cached buying power
        WHEN: get_buying_power called twice
        THEN: API called only once, second call uses cache
        """
        from src.trading_bot.account.account_data import AccountData

        with patch('robin_stocks.robinhood.account.load_account_profile') as mock_api:
            mock_api.return_value = {'buying_power': '10000.50'}
            mock_auth = Mock()

            account = AccountData(auth=mock_auth)

            # WHEN: Called twice
            result1 = account.get_buying_power(use_cache=True)
            result2 = account.get_buying_power(use_cache=True)

            # THEN: API called only once
            assert result1 == result2 == 10000.50
            assert mock_api.call_count == 1

    def test_stale_cache_triggers_refetch(self):
        """
        T018: Test stale cache (expired TTL) triggers refetch.

        GIVEN: Cached buying power older than TTL
        WHEN: get_buying_power called
        THEN: API called again with fresh data
        """
        from src.trading_bot.account.account_data import AccountData

        with patch('robin_stocks.robinhood.account.load_account_profile') as mock_api:
            with patch('src.trading_bot.account.account_data.datetime') as mock_datetime:
                mock_api.return_value = {'buying_power': '10000.50'}
                mock_auth = Mock()

                # Mock time progression
                start_time = datetime(2025, 1, 8, 12, 0, 0)
                stale_time = datetime(2025, 1, 8, 12, 2, 0)  # 2 minutes later (past 60s TTL)

                mock_datetime.utcnow.side_effect = [start_time, stale_time, stale_time]

                account = AccountData(auth=mock_auth)

                # WHEN: First call caches
                result1 = account.get_buying_power(use_cache=True)

                # Advance time past TTL
                mock_api.return_value = {'buying_power': '12000.75'}

                # Second call should refetch
                result2 = account.get_buying_power(use_cache=True)

                # THEN: API called twice
                assert mock_api.call_count == 2
                assert result2 == 12000.75

    def test_manual_cache_invalidation_specific_key(self):
        """
        T019: Test manual cache invalidation clears specific key.

        GIVEN: Cached buying power
        WHEN: invalidate_cache('buying_power') called
        THEN: Next call fetches fresh data
        """
        from src.trading_bot.account.account_data import AccountData

        with patch('robin_stocks.robinhood.account.load_account_profile') as mock_api:
            mock_api.return_value = {'buying_power': '10000.50'}
            mock_auth = Mock()

            account = AccountData(auth=mock_auth)

            # WHEN: First call caches
            result1 = account.get_buying_power(use_cache=True)

            # Invalidate cache
            account.invalidate_cache('buying_power')

            # Second call should refetch
            mock_api.return_value = {'buying_power': '15000.00'}
            result2 = account.get_buying_power(use_cache=True)

            # THEN: API called twice
            assert mock_api.call_count == 2
            assert result2 == 15000.00

    def test_manual_cache_invalidation_all_keys(self):
        """
        T020: Test manual cache invalidation clears all keys.

        GIVEN: Multiple cached values
        WHEN: invalidate_cache(None) called
        THEN: All caches cleared
        """
        from src.trading_bot.account.account_data import AccountData

        mock_auth = Mock()
        account = AccountData(auth=mock_auth)

        # WHEN: Populate cache manually
        account._cache['buying_power'] = Mock()
        account._cache['positions'] = Mock()
        account._cache['balance'] = Mock()

        # Invalidate all
        account.invalidate_cache(None)

        # THEN: All caches cleared
        assert len(account._cache) == 0


class TestAPIFetching:
    """Test suite for robin-stocks API integration."""

    def test_fetch_positions_returns_list(self):
        """
        T026: Test get_positions returns list of Position objects.

        GIVEN: API returns holdings
        WHEN: get_positions called
        THEN: Returns list with Position objects with P&L
        """
        from src.trading_bot.account.account_data import AccountData, Position

        with patch('robin_stocks.robinhood.account.build_holdings') as mock_api:
            mock_api.return_value = {
                'AAPL': {
                    'quantity': '10',
                    'average_buy_price': '150.25',
                    'price': '155.00',
                    'equity': '1550.00'
                }
            }
            mock_auth = Mock()

            account = AccountData(auth=mock_auth)

            # WHEN: get_positions called
            positions = account.get_positions()

            # THEN: Returns list with Position object
            assert len(positions) == 1
            assert isinstance(positions[0], Position)
            assert positions[0].symbol == 'AAPL'
            assert positions[0].quantity == 10
            assert positions[0].profit_loss == Decimal("47.50")  # (155-150.25) * 10

    def test_empty_positions_returns_empty_list(self):
        """
        T027: Test empty positions returns empty list.

        GIVEN: API returns no holdings
        WHEN: get_positions called
        THEN: Returns empty list
        """
        from src.trading_bot.account.account_data import AccountData

        with patch('robin_stocks.robinhood.account.build_holdings') as mock_api:
            mock_api.return_value = {}
            mock_auth = Mock()

            account = AccountData(auth=mock_auth)

            # WHEN: get_positions called
            positions = account.get_positions()

            # THEN: Returns empty list
            assert positions == []
            assert len(positions) == 0

    def test_fetch_account_balance_from_api(self):
        """
        T028: Test get_account_balance returns AccountBalance object.

        GIVEN: API returns account profile
        WHEN: get_account_balance called
        THEN: Returns AccountBalance with cash, equity, buying_power
        """
        from src.trading_bot.account.account_data import AccountData, AccountBalance

        with patch('robin_stocks.robinhood.account.load_account_profile') as mock_api:
            mock_api.return_value = {
                'cash': '5000.00',
                'equity': '12500.75',
                'buying_power': '10000.50'
            }
            mock_auth = Mock()

            account = AccountData(auth=mock_auth)

            # WHEN: get_account_balance called
            balance = account.get_account_balance()

            # THEN: Returns AccountBalance object
            assert isinstance(balance, AccountBalance)
            assert balance.cash == Decimal("5000.00")
            assert balance.equity == Decimal("12500.75")
            assert balance.buying_power == Decimal("10000.50")

    def test_fetch_day_trade_count_from_api(self):
        """
        T029: Test get_day_trade_count returns int (0-3).

        GIVEN: API returns day_trade_count
        WHEN: get_day_trade_count called
        THEN: Returns int value
        """
        from src.trading_bot.account.account_data import AccountData

        with patch('robin_stocks.robinhood.account.load_account_profile') as mock_api:
            mock_api.return_value = {
                'day_trade_count': '2',
                'buying_power': '10000.00'
            }
            mock_auth = Mock()

            account = AccountData(auth=mock_auth)

            # WHEN: get_day_trade_count called
            count = account.get_day_trade_count()

            # THEN: Returns int
            assert count == 2
            assert isinstance(count, int)

    def test_network_error_retries_with_backoff(self):
        """
        T030: Test network error triggers exponential backoff retry.

        GIVEN: 2 network errors, then success
        WHEN: get_buying_power called
        THEN: Retried 3 times with backoff delays
        """
        from src.trading_bot.account.account_data import AccountData

        with patch('robin_stocks.robinhood.account.load_account_profile') as mock_api:
            with patch('time.sleep') as mock_sleep:
                # GIVEN: 2 network errors, then success
                mock_api.side_effect = [
                    Exception("Network timeout"),
                    Exception("Network timeout"),
                    {'buying_power': '10000.50'}
                ]
                mock_auth = Mock()

                account = AccountData(auth=mock_auth)

                # WHEN: get_buying_power called (disable cache to force API call)
                result = account.get_buying_power(use_cache=False)

                # THEN: Retried 3 times, succeeded
                assert result == 10000.50
                assert mock_api.call_count == 3
                assert mock_sleep.call_count == 2  # Slept after 1st and 2nd attempt
                mock_sleep.assert_any_call(1.0)  # 1s after 1st failure
                mock_sleep.assert_any_call(2.0)  # 2s after 2nd failure

    def test_rate_limit_429_triggers_backoff(self):
        """
        T031: Test rate limit (429) triggers backoff.

        GIVEN: Rate limit error, then success
        WHEN: API call made
        THEN: Backoff applied and retry succeeds
        """
        from src.trading_bot.account.account_data import AccountData

        with patch('robin_stocks.robinhood.account.load_account_profile') as mock_api:
            with patch('time.sleep') as mock_sleep:
                # GIVEN: Rate limit, then success
                rate_limit_error = Exception("429 Too Many Requests")
                mock_api.side_effect = [
                    rate_limit_error,
                    {'buying_power': '10000.50'}
                ]
                mock_auth = Mock()

                account = AccountData(auth=mock_auth)

                # WHEN: get_buying_power called
                result = account.get_buying_power(use_cache=False)

                # THEN: Retry succeeded
                assert result == 10000.50
                assert mock_api.call_count == 2
                assert mock_sleep.call_count == 1

    def test_invalid_api_response_raises_error(self):
        """
        T032: Test invalid API response raises AccountDataError.

        GIVEN: Malformed API response
        WHEN: Fetch method called
        THEN: AccountDataError raised with clear message
        """
        from src.trading_bot.account.account_data import AccountData, AccountDataError

        with patch('robin_stocks.robinhood.account.load_account_profile') as mock_api:
            # GIVEN: Missing buying_power field
            mock_api.return_value = {'cash': '5000.00'}  # No buying_power
            mock_auth = Mock()

            account = AccountData(auth=mock_auth)

            # WHEN/THEN: AccountDataError raised
            with pytest.raises(AccountDataError, match="missing buying_power"):
                account.get_buying_power(use_cache=False)


class TestPLCalculations:
    """Test suite for profit/loss calculations."""
    pass


class TestErrorHandling:
    """Test suite for error handling and retry logic."""
    pass
