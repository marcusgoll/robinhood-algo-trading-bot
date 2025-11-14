"""
Quick test script to verify Alpaca production URL accessibility

Run this to verify all Alpaca API endpoints are accessible.
"""

import httpx
import sys


def test_url(url: str, name: str) -> bool:
    """Test if URL is accessible via DNS and responds."""
    print(f"\nTesting {name}...")
    print(f"  URL: {url}")

    try:
        with httpx.Client(timeout=5.0, follow_redirects=True) as client:
            response = client.get(url)

            # Any response (even 401 Unauthorized) means server is reachable
            if response.status_code in [200, 401, 403, 404]:
                print(f"  ✅ Accessible (HTTP {response.status_code})")
                return True
            else:
                print(f"  ⚠️  Unexpected status: HTTP {response.status_code}")
                return False

    except httpx.TimeoutException:
        print(f"  ❌ Timeout - server not responding")
        return False

    except httpx.ConnectError as e:
        print(f"  ❌ Connection failed - DNS or network issue: {e}")
        return False

    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def main():
    """Test all Alpaca production URLs."""
    print("=" * 60)
    print("Alpaca Production URL Accessibility Test")
    print("=" * 60)

    endpoints = {
        "Market Data API (News)": "https://data.alpaca.markets/v1beta1/news",
        "Market Data API (Root)": "https://data.alpaca.markets",
        "Trading API (Paper)": "https://paper-api.alpaca.markets",
        "Trading API (Live)": "https://api.alpaca.markets",
    }

    results = {}
    for name, url in endpoints.items():
        results[name] = test_url(url, name)

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    all_pass = True
    for name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")
        if not success:
            all_pass = False

    print("=" * 60)

    if all_pass:
        print("\n✅ All production URLs are accessible!")
        return 0
    else:
        print("\n❌ Some URLs are not accessible - check network or DNS")
        return 1


if __name__ == "__main__":
    sys.exit(main())
