from app.services.opponent_service import classify_opponent, jam_call_strategy


def test_classify_nit():
    assert classify_opponent(pfr=0.08, aggression=0.15) == "NIT"


def test_classify_tag():
    assert classify_opponent(pfr=0.18, aggression=0.35) == "TAG"


def test_classify_lag():
    assert classify_opponent(pfr=0.30, aggression=0.60) == "LAG"


def test_classify_maniac():
    assert classify_opponent(pfr=0.50, aggression=0.90) == "MANIAC"


def test_jam_call_strategy_widens_for_lag():
    nit_strategy = jam_call_strategy("NIT")
    lag_strategy = jam_call_strategy("LAG")
    assert lag_strategy["call_jam_widen"] > nit_strategy["call_jam_widen"]
