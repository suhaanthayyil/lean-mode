import numpy as np
import pytest

from bitsbench.agents.llm import LLMAgent
from bitsbench.agents.reference import EIGAgent, RandomAgent
from bitsbench.clients import MockClient
from bitsbench.episodes import Episode, make_episode, make_suite
from bitsbench.metrics import references, score_record
from bitsbench.runner import run_episode


def test_episodes_are_deterministic_and_split_dependent():
    a, b = make_episode("dev", "numbers", "L2", 3), make_episode("dev", "numbers", "L2", 3)
    assert a.to_json() == b.to_json()
    assert make_episode("pilot", "numbers", "L2", 3).target != a.target or \
        make_episode("pilot", "numbers", "L2", 3).test_inputs != a.test_inputs
    assert Episode.from_json(a.to_json()).to_json() == a.to_json()


def test_test_split_needs_private_salt(monkeypatch):
    monkeypatch.delenv("BITSBENCH_TEST_SALT", raising=False)
    with pytest.raises(RuntimeError):
        make_episode("test", "numbers", "L1", 0)


def test_noise_only_for_binary_domains():
    with pytest.raises(ValueError):
        make_episode("dev", "lists", "L1", 0, eps=0.1)


@pytest.mark.parametrize("domain,level", [("numbers", "L1"), ("lists", "L2"), ("regular", "L1")])
def test_eig_reference_identifies_small_spaces(domain, level):
    ep = make_episode("dev", domain, level, 0)
    rows = score_record(run_episode(EIGAgent(), ep), references(ep, {"random": 2, "eig": 1}))
    final = rows[-1]
    assert final["map_correct"] and final["acc"] == 1.0 and final["rule_correct"]


@pytest.mark.parametrize("condition", ["active", "passive_random", "passive_eig"])
def test_decomposition_identity_and_reference_has_no_inference_regret(condition):
    ep = make_episode("dev", "boolean", "L1", 1)
    ref = references(ep, {"random": 2, "eig": 1})
    for agent in (LLMAgent(MockClient()), RandomAgent()):
        rows = score_record(run_episode(agent, ep, condition), ref)
        assert [r["k"] for r in rows] == ep.checkpoints
        for r in rows:
            assert r["gather_regret"] + r["infer_regret"] == pytest.approx(r["total_regret"])
            if isinstance(agent, RandomAgent):
                assert r["infer_regret"] == pytest.approx(0.0)
        fin = rows[-1]
        assert fin["ident_gather_regret"] + fin["ident_infer_regret"] == pytest.approx(
            fin["eig_map_mass"] - float(fin["rule_correct"]))


def test_mock_llm_records_transcript_and_survives_bad_replies():
    ep = make_episode("dev", "lists", "L1", 0)
    rec = run_episode(LLMAgent(MockClient(error_rate=0.5)), ep)
    info = rec["agent_info"]
    assert len(rec["history"]) == ep.budget and len(rec["checkpoints"]) == len(ep.checkpoints)
    assert info["stats"]["invalid_queries"] > 0
    msgs = info["transcript"]["messages"]
    assert all(m["role"] != n["role"] for m, n in zip(msgs, msgs[1:])), "roles must alternate"
    assert not any("CHECKPOINT" in m["text"] for m in msgs), "checkpoints must not leak into the main thread"


def test_noisy_oracle_is_deterministic_and_noisy():
    ep = make_episode("dev", "numbers", "L1", 2, eps=0.1)
    h1 = run_episode(RandomAgent(), ep)["history"]
    h2 = run_episode(RandomAgent(), ep)["history"]
    assert h1 == h2
    from bitsbench.domains import get_domain
    sp = get_domain("numbers").space("L1")
    eps_runs = [make_episode("dev", "numbers", "L1", i, eps=0.1) for i in range(20)]
    flips = [o["y"] != sp.output(e.target, o["x"]) for e in eps_runs for o in run_episode(RandomAgent(), e)["history"]]
    assert 0.03 < np.mean(flips) < 0.2


def test_suites_build():
    assert len(make_suite("mini")) == 30
