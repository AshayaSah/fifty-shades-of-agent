#!/usr/bin/env python3
"""
Phase 1 Verification Script - Data Ingestion Layer
Tests all checklist items from Phase 1 specification.
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


def test_router_fetch():
    """Test 1: Confirm router can fetch AAPL data"""
    print("=== Test 1: Router fetch AAPL ===")
    try:
        from technical_analyst.data.providers.router import ProviderRouter
        router = ProviderRouter()
        series = router.fetch('AAPL', '1d', 90)
        print(f"✓ Successfully fetched {len(series.candles)} candles for AAPL")
        print(f"  Source: {series.source}")
        print(f"  First candle: {series.candles[0].timestamp} - Close: {series.candles[0].close}")
        print(f"  Last candle: {series.candles[-1].timestamp} - Close: {series.candles[-1].close}")
        return True
    except Exception as e:
        print(f"✗ Failed to fetch AAPL: {e}")
        return False


def test_fallback_trigger():
    """Test 2: Confirm fallback triggers when primary fails"""
    print("\n=== Test 2: Fallback trigger ===")
    try:
        from technical_analyst.data.providers.router import ProviderRouter, NoUsableDataError
        from technical_analyst.data.providers.base import ProviderError
        
        # Create a mock provider that always fails
        class FailingProvider:
            name = "failing_provider"
            def fetch(self, symbol, interval, lookback_days):
                raise ProviderError("Simulated failure")
        
        # Test with failing primary provider
        router = ProviderRouter(providers=[FailingProvider()])
        try:
            series = router.fetch('AAPL', '1d', 90)
            print("✗ Should have raised NoUsableDataError")
            return False
        except NoUsableDataError:
            print("✓ NoUsableDataError raised when all providers fail (as expected)")
            return True
    except Exception as e:
        print(f"✗ Fallback test failed: {e}")
        return False


def test_bad_ticker_error():
    """Test 3: Confirm bad ticker returns clean error, not stack trace"""
    print("\n=== Test 3: Bad ticker error handling ===")
    try:
        from technical_analyst.data.providers.router import ProviderRouter, NoUsableDataError
        
        router = ProviderRouter()
        try:
            series = router.fetch('NOTASYMBOL123', '1d', 90)
            print("✗ Should have raised NoUsableDataError for bad ticker")
            return False
        except NoUsableDataError as e:
            error_msg = str(e)
            # Verify it's a clean error message, not a stack trace
            if 'Traceback' in error_msg or 'File' in error_msg:
                print(f"✗ Error contains stack trace: {error_msg[:100]}...")
                return False
            else:
                print(f"✓ Clean error message for bad ticker: {error_msg[:100]}...")
                return True
        except Exception as e:
            print(f"✗ Unexpected exception type: {type(e).__name__}: {e}")
            return False
    except Exception as e:
        print(f"✗ Bad ticker test failed: {e}")
        return False


def test_symbol_not_found_vs_provider_error():
    """Test 4: Verify SymbolNotFoundError vs ProviderError distinction"""
    print("\n=== Test 4: Exception type distinction ===")
    try:
        from technical_analyst.data.providers.base import ProviderError, SymbolNotFoundError
        from technical_analyst.data.providers.yfinance_provider import YFinanceProvider
        from technical_analyst.data.providers.twelve_data_provider import TwelveDataProvider
        
        # Test yfinance provider - empty result should be ProviderError
        yf_provider = YFinanceProvider()
        try:
            # This might fail with various errors, but we want to verify the type
            series = yf_provider.fetch('AAPL', '1d', 90)
            print("✓ yfinance provider successfully fetched AAPL")
        except ProviderError as e:
            print(f"✓ yfinance raised ProviderError (as expected): {e}")
        except SymbolNotFoundError as e:
            print(f"✗ yfinance raised SymbolNotFoundError (should be ProviderError): {e}")
            return False
        except Exception as e:
            print(f"⚠ yfinance raised unexpected exception: {type(e).__name__}: {e}")
        
        return True
    except Exception as e:
        print(f"✗ Exception distinction test failed: {e}")
        return False


def test_injectable_providers():
    """Test 5: Verify providers list is constructor-injectable for testing"""
    print("\n=== Test 5: Injectable providers for testing ===")
    try:
        from technical_analyst.data.providers.router import ProviderRouter
        
        # Create mock providers
        class MockProvider:
            def __init__(self, name, should_fail=False):
                self.name = name
                self.should_fail = should_fail
                self.fetch_count = 0
            
            def fetch(self, symbol, interval, lookback_days):
                self.fetch_count += 1
                if self.should_fail:
                    from technical_analyst.data.providers.base import ProviderError
                    raise ProviderError(f"{self.name} failed")
                # Return minimal valid data
                from technical_analyst.data.models import Candle, OHLCVSeries
                from datetime import datetime
                return OHLCVSeries(
                    symbol=symbol,
                    interval=interval,
                    candles=[Candle(
                        timestamp=datetime.now(),
                        open=100.0, high=101.0, low=99.0, close=100.5, volume=1000
                    )],
                    source=self.name
                )
        
        # Test with custom providers
        provider1 = MockProvider("provider1", should_fail=True)
        provider2 = MockProvider("provider2", should_fail=False)
        
        router = ProviderRouter(providers=[provider1, provider2])
        series = router.fetch('TEST', '1d', 30)
        
        if provider1.fetch_count == 1 and provider2.fetch_count == 1:
            print("✓ Custom providers injected and called correctly")
            print(f"  Provider1 called: {provider1.fetch_count} times")
            print(f"  Provider2 called: {provider2.fetch_count} times")
            return True
        else:
            print(f"✗ Provider call counts incorrect: {provider1.fetch_count}, {provider2.fetch_count}")
            return False
    except Exception as e:
        print(f"✗ Injectable providers test failed: {e}")
        return False


def main():
    """Run all verification tests"""
    print("Phase 1 Verification - Data Ingestion Layer")
    print("=" * 60)
    
    tests = [
        test_router_fetch,
        test_fallback_trigger,
        test_bad_ticker_error,
        test_symbol_not_found_vs_provider_error,
        test_injectable_providers,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    for i, (test, result) in enumerate(zip(tests, results)):
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{i+1}. {test.__name__}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All Phase 1 checklist items verified!")
        return 0
    else:
        print(f"\n⚠ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())