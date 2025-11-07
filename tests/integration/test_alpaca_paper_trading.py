"""
Comprehensive Alpaca Paper Trading API Test Suite

Tests all major Alpaca API endpoints with paper trading account:
- Account information
- Market data (quotes, bars, news)
- Order management (create, list, cancel)
- Position management
- Trading operations
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

load_dotenv()

# Configure UTF-8 output for Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


class AlpacaPaperTradingTester:
    """Test Alpaca Paper Trading API functionality"""

    def __init__(self):
        self.api_key = os.getenv("ALPACA_API_KEY")
        self.secret_key = os.getenv("ALPACA_SECRET_KEY")
        self.base_url = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
        self.data_url = "https://data.alpaca.markets"

        self.results = {
            "passed": [],
            "failed": [],
            "warnings": []
        }

        # Validate credentials
        if not self.api_key or not self.secret_key:
            raise ValueError(
                "Missing Alpaca credentials. Set ALPACA_API_KEY and ALPACA_SECRET_KEY in .env"
            )

        print(f"🔑 Using credentials: {self.api_key[:8]}...")
        print(f"🌐 Trading API: {self.base_url}")
        print(f"📊 Data API: {self.data_url}")
        print()

    def _get_headers(self, use_data_api=False):
        """Get request headers with authentication"""
        return {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.secret_key,
            "accept": "application/json"
        }

    def _make_request(self, method, url, headers, **kwargs):
        """Make HTTP request with error handling"""
        import requests

        try:
            response = requests.request(method, url, headers=headers, **kwargs)
            return response
        except Exception as e:
            return None

    def test_account_info(self):
        """Test: Get account information"""
        print("📋 Test 1: Account Information")
        print("-" * 60)

        import requests

        url = f"{self.base_url}/v2/account"
        headers = self._get_headers()

        try:
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Account Status: {data.get('status')}")
                print(f"✅ Account Number: {data.get('account_number')}")
                print(f"✅ Buying Power: ${float(data.get('buying_power', 0)):,.2f}")
                print(f"✅ Cash: ${float(data.get('cash', 0)):,.2f}")
                print(f"✅ Portfolio Value: ${float(data.get('portfolio_value', 0)):,.2f}")
                print(f"✅ Pattern Day Trader: {data.get('pattern_day_trader')}")
                print(f"✅ Trading Blocked: {data.get('trading_blocked')}")
                print(f"✅ Account Blocked: {data.get('account_blocked')}")

                self.results["passed"].append("Account Information")
                return True
            else:
                print(f"❌ Failed: {response.status_code} - {response.text}")
                self.results["failed"].append(f"Account Information ({response.status_code})")
                return False

        except Exception as e:
            print(f"❌ Error: {e}")
            self.results["failed"].append(f"Account Information (Exception: {e})")
            return False

    def test_positions(self):
        """Test: Get current positions"""
        print("\n📊 Test 2: Current Positions")
        print("-" * 60)

        import requests

        url = f"{self.base_url}/v2/positions"
        headers = self._get_headers()

        try:
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                positions = response.json()
                print(f"✅ Open Positions: {len(positions)}")

                if positions:
                    for pos in positions[:5]:  # Show first 5
                        print(f"  • {pos.get('symbol')}: {pos.get('qty')} shares @ ${pos.get('avg_entry_price')}")
                        print(f"    Current: ${pos.get('current_price')} | P&L: ${pos.get('unrealized_pl')}")
                else:
                    print("  ℹ️  No open positions (expected for new paper account)")

                self.results["passed"].append("Positions")
                return True
            else:
                print(f"❌ Failed: {response.status_code} - {response.text}")
                self.results["failed"].append(f"Positions ({response.status_code})")
                return False

        except Exception as e:
            print(f"❌ Error: {e}")
            self.results["failed"].append(f"Positions (Exception: {e})")
            return False

    def test_orders_list(self):
        """Test: List orders"""
        print("\n📝 Test 3: Order History")
        print("-" * 60)

        import requests

        url = f"{self.base_url}/v2/orders"
        headers = self._get_headers()
        params = {"limit": 10, "status": "all"}

        try:
            response = requests.get(url, headers=headers, params=params)

            if response.status_code == 200:
                orders = response.json()
                print(f"✅ Recent Orders: {len(orders)}")

                if orders:
                    for order in orders[:5]:
                        print(f"  • {order.get('symbol')}: {order.get('side')} {order.get('qty')} @ {order.get('type')}")
                        print(f"    Status: {order.get('status')} | Filled: {order.get('filled_qty')}/{order.get('qty')}")
                else:
                    print("  ℹ️  No orders yet (expected for new paper account)")

                self.results["passed"].append("Order History")
                return True
            else:
                print(f"❌ Failed: {response.status_code} - {response.text}")
                self.results["failed"].append(f"Order History ({response.status_code})")
                return False

        except Exception as e:
            print(f"❌ Error: {e}")
            self.results["failed"].append(f"Order History (Exception: {e})")
            return False

    def test_market_data_quote(self):
        """Test: Get real-time quote"""
        print("\n💰 Test 4: Market Data - Latest Quote")
        print("-" * 60)

        import requests

        symbol = "AAPL"
        url = f"{self.data_url}/v2/stocks/{symbol}/quotes/latest"
        headers = self._get_headers(use_data_api=True)

        try:
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                quote = data.get("quote", {})
                print(f"✅ Latest Quote for {symbol}:")
                print(f"  • Bid: ${quote.get('bp')} x {quote.get('bs')}")
                print(f"  • Ask: ${quote.get('ap')} x {quote.get('as')}")
                print(f"  • Timestamp: {quote.get('t')}")

                self.results["passed"].append("Market Data - Quote")
                return True
            else:
                print(f"❌ Failed: {response.status_code} - {response.text}")
                self.results["failed"].append(f"Market Data - Quote ({response.status_code})")
                return False

        except Exception as e:
            print(f"❌ Error: {e}")
            self.results["failed"].append(f"Market Data - Quote (Exception: {e})")
            return False

    def test_market_data_bars(self):
        """Test: Get historical bars"""
        print("\n📈 Test 5: Market Data - Historical Bars")
        print("-" * 60)

        import requests

        symbol = "AAPL"
        end_date = datetime.now()
        start_date = end_date - timedelta(days=5)

        url = f"{self.data_url}/v2/stocks/{symbol}/bars"
        headers = self._get_headers(use_data_api=True)
        params = {
            "start": start_date.strftime("%Y-%m-%d"),
            "end": end_date.strftime("%Y-%m-%d"),
            "timeframe": "1Day",
            "limit": 5
        }

        try:
            response = requests.get(url, headers=headers, params=params)

            if response.status_code == 200:
                data = response.json()
                bars = data.get("bars", [])
                print(f"✅ Retrieved {len(bars)} bars for {symbol}:")

                for bar in bars[:3]:
                    print(f"  • {bar.get('t')[:10]}: O=${bar.get('o')} H=${bar.get('h')} L=${bar.get('l')} C=${bar.get('c')} V={bar.get('v'):,}")

                self.results["passed"].append("Market Data - Bars")
                return True
            else:
                print(f"❌ Failed: {response.status_code} - {response.text}")
                self.results["failed"].append(f"Market Data - Bars ({response.status_code})")
                return False

        except Exception as e:
            print(f"❌ Error: {e}")
            self.results["failed"].append(f"Market Data - Bars (Exception: {e})")
            return False

    def test_market_data_news(self):
        """Test: Get news (used by CatalystDetector)"""
        print("\n📰 Test 6: Market Data - News API")
        print("-" * 60)

        import requests

        url = f"{self.data_url}/v1beta1/news"
        headers = self._get_headers(use_data_api=True)
        params = {
            "symbols": "AAPL,TSLA",
            "limit": 5,
            "sort": "desc"
        }

        try:
            response = requests.get(url, headers=headers, params=params)

            if response.status_code == 200:
                data = response.json()
                news_items = data.get("news", [])
                print(f"✅ Retrieved {len(news_items)} news articles:")

                for item in news_items[:3]:
                    print(f"  • {item.get('headline')[:60]}...")
                    print(f"    Symbols: {', '.join(item.get('symbols', []))}")
                    print(f"    Source: {item.get('source')}")

                self.results["passed"].append("Market Data - News")
                return True
            else:
                print(f"❌ Failed: {response.status_code} - {response.text}")
                self.results["failed"].append(f"Market Data - News ({response.status_code})")
                return False

        except Exception as e:
            print(f"❌ Error: {e}")
            self.results["failed"].append(f"Market Data - News (Exception: {e})")
            return False

    def test_place_order(self):
        """Test: Place a test order (market buy)"""
        print("\n🛒 Test 7: Place Test Order")
        print("-" * 60)

        import requests

        url = f"{self.base_url}/v2/orders"
        headers = self._get_headers()

        # Small test order
        order_data = {
            "symbol": "AAPL",
            "qty": 1,
            "side": "buy",
            "type": "market",
            "time_in_force": "day"
        }

        print(f"Attempting to place order: BUY 1 AAPL @ MARKET")

        try:
            response = requests.post(url, headers=headers, json=order_data)

            if response.status_code in [200, 201]:
                data = response.json()
                print(f"✅ Order placed successfully!")
                print(f"  • Order ID: {data.get('id')}")
                print(f"  • Symbol: {data.get('symbol')}")
                print(f"  • Side: {data.get('side')}")
                print(f"  • Qty: {data.get('qty')}")
                print(f"  • Type: {data.get('type')}")
                print(f"  • Status: {data.get('status')}")

                self.results["passed"].append("Place Order")
                return data.get('id')  # Return order ID for cancellation test
            else:
                print(f"❌ Failed: {response.status_code} - {response.text}")
                self.results["failed"].append(f"Place Order ({response.status_code})")
                return None

        except Exception as e:
            print(f"❌ Error: {e}")
            self.results["failed"].append(f"Place Order (Exception: {e})")
            return None

    def test_cancel_order(self, order_id):
        """Test: Cancel an order"""
        print("\n❌ Test 8: Cancel Order")
        print("-" * 60)

        if not order_id:
            print("⚠️  Skipped: No order ID from previous test")
            self.results["warnings"].append("Cancel Order (No order to cancel)")
            return False

        import requests
        import time

        # Wait a moment to ensure order is processed
        time.sleep(2)

        url = f"{self.base_url}/v2/orders/{order_id}"
        headers = self._get_headers()

        try:
            response = requests.delete(url, headers=headers)

            if response.status_code in [200, 204]:
                print(f"✅ Order {order_id} cancelled successfully")
                self.results["passed"].append("Cancel Order")
                return True
            elif response.status_code == 422:
                print(f"⚠️  Order already filled/cancelled (status 422)")
                self.results["warnings"].append("Cancel Order (Already filled)")
                return True
            else:
                print(f"❌ Failed: {response.status_code} - {response.text}")
                self.results["failed"].append(f"Cancel Order ({response.status_code})")
                return False

        except Exception as e:
            print(f"❌ Error: {e}")
            self.results["failed"].append(f"Cancel Order (Exception: {e})")
            return False

    def test_clock(self):
        """Test: Get market clock"""
        print("\n🕐 Test 9: Market Clock")
        print("-" * 60)

        import requests

        url = f"{self.base_url}/v2/clock"
        headers = self._get_headers()

        try:
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Market Clock:")
                print(f"  • Is Open: {data.get('is_open')}")
                print(f"  • Timestamp: {data.get('timestamp')}")
                print(f"  • Next Open: {data.get('next_open')}")
                print(f"  • Next Close: {data.get('next_close')}")

                self.results["passed"].append("Market Clock")
                return True
            else:
                print(f"❌ Failed: {response.status_code} - {response.text}")
                self.results["failed"].append(f"Market Clock ({response.status_code})")
                return False

        except Exception as e:
            print(f"❌ Error: {e}")
            self.results["failed"].append(f"Market Clock (Exception: {e})")
            return False

    def test_catalyst_detector(self):
        """Test: CatalystDetector integration"""
        print("\n🔍 Test 10: CatalystDetector Integration")
        print("-" * 60)

        try:
            import asyncio
            from trading_bot.momentum.catalyst_detector import CatalystDetector
            from trading_bot.momentum.config import MomentumConfig

            # Create config and detector
            config = MomentumConfig.from_env()
            detector = CatalystDetector(config)

            # Test scan method (async)
            print("Testing scan() with sample symbols...")

            async def run_scan():
                return await detector.scan(["AAPL", "TSLA", "NVDA"])

            signals = asyncio.run(run_scan())

            print(f"✅ CatalystDetector working!")
            print(f"  • Detected {len(signals)} momentum signals")

            if signals:
                for signal in signals[:3]:
                    print(f"  • {signal.symbol}: Type={signal.signal_type.value}, Strength={signal.strength:.1f}")
                    if hasattr(signal, 'catalyst_type') and signal.catalyst_type:
                        print(f"    Catalyst: {signal.catalyst_type.value}")
            else:
                print("  ℹ️  No signals detected (normal if no strong catalysts)")

            self.results["passed"].append("CatalystDetector Integration")
            return True

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            print(traceback.format_exc())
            self.results["failed"].append(f"CatalystDetector Integration (Exception: {e})")
            return False

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)

        total_tests = len(self.results["passed"]) + len(self.results["failed"]) + len(self.results["warnings"])

        print(f"\n✅ Passed: {len(self.results['passed'])}/{total_tests}")
        for test in self.results["passed"]:
            print(f"  • {test}")

        if self.results["warnings"]:
            print(f"\n⚠️  Warnings: {len(self.results['warnings'])}")
            for test in self.results["warnings"]:
                print(f"  • {test}")

        if self.results["failed"]:
            print(f"\n❌ Failed: {len(self.results['failed'])}")
            for test in self.results["failed"]:
                print(f"  • {test}")
        else:
            print("\n🎉 All tests passed!")

        print("\n" + "=" * 60)

    def run_all_tests(self):
        """Run all tests in sequence"""
        print("=" * 60)
        print("🚀 ALPACA PAPER TRADING API TEST SUITE")
        print("=" * 60)
        print()

        # Run tests
        self.test_account_info()
        self.test_positions()
        self.test_orders_list()
        self.test_market_data_quote()
        self.test_market_data_bars()
        self.test_market_data_news()

        # Order placement and cancellation
        order_id = self.test_place_order()
        self.test_cancel_order(order_id)

        self.test_clock()
        self.test_catalyst_detector()

        # Print summary
        self.print_summary()


if __name__ == "__main__":
    try:
        tester = AlpacaPaperTradingTester()
        tester.run_all_tests()
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
