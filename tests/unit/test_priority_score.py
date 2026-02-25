import time

from courseflow.main import calculate_score


def test_priority_affects_score():
    base = time.time()

    low = calculate_score(priority=0, base_time=base)
    high = calculate_score(priority=10, base_time=base)

    assert high < low
