from sizing import calculate_lot_size


def test_basic_lot_size():
    # equity=10000, risk=1%, SL=50 pips, pip_value=10
    # risk_amount = 10000 * 1 / 100 = 100
    # lot_size = 100 / (50 * 10) = 0.20
    assert calculate_lot_size(10000, 1, 50, 10) == 0.20


def test_higher_risk():
    # equity=5000, risk=2%, SL=25 pips, pip_value=10
    # risk_amount = 5000 * 2 / 100 = 100
    # lot_size = 100 / (25 * 10) = 0.40
    assert calculate_lot_size(5000, 2, 25, 10) == 0.40


def test_small_account():
    # equity=1000, risk=0.5%, SL=100 pips, pip_value=10
    # risk_amount = 1000 * 0.5 / 100 = 5
    # lot_size = 5 / (100 * 10) = 0.005 -> rounds to 0.01
    assert calculate_lot_size(1000, 0.5, 100, 10) == 0.01


def test_zero_sl_returns_zero():
    assert calculate_lot_size(10000, 1, 0, 10) == 0.0


def test_zero_pip_value_returns_zero():
    assert calculate_lot_size(10000, 1, 50, 0) == 0.0
