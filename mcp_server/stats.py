import math
from typing import Dict, Any
from mcp_server.constants import DISCLAIMER, current_iso_timestamp

def compute_disproportionality(a: int, b: int, c: int, d: int) -> Dict[str, Any]:
    """
    Compute disproportionality metrics (PRR, ROR, 95% CIs, Chi-Square) and
    evaluate the Evans et al. (2001) criteria for signal detection.
    
    2x2 Contingency Table:
                     Target Reaction      Other Reactions      Total
    Target Drug            a                    b              a + b
    Other Drugs            c                    d              c + d
    Total                a + c                b + d              N
    
    Evans Criteria for a signal:
    - PRR >= 2.0
    - a >= 3
    - chi_square >= 4.0
    """
    a = int(a)
    b = int(b)
    c = int(c)
    d = int(d)
    
    n_drug = a + b
    n_other = c + d
    n_reaction = a + c
    n_none = b + d
    n_total = a + b + c + d
    
    timestamp = current_iso_timestamp()

    if n_drug <= 0 or n_other <= 0 or n_reaction <= 0 or n_none <= 0 or a < 0 or b < 0 or c < 0 or d < 0:
        return {
            "a": a,
            "b": b,
            "c": c,
            "d": d,
            "prr": 0.0,
            "prr_ci_lower": 0.0,
            "prr_ci_upper": 0.0,
            "ror": 0.0,
            "ror_ci_lower": 0.0,
            "ror_ci_upper": 0.0,
            "chi_square": 0.0,
            "chi_square_yates": 0.0,
            "signal_flag": False,
            "criteria_met": {
                "count_threshold": bool(a >= 3),
                "prr_threshold": False,
                "chi_square_threshold": False
            },
            "source": "Formula: Evans et al. (2001) Pharmacovigilance criteria",
            "data_source": "Deterministic Local Python Math",
            "retrieved_at": timestamp,
            "disclaimer": DISCLAIMER
        }

    # 1. Proportional Reporting Ratio (PRR)
    # PRR = (a / (a + b)) / (c / (c + d))
    rate_drug = a / n_drug
    rate_other = c / n_other if n_other > 0 else 0.0
    
    if rate_other > 0 and rate_drug > 0:
        prr = rate_drug / rate_other
        # SE(ln(PRR)) = sqrt(1/a - 1/(a+b) + 1/c - 1/(c+d))
        var_prr = (1.0 / a) - (1.0 / n_drug) + (1.0 / c) - (1.0 / n_other)
        se_prr = math.sqrt(max(0.0, var_prr))
        prr_ci_lower = math.exp(math.log(prr) - 1.96 * se_prr)
        prr_ci_upper = math.exp(math.log(prr) + 1.96 * se_prr)
    else:
        prr = 0.0
        prr_ci_lower = 0.0
        prr_ci_upper = 0.0

    # 2. Reporting Odds Ratio (ROR)
    # ROR = (a / b) / (c / d) = (a * d) / (b * c)
    if b > 0 and c > 0 and a > 0 and d > 0:
        ror = (a * d) / (b * c)
        var_ror = (1.0 / a) + (1.0 / b) + (1.0 / c) + (1.0 / d)
        se_ror = math.sqrt(var_ror)
        ror_ci_lower = math.exp(math.log(ror) - 1.96 * se_ror)
        ror_ci_upper = math.exp(math.log(ror) + 1.96 * se_ror)
    else:
        ror = 0.0
        ror_ci_lower = 0.0
        ror_ci_upper = 0.0

    # 3. Chi-square (Pearson and with Yates' continuity correction)
    # Pearson chi^2 = N * (a*d - b*c)^2 / ((a+b)*(c+d)*(a+c)*(b+d))
    denom = float(n_drug) * float(n_other) * float(n_reaction) * float(n_none)
    if denom > 0:
        ad_bc = abs(a * d - b * c)
        chi_square = (float(n_total) * (ad_bc ** 2)) / denom
        
        # Yates' corrected chi^2
        yates_diff = max(0.0, ad_bc - (n_total / 2.0))
        chi_square_yates = (float(n_total) * (yates_diff ** 2)) / denom
    else:
        chi_square = 0.0
        chi_square_yates = 0.0

    # Evans Criteria: PRR >= 2, a >= 3, chi_square >= 4
    count_ok = bool(a >= 3)
    prr_ok = bool(prr >= 2.0)
    chi_ok = bool(chi_square_yates >= 4.0 or chi_square >= 4.0)
    signal_flag = count_ok and prr_ok and chi_ok

    return {
        "a": a,
        "b": b,
        "c": c,
        "d": d,
        "prr": round(prr, 3),
        "prr_ci_lower": round(prr_ci_lower, 3),
        "prr_ci_upper": round(prr_ci_upper, 3),
        "ror": round(ror, 3),
        "ror_ci_lower": round(ror_ci_lower, 3),
        "ror_ci_upper": round(ror_ci_upper, 3),
        "chi_square": round(chi_square, 3),
        "chi_square_yates": round(chi_square_yates, 3),
        "signal_flag": signal_flag,
        "criteria_met": {
            "count_threshold": count_ok,
            "prr_threshold": prr_ok,
            "chi_square_threshold": chi_ok
        },
        "source": "Formula: Evans SJ et al. (2001) Pharmacoepidemiol Drug Saf 10(6):483-6",
        "data_source": "Deterministic Local Python Math",
        "retrieved_at": timestamp,
        "disclaimer": DISCLAIMER
    }
