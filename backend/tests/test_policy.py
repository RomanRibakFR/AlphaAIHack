"""Примеры из docs/decision-policy.md, разделы 5.5, 6.2–6.4 и 8: лимит, подбор условий, LGD, класс и ставка."""
from app.decision import Request, grade_of, lgd_of, pd_max_of, pick_terms, rate_of
from app.policy import product


def terms(code, amount, term, receipts, existing, collateral=None):
    req = Request(code, amount, term, is_legal=True, collateral_value=collateral, reviewed_before=False)
    return pick_terms(req, product(code), receipts, existing)


def test_rate_is_key_plus_margin_plus_expected_loss():
    wc = product("WORKING_CAPITAL")
    assert rate_of(0.0772, wc, 0.40) == 0.181  # 14% + 1% + 7,72% × 40% (C03)
    assert rate_of(0.005, wc, 0.40) == 0.152
    assert rate_of(0.0062, product("INVESTMENT"), 0.20) == 0.151  # полный залог, LGD 20% (C07)
    assert rate_of(0.30, product("OVERDRAFT"), 0.40) == 0.22  # упёрлись в потолок продукта


def test_lgd_by_basel_foundation_approach():
    assert lgd_of(product("WORKING_CAPITAL"), 3_000_000, None) == 0.40
    assert lgd_of(product("INVESTMENT"), 20_000_000, 35_000_000) == 0.20  # 60% от 35 млн покрывают всю сумму
    assert round(lgd_of(product("INVESTMENT"), 30_000_000, 25_000_000), 4) == 0.30  # покрыто 15 из 30 млн


def test_grade_boundaries_and_product_pd_max():
    assert round(pd_max_of(product("WORKING_CAPITAL"), 0.40), 4) == 0.25
    assert round(pd_max_of(product("OVERDRAFT"), 0.40), 4) == 0.175
    assert round(pd_max_of(product("INVESTMENT"), 0.20), 4) == 0.35
    assert [grade_of(pd, 0.25) for pd in (0.0015, 0.0772, 0.1582, 0.4035)] == ["A", "B", "C", "D"]
    assert grade_of(0.20, 0.175) == "D"  # тот же риск по овердрафту ставкой уже не покрыть


def test_example_c01_as_requested():
    (kind, amount, term), _, _, _ = terms("WORKING_CAPITAL", 3_000_000, 24, 2_500_000, 100_000)
    assert (kind, amount, term) == ("AS_REQUESTED", 3_000_000, 24)


def test_example_c03_longer_term_keeps_amount():
    offer, limit, binding, _ = terms("WORKING_CAPITAL", 8_000_000, 18, 4_000_000, 150_000)
    assert offer == ("TERM_EXTENDED", 8_000_000, 30)
    assert (limit, binding) == (5_950_000, "new_payment")


def test_example_c08_overdraft_limited_by_turnover():
    offer, _, binding, _ = terms("OVERDRAFT", 3_000_000, 12, 4_000_000, 0)
    assert offer == ("AMOUNT_REDUCED", 2_000_000, 12)
    assert binding == "turnover_share"


def test_example_c09_nothing_to_offer():
    offer, limit, binding, _ = terms("WORKING_CAPITAL", 10_000_000, 24, 1_000_000, 180_000)
    assert offer is None
    assert (limit, binding) == (0, "total_debt_service")  # 18% уже больше допустимых 17%


def test_collateral_caps_investment():
    offer, _, binding, _ = terms("INVESTMENT", 30_000_000, 84, 10_000_000, 0, collateral=35_000_000)
    assert binding == "collateral"
    assert offer[1] == 21_000_000  # 60% залога
