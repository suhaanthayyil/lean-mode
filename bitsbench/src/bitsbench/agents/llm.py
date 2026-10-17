"""Language-model agent: prompts, conversation management and reply parsing.

The conversation is append-only. A checkpoint is answered in a fork (the main
history plus one extra user turn) that is then discarded, so held-out test
inputs never enter the history the agent experiments from.
"""

from __future__ import annotations

import re
from typing import Hashable

from ..clients import Client, Message
from .base import Agent, Obs, Prediction

QUERY_RE = re.compile(r"^\s*\**\s*QUERY\s*\**\s*:\s*(.+?)\s*$", re.MULTILINE | re.IGNORECASE)
RULE_RE = re.compile(r"^\s*\**\s*RULE\s*\**\s*:\s*(.+?)\s*$", re.MULTILINE | re.IGNORECASE)
PRED_RE = re.compile(r"PREDICTIONS\s*\**\s*:", re.IGNORECASE)
MARKUP_RE = re.compile(r"^[\s`*_]+|[\s`*_]+$")
RULE_MARKUP_RE = re.compile(r"^[\s`*]+|[\s`]+$")  # a trailing * may be a Kleene star


def system_prompt(domain, ep, mode: str) -> str:
    if mode == "active":
        role = (
            "You are a scientist investigating a black box. The box computes a hidden rule f, drawn at "
            "random from a known family of rules described below. You cannot look inside the box, but you "
            "can run experiments: you choose an input x and the box reports f(x).\n\n"
            f"You have a budget of {ep.budget} experiments. Your goal is to learn f well enough to predict "
            "its outputs on new inputs. Experiments are scarce, so choose each one to be as informative as "
            "possible given what you have already seen.\n\n"
            "From time to time you will reach a CHECKPOINT where you must predict f on a list of held-out "
            "inputs. Checkpoints do not use up experiments, and you will not be told whether your "
            "predictions were right. At the final checkpoint you will also be asked to state the rule "
            "exactly. You are scored on prediction accuracy at every checkpoint and on whether your final "
            "rule is exactly right, so both choosing informative experiments and reasoning carefully from "
            "their results matter."
        )
    else:
        role = (
            "You are a scientist investigating a black box. The box computes a hidden rule f, drawn at "
            "random from a known family of rules described below. You cannot look inside the box. Another "
            "investigator has run some experiments, each choosing an input x and recording the reported "
            "f(x). You will be shown their results and asked to predict f on held-out inputs (and, once all "
            "experiments are in, to state the rule exactly). You are scored on prediction accuracy and on "
            "whether your final rule is exactly right."
        )
    noise = ""
    if ep.eps:
        noise = (
            f"\n\nThe box is noisy: each reported result is flipped (true <-> false) independently with "
            f"probability {ep.eps:g}. Repeating an experiment gives a fresh, independent reading. Predictions "
            "are scored against the true, noise-free f."
        )
    fmt = ""
    if mode == "active":
        fmt = (
            "\n\nFORMAT\nThink as much as you like. To run an experiment, end your reply with one line\n"
            f"QUERY: <input>\nwhere <input> is {domain.input_format}. Only the last QUERY line counts."
        )
    return f"{role}{noise}\n\nTHE RULE FAMILY\n{domain.describe(ep.level)}{fmt}"


def observation_table(domain, history: list[Obs]) -> str:
    if not history:
        return "No experiments yet."
    lines = []
    for o in history:
        if o.valid:
            lines.append(f"  {o.t}. f({domain.fmt_input(o.x)}) = {domain.fmt_output(o.y)}")
        else:
            lines.append(f"  {o.t}. (invalid experiment - skipped, no result)")
    return "\n".join(lines)


def checkpoint_prompt(domain, ep, history: list[Obs], test_inputs: list, final: bool, mode: str) -> str:
    n = len(test_inputs)
    items = "\n".join(f"  {i + 1}. {domain.fmt_input(x)}" for i, x in enumerate(test_inputs))
    if mode == "active":
        head = (f"CHECKPOINT ({len(history)} of {ep.budget} experiments used). This does not use an "
                "experiment, and you will not be told the correct answers.")
    else:
        head = f"Results of the {len(history)} experiment(s) run so far:\n{observation_table(domain, history)}"
    rule = ""
    if final:
        rule = ("First, on its own line, give your single best guess of the rule:\nRULE: <rule>\n"
                f"where <rule> is {domain.rule_format}.\n")
    return (
        f"{head}\n\nPredict f(x) for each of these {n} inputs:\n{items}\n\n{rule}"
        f"{'Then end' if final else 'End'} your reply with one line\nPREDICTIONS: [p1, p2, ..., p{n}]\n"
        f"giving exactly {n} predictions in the order above, each {domain.output_format}."
    )


