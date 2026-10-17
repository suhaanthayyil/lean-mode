import numpy as np
import pytest

from bitsbench.domains import all_configs, get_domain
from bitsbench.space import Posterior

# Regression guard: changing a hypothesis class changes every score, so sizes are pinned.
EXPECTED_SIZES = {
    ("numbers", "L1"): 194, ("numbers", "L2"): 17930,
    ("boolean", "L1"): 1136, ("boolean", "L2"): 11944, ("boolean", "L3"): 312104,
    ("regular", "L1"): 864, ("regular", "L2"): 48350,
    ("lists", "L1"): 26, ("lists", "L2"): 442, ("lists", "L3"): 5796,
}


@pytest.mark.parametrize("domain,level", all_configs())
def test_space_size_and_uniqueness(domain, level):
    sp = get_domain(domain).space(level)
    assert len(sp) == EXPECTED_SIZES[(domain, level)]
    assert len(np.unique(sp.table, axis=0)) == len(sp), "hypotheses must be semantically distinct"
    if sp.binary:
        rate = sp.table.mean(axis=1)
        assert rate.min() >= 0.1 and rate.max() <= 0.9


@pytest.mark.parametrize("domain,level", all_configs())
def test_canonical_sources_identify_themselves(domain, level):
    d = get_domain(domain)
    sp = d.space(level)
    rng = np.random.default_rng(0)
    for h in rng.choice(len(sp), size=min(25, len(sp)), replace=False):
        assert d.rule_matches(level, sp.sources[h], int(h))


def test_posterior_noise_free_is_version_space():
    d = get_domain("numbers")
    sp = d.space("L2")
    target = 123
    post = Posterior(sp)
    for x in (3, 50, 97, 12):
        post.observe(x, sp.output(target, x))
    consistent = np.ones(len(sp), bool)
    for x in (3, 50, 97, 12):
        consistent &= sp.column(x) == sp.column(x)[target]
    assert post.weights()[target] > 0
    assert np.isclose(post.bits_gained(), np.log2(len(sp)) - np.log2(consistent.sum()))


def test_noisy_posterior_never_collapses():
    sp = get_domain("boolean").space("L1")
    post = Posterior(sp, eps=0.1)
    for x in sp.pool[:40]:
        post.observe(x, not sp.output(0, x))  # every observation contradicts hypothesis 0
    assert np.isfinite(post.entropy_bits()) and post.weights()[0] > 0


def test_eig_is_zero_for_already_determined_inputs():
    sp = get_domain("numbers").space("L1")
    post = Posterior(sp)
    x = sp.pool[10]
    post.observe(x, sp.output(5, x))
    assert post.eig()[10] == pytest.approx(0.0, abs=1e-9)


def test_lists_fallback_matches_direct_execution():
    from bitsbench.domains.lists import run_pipeline

    sp = get_domain("lists").space("L3")
    x = (9, 8, 7, 6, 5, 4)  # length 6 is outside the exhaustive part of the pool
    col = sp.column(x)
    for h in (0, 100, 5000):
        assert sp.vocab[col[h]] == run_pipeline(sp.sources[h].split(" | "), x)
