from technical_analyst.data.providers.symbols import (
    CRYPTO_SYMBOL_MAP,
    resolve_symbol,
)


def test_bitcoin_maps_to_usd_ticker():
    assert resolve_symbol("BTC") == "BTC-USD"


def test_lowercase_input_is_mapped():
    assert resolve_symbol("btc") == "BTC-USD"
    assert resolve_symbol("eth") == "ETH-USD"


def test_common_altcoins_map_to_usd_ticker():
    for symbol, ticker in CRYPTO_SYMBOL_MAP.items():
        assert resolve_symbol(symbol) == ticker
        assert ticker.endswith("-USD")


def test_unknown_symbol_passes_through():
    assert resolve_symbol("AAPL") == "AAPL"
    assert resolve_symbol("MSFT") == "MSFT"


def test_already_suffixed_ticker_passes_through():
    assert resolve_symbol("BTC-USD") == "BTC-USD"
    assert resolve_symbol("ETH-USD") == "ETH-USD"


def test_empty_string_passes_through():
    assert resolve_symbol("") == ""
