import pytest
import math
from mcp_server.stats import compute_disproportionality

def test_evans_signal_positive():
    """
    Hand-checked benchmark example:
    Drug target: a = 50, b = 950 (Total drug = 1,000)
    Other drugs: c = 100, d = 98,900 (Total other = 99,000)
    Total reports N = 100,000
    
    Rate drug = 50 / 1000 = 0.05
    Rate other = 100 / 99000 = 0.0010101
    PRR = 0.05 / 0.0010101 = 49.5
    
    ROR = (50 * 98900) / (950 * 100) = 4,945,000 / 95,000 = 52.0526
    
    Evans criteria:
    - a >= 3 (50 >= 3) -> True
    - PRR >= 2.0 (49.5 >= 2.0) -> True
    - chi_square >= 4.0 -> True
    """
    res = compute_disproportionality(a=50, b=950, c=100, d=98900)
    
    assert res["signal_flag"] is True
    assert res["a"] == 50
    assert pytest.approx(res["prr"], rel=1e-2) == 49.5
    assert pytest.approx(res["ror"], rel=1e-2) == 52.053
    assert res["chi_square"] > 500.0
    assert res["prr_ci_lower"] > 30.0
    assert res["ror_ci_lower"] > 35.0
    assert res["criteria_met"]["count_threshold"] is True
    assert res["criteria_met"]["prr_threshold"] is True
    assert res["criteria_met"]["chi_square_threshold"] is True

def test_evans_signal_negative_low_count():
    """
    Even with high PRR, if a < 3, Evans signal_flag must be False.
    """
    res = compute_disproportionality(a=2, b=10, c=1, d=5000)
    assert res["a"] == 2
    assert res["criteria_met"]["count_threshold"] is False
    assert res["signal_flag"] is False

def test_evans_signal_negative_low_prr():
    """
    If PRR < 2.0, signal_flag must be False.
    """
    # Equal proportions
    res = compute_disproportionality(a=100, b=900, c=1000, d=9000)
    assert res["a"] == 100
    assert pytest.approx(res["prr"], rel=1e-2) == 1.0
    assert res["criteria_met"]["prr_threshold"] is False
    assert res["signal_flag"] is False

def test_zero_division_guard():
    """Ensure no exceptions when contingency counts are zeros."""
    res = compute_disproportionality(a=0, b=0, c=0, d=0)
    assert res["signal_flag"] is False
    assert res["prr"] == 0.0
    assert res["ror"] == 0.0
    assert res["chi_square"] == 0.0

