from mt5_client import search_symbols, _category_from_name

CATALOG = [
    "AAPLm", "AMZNm", "MSFTm", "NVDAm", "TSLAm", "META",
    "EURUSDm", "GBPUSDm", "USDJPYm", "AUDUSDm",
    "XAUUSDm", "XAGUSDm", "USOILm", "UKOILm", "XNGUSDm",
    "BTCUSDm", "ETHUSDm", "SOLUSDm",
    "US500m", "US30m", "NAS100m", "DE30m", "JP225m",
]


def test_ticker_query():
    assert search_symbols("Apple", CATALOG)[0]["symbol"] == "AAPLm"


def test_currency_pair_with_slash():
    assert search_symbols("EUR/USD", CATALOG)[0]["symbol"] == "EURUSDm"


def test_currency_pair_no_slash():
    assert search_symbols("EURUSD", CATALOG)[0]["symbol"] == "EURUSDm"


def test_common_name_alias_gold():
    assert search_symbols("gold", CATALOG)[0]["symbol"] == "XAUUSDm"


def test_common_name_alias_oil():
    assert search_symbols("oil", CATALOG)[0]["symbol"] == "USOILm"


def test_common_name_alias_btc():
    assert search_symbols("bitcoin", CATALOG)[0]["symbol"] == "BTCUSDm"


def test_index_query():
    assert search_symbols("US500", CATALOG)[0]["symbol"] == "US500m"


def test_no_match_returns_empty():
    assert search_symbols("zzzzzqwerty", CATALOG) == []


def test_category_forex():
    assert _category_from_name("EURUSDm") == "Forex"


def test_category_stock():
    assert _category_from_name("AAPLm") == "Stocks"


def test_category_metal():
    assert _category_from_name("XAUUSDm") == "Metals"


def test_category_crypto():
    assert _category_from_name("BTCUSDm") == "Crypto"


def test_category_index():
    assert _category_from_name("US500m") == "Indices"


def test_category_energy():
    assert _category_from_name("USOILm") == "Energies"
