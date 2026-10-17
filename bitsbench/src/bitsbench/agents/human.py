"""Play an episode in the terminal (for human baselines and for sanity-checking prompts)."""

from __future__ import annotations

from .base import Agent, Prediction
from .llm import observation_table, system_prompt


class HumanAgent(Agent):
    name = "human"

    def __init__(self, ask=input, say=print):
        self.ask, self.say = ask, say

    def begin(self, ep, domain, mode):
        super().begin(ep, domain, mode)
        self.say(system_prompt(domain, ep, mode).split("\n\nFORMAT")[0])
        self.say(f"\nEnter inputs as {domain.input_format.split(', e.g.')[0]}.")

    def choose(self, history):
        self.say("\n" + observation_table(self.domain, history))
        while True:
            try:
                return self.domain.parse_input(self.ask(f"experiment {len(history) + 1}/{self.ep.budget}> "))
            except ValueError as e:
                self.say(f"  invalid: {e}")

    def predict(self, history, test_inputs, final):
        self.say(f"\nCHECKPOINT after {len(history)} experiments - predict f(x) ({self.domain.output_format}).")
        outs = []
        for x in test_inputs:
            while True:
                try:
                    outs.append(self.domain.parse_output(self.ask(f"  f({self.domain.fmt_input(x)}) = ")))
                    break
                except Exception as e:
                    self.say(f"  invalid: {e}")
        rule = self.ask(f"Your best guess of the rule ({self.domain.rule_format.split(', e.g.')[0]}): ") if final else None
        return Prediction(outs, rule=rule or None)
