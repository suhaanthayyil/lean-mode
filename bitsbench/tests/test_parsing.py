import pytest

from bitsbench.agents.llm import parse_predictions, parse_query, parse_rule
from bitsbench.domains import get_domain
from bitsbench.safe_eval import compile_expr


def test_parse_query_takes_last_line_and_strips_markup():
    d = get_domain("numbers")
    assert parse_query(d, "maybe QUERY: 3?\nQUERY: 12\nthinking...\n**QUERY:** `40`") == 40
    with pytest.raises(ValueError):
        parse_query(d, "QUERY: 400")
    with pytest.raises(ValueError):
        parse_query(d, "no query here")


@pytest.mark.parametrize("domain,text,expected", [
    ("boolean", "QUERY: 0110 1001", "01101001"),
    ("regular", "QUERY: `abba`", "abba"),
    ("lists", "QUERY: [3, 1, 4]", (3, 1, 4)),
])
def test_parse_query_per_domain(domain, text, expected):
    assert parse_query(get_domain(domain), text) == expected


def test_parse_predictions_binary_and_nested():
    nb = get_domain("numbers")
    out, ok = parse_predictions(nb, "blah PREDICTIONS: [true, False, 1, no]", 4)
    assert ok and out == [True, False, True, False]
    out, ok = parse_predictions(nb, "PREDICTIONS: [true, maybe]", 3)
    assert not ok and out == [True, None, None]
    ls = get_domain("lists")
    out, ok = parse_predictions(ls, "RULE: sort | take(2)\nPREDICTIONS: [[1, 2], [], [3]] trailing [x]", 3)
    assert ok and out == [(1, 2), (), (3,)]


def test_parse_rule():
    assert parse_rule("RULE: `x % 2 == 0`\nPREDICTIONS: []") == "x % 2 == 0"
    assert parse_rule("nothing") is None
    assert parse_rule("**RULE:** `(a|b)*`") == "(a|b)*"


@pytest.mark.parametrize("src", ["__import__('os')", "x.__class__", "(lambda: 1)()", "[c for c in 'ab']",
                                 "open('f')", "'a' * 10", "2 ** x"])
def test_safe_eval_rejects(src):
    with pytest.raises(ValueError):
        compile_expr(src, ["x"], {})


def test_rule_matching_accepts_equivalent_forms():
    nb = get_domain("numbers")
    sp = nb.space("L1")
    h = sp.sources.index("x % 2 == 0")
    assert nb.rule_matches("L1", "not (x % 2 == 1)", h)
    assert not nb.rule_matches("L1", "x % 4 == 0", h)
    rg = get_domain("regular")
    sp = rg.space("L1")
    ends_b = next(i for i in range(len(sp)) if all(sp.output(i, s) == s.endswith("b") for s in sp.pool))
    assert rg.rule_matches("L1", "(a|b)*b", ends_b)
    assert rg.rule_matches("L1", "DFA[start q0, accept {q1}; q0: a->q0 b->q1; q1: a->q0 b->q1]", ends_b)