def _balanced_list(text: str, start: int) -> str | None:
    i = text.find("[", start)
    if i < 0:
        return None
    depth = 0
    for j in range(i, len(text)):
        if text[j] == "[":
            depth += 1
        elif text[j] == "]":
            depth -= 1
            if depth == 0:
                return text[i : j + 1]
    return None


def parse_query(domain, text: str) -> Hashable:
    hits = QUERY_RE.findall(text or "")
    if not hits:
        raise ValueError("no line starting with QUERY: was found")
    return domain.parse_input(MARKUP_RE.sub("", hits[-1]))


def parse_predictions(domain, text: str, n: int) -> tuple[list, bool]:
    marks = list(PRED_RE.finditer(text or ""))
    if not marks:
        return [None] * n, False
    raw = _balanced_list(text, marks[-1].end())
    if raw is None:
        return [None] * n, False
    try:
        values = domain.parse_prediction_list(raw)
    except Exception:
        return [None] * n, False
    out = []
    for v in values[:n]:
        try:
            out.append(domain.parse_output(v))
        except Exception:
            out.append(None)
    out += [None] * (n - len(out))
    return out, len(values) == n


def parse_rule(text: str) -> str | None:
    hits = RULE_RE.findall(text or "")
    return RULE_MARKUP_RE.sub("", hits[-1]) if hits else None


class LLMAgent(Agent):
    def __init__(self, client: Client, max_retries: int = 2, keep_transcript: bool = True):
        self.client = client
        self.name = client.name
        self.max_retries = max_retries
        self.keep_transcript = keep_transcript

    def begin(self, ep, domain, mode):
        super().begin(ep, domain, mode)
        if hasattr(self.client, "bind"):
            self.client.bind(domain, ep)
        self.system = system_prompt(domain, ep, mode)
        self.messages: list[Message] = []
        self.forks: list[dict] = []
        self.stats = {"calls": 0, "invalid_queries": 0, "wasted_experiments": 0, "unparsed_predictions": 0}

    # -- conversation helpers ------------------------------------------------
    def _call(self, messages: list[Message]) -> Message:
        self.stats["calls"] += 1
        return self.client.complete(self.system, messages)

    def _result_text(self, history: list[Obs]) -> str:
        if not history:
            return f"You have {self.ep.budget} experiments. No experiments have been run yet."
        last = history[-1]
        if last.valid:
            head = f"Experiment {last.t}: f({self.domain.fmt_input(last.x)}) = {self.domain.fmt_output(last.y)}"
        else:
            head = f"Experiment {last.t} was invalid and was skipped (it still counts against the budget)."
        return (f"{head}\n\nAll results so far:\n{observation_table(self.domain, history)}\n\n"
                f"Experiments used: {len(history)} of {self.ep.budget}.")

    # -- Agent API -----------------------------------------------------------
    def choose(self, history):
        prompt = self._result_text(history) + ("\n\nChoose your next experiment." if history else
                                               "\n\nChoose your first experiment.")
        self.messages.append(Message("user", prompt))
        for attempt in range(self.max_retries + 1):
            reply = self._call(self.messages)
            self.messages.append(reply)
            try:
                return parse_query(self.domain, reply.text)
            except ValueError as e:
                self.stats["invalid_queries"] += 1
                if attempt == self.max_retries:
                    break
                self.messages.append(Message("user", (
                    f"That experiment could not be run: {e}. Reply again, ending with one line "
                    f"QUERY: <input>, where <input> is {self.domain.input_format}.")))
        self.stats["wasted_experiments"] += 1
        return None

    def predict(self, history, test_inputs, final):
        cp = checkpoint_prompt(self.domain, self.ep, history, test_inputs, final, self.mode)
        if self.mode == "active":
            convo = self.messages + [Message("user", self._result_text(history) + "\n\n" + cp)]
        else:
            convo = [Message("user", cp)]
        n = len(test_inputs)
        outputs, ok, rule, replies = [None] * n, False, None, []
        for attempt in range(2):
            reply = self._call(convo)
            replies.append(reply)
            outputs, ok = parse_predictions(self.domain, reply.text, n)
            rule = (parse_rule(reply.text) or rule) if final else None
            if ok:
                break
            convo = convo + [reply, Message("user", (
                f"I could not read your predictions. End your reply with one line PREDICTIONS: [p1, ..., p{n}] "
                f"containing exactly {n} predictions, each {self.domain.output_format}."
                + (" Put the RULE: line before it." if final else "")))]
        if not ok:
            self.stats["unparsed_predictions"] += 1
        if self.keep_transcript:
            self.forks.append({"k": len(history), "prompt": cp, "replies": [r.to_json() for r in replies]})
        return Prediction(outputs, rule=rule, ok=ok)

    def end(self):
        info = {"stats": self.stats, "usage": self.client.usage_snapshot(reset=True)}
        if self.keep_transcript:
            info["transcript"] = {"system": self.system, "messages": [m.to_json() for m in self.messages],
                                  "checkpoints": self.forks}
        return info
