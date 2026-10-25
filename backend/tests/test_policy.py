"""Примеры из docs/decision-policy.md, раздел 8: PD задан вручную, сверяем ставку, сумму и срок."""
from app.decision import Request, make_offer, rate_of
from app.policy import product


def offer(code, amount, term, turnover, existing, pd, collateral=None):
    prod = product(code)
    req = Request(code, amount, term, is_legal=True, collateral_value=collateral, reviewed_before=False)
    return make_offer(req, prod, rate_of(pd, prod), turnover, existing)


def test_rate_is_key_plus_margin_plus_expected_loss():
    assert rate_of(0.04, product("WORKING_CAPITAL")) == 0.174  # 14% + 1% + 4% × 60%
    assert rate_of(0.03, product("INVESTMENT")) == 0.159  # с залогом LGD 30%
    assert rate_of(0.20, product("OVERDRAFT")) == 0.22  # упёрлись в потолок продукта


def test_example_1_as_requested():
    o, _, _ = offer("WORKING_CAPITAL", 3_000_000, 24, 2_500_000, 100_000, 0.02)
    assert (o.kind, o.amount, o.term_months, o.rate, o.monthly_payment) == ("AS_REQUESTED", 3_000_000, 24, 0.162, 147_176)
    assert o.conditions == ["Поручительство собственника бизнеса"]  # беззалоговый кредит юрлицу


def test_example_2_longer_term_keeps_amount():
    o, _, _ = offer("WORKING_CAPITAL", 8_000_000, 18, 3_000_000, 150_000, 0.04)
    assert (o.kind, o.amount, o.term_months, o.monthly_payment) == ("TERM_EXTENDED", 8_000_000, 24, 397_077)


def test_example_3_smaller_amount_with_alternative():
    o, limit, binding = offer("WORKING_CAPITAL", 6_000_000, 24, 1_500_000, 120_000, 0.05)
    assert (o.kind, o.amount, o.rate, binding) == ("AMOUNT_REDUCED", 3_600_000, 0.18, "payment_capacity")
    assert o.alternatives[0]["term_months"] == 36
    assert 4_960_000 <= o.alternatives[0]["amount"] <= 4_980_000
    assert "платежи по текущим кредитам" in o.reason


def test_example_8_overdraft_limited_by_turnover():
    o, _, binding = offer("OVERDRAFT", 3_000_000, 12, 4_000_000, 0, 0.03)
    assert (o.amount, o.rate, binding) == (2_000_000, 0.168, "turnover_share")
    assert o.monthly_payment == 28_000  # по овердрафту — только проценты


def test_example_9_nothing_to_offer():
    o, limit, _ = offer("WORKING_CAPITAL", 10_000_000, 24, 1_000_000, 180_000, 0.06)
    assert o is None
    assert limit < 3_000_000  # меньше 30% запрошенного


def test_collateral_caps_investment():
    o, _, binding = offer("INVESTMENT", 30_000_000, 84, 10_000_000, 0, 0.03, collateral=35_000_000)
    assert binding == "ltv"
    assert o.amount == 24_500_000  # 70% залога
