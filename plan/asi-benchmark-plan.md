# Plan: an ICML 2027 benchmark on overseeing superhuman AI ("Oversight-Gap", working name)

*Status: plan only. No code has been written for it. Facts marked UNVERIFIED came from aggregators or memory, or the primary source could not be reached: arxiv.org and icml.cc did not resolve during research, so most citations are based on search-result summaries.*

---

## 1. Recommendation

**Build Oversight-Gap: can a weaker judge tell when a stronger AI is right? It is scored exactly, on certified logic and math claims.** It is a hybrid. The frame comes from the Oversight-Gap proposal. The "real math" worlds come from BeyondRecords. BITS-Bench's exact-posterior code is folded in. The hybrid is designed to fix the fatal objections both critics raised.

**Pitch.** Once AI is superhuman, nobody can grade its work by redoing it. Oversight then depends on two things: verification being easier than generation, and protocols (spot-checks, critique, debate) that let a weaker judge get at the truth. Current oversight benchmarks are weak in three ways. Their answer keys are written by humans. Their capability gaps are artificial (hidden passages). And they are small. In our benchmark, stronger solvers make claims about objects whose truth is computed exactly: planted SAT instances, Golomb rulers and covering designs, and enumerated hidden-rule worlds. The solvers are frontier LLMs, or classical search given far more compute than the judge. Some claims are honest, some are subtly sabotaged, and some come from computed worst-case adversaries. Weak judges must accept or reject each claim. Every label is exact, and for every judge an ideal or worst-case reference overseer is computed. That lets us measure how oversight degrades as the gap grows, which protocols slow the decline, and why judges fail: they check the wrong things, or they are talked out of what their own evidence shows.

**Core question.** As a solver pulls ahead of its overseer on the same information, how fast does the overseer lose the ability to separate correct claims from incorrect or sabotaged ones? Does that depend on whether the claim has a short certificate (V1), can only be checked statistically (V2), or is universal or negative (V3, coNP-like)?

**Why it is ASI-relevant.**
- The labels stay valid however strong the solver gets, because nobody has to be smarter than the solver to grade it.
- It targets a failure already visible at the frontier. In First Proof batch 1, models produced confident proofs for all 10 problems and only 2 held up (arXiv 2602.21201). Several AI "Erdős solutions" were rediscoveries of known results (Quanta, Aug 2026). Sandbagging detection sits around 0.60 AUC (CTRL-ALT-DECEIT, secondary source). ASI-Bench shows research automation is arriving. The next question is who checks it.

**Why this beats the alternatives.**
- **Cost.** It is the cheapest option: an MVP is about $1.5–2k of API spend on CPU only. It reuses 40–60% of the BITS-Bench infrastructure.
- **The headline survives a null.** The main result is falsifiable and theory-driven (debate should help most on V3 claims). A null result is still publishable.
- **BeyondRecords alone** probably finds zero records beyond humanity's best at a $3k budget. It also depends on record tables and dated histories we could not reach.
- **Discovery Autopsy** is bounded by an ideal observer, and its "exact" split relies on hypothesis spaces the agent reports about itself.
- **HEADROOM** collapses into "recognise the textbook prior".

**How the hybrid fixes the critics' fatal objections.**

| Objection to the original Oversight-Gap | Fix |
|---|---|
| The gap is just information asymmetry (k spot-checks vs B experiments) | The **primary worlds give judge and solver identical information**: SAT, rulers, designs. The gap is in compute and search capability. BITS worlds are kept only as a contrasting "information-gap" regime. |
| The judge tool ban is artificial | Judges get a **capped compute/tool budget**, not a ban. Instance sizes are calibrated so the capped judge cannot solve them and the strong solver can. |
| H2 is tautological when the honest debater has the oracle | The **primary debaters are LLMs without the oracle**, and they must find the witness themselves. Oracle-backed debate is reported only as an upper bound. |
| An "ideal overseer" is the wrong normaliser against an optimal adversary | A **minimax (Stackelberg) worst-case false-accept rate** is computed on small instances. The Bayes-ideal reference is secondary. |
| Calling an enumerator "superhuman" overclaims | Drop the word. Strong solvers are described as "beyond the judge's reach". Extrapolation to ASI is labelled as hypothetical. |
| Too many grid cells | Tight MVP (§3.6). V2 claims go to the appendix. |

---

## 2. What exists and the exact gap

| Work | What it does | Why it is not this benchmark |
|---|---|---|
| ASI-Bench, arXiv 2608.17271 (https://arxiv.org/abs/2608.17271) | 60 expert research projects. Mean scores fall from 50.91 at B1 to 26.62 at B3 as guidance is removed. | Measures capability with rubrics and judges. Does not measure oversight. |
| Khan et al., ICML 2024 (https://arxiv.org/abs/2402.06782) | Debate on QuALITY. Human judges reach 88% with debate vs 60% naive. | The gap is a hidden passage, and the answer keys are human-written. |
| Kenton et al., NeurIPS 2024 (https://arxiv.org/abs/2407.04622) | Weak LLM judges across protocols and tasks. | No ideal-overseer reference, no worst-case adversary, existing human-keyed datasets. |
| Engels et al. 2025 (https://arxiv.org/abs/2504.18530) | Oversight Elo vs general Elo in 4 games. | Capability is proxied by Chatbot Arena Elo, and there are no exact references. |
| Elasky et al. 2026 (https://arxiv.org/abs/2605.27483), the **closest** | Debate on verifiable code and logic, 5 model pairings. Debate helps only when the critic out-classifies the judge. | No verification-complexity ladder, no computed adversaries, no checking-vs-persuasion decomposition, no controlled gap axis. |
| CTRL-ALT-DECEIT (https://arxiv.org/abs/2511.09904); ASMR-Bench (https://arxiv.org/abs/2604.16286) | Sabotage and sandbagging monitors in ML R&D. ASMR-Bench's best auditor reaches AUROC 0.77 on 9 codebases. | Small N, and no exact measure of how much damage the sabotage did. |

Also cite and differentiate: Fluri et al. on consistency checks (https://arxiv.org/abs/2306.09983) and "A Benchmark for Scalable Oversight Protocols" (https://arxiv.org/abs/2504.03731). From memory, all UNVERIFIED this session: Neural Interactive Proofs (arXiv 2412.08897), Prover-Verifier Games (arXiv 2407.13692), Irving et al. 2018 on debate (arXiv 1805.00899).

**The exact gap.** No benchmark found combines all five of these:
1. a solver genuinely beyond the judge on the same information;
2. computed rather than human-written truth;
3. an exact or worst-case reference overseer to normalise against;
4. a controlled ladder of verification complexity (certificate, statistical, universal);
5. sabotage whose damage is exact.

*Novelty is NOT confirmed.* The search budget ran out before a dedicated search, so this is the week-1 gate.

---

## 3. Benchmark design

### 3.1 Worlds (each claim is about an object whose truth is computed)

| World | Role | Example claims |
|---|---|---|
| **W1 Planted SAT / graph colouring** (primary) | Reasoning gap with identical information. Sizes are chosen in the pilot so that a capped judge cannot solve the instance and a strong solver (kissat or CP-SAT with CPU-hours, or a frontier LLM with tools) can. | V1: "this assignment satisfies φ". V3: "φ is UNSAT" (true claims come with a DRAT proof checked by drat-trim). |
| **W2 Real-math bridge: Golomb rulers** (MVP), plus covering designs and constant-weight codes if table access passes the gate | External validity on real mathematics. Optimal rulers are proven up to about 27–28 marks (from memory, UNVERIFIED). | V1: "these n marks form a Golomb ruler of length L". V2: "this constructor stays valid for n up to 40". V3: "no shorter n-mark ruler exists" (true at proven optima, false where better rulers are known). |
| **W3 BITS hidden-rule worlds** (Boolean L2/L3, regular languages) | Controlled information-gap regime with exact posteriors. Hosts the sandbagging track. | V2: "the hidden rule is equivalent to R". V3: "these experiments uniquely identify the rule". |

### 3.2 Claim sources
Base rate of true claims is 0.5 (0.2 as an ablation).
1. Honest exact solver.
2. Honest frontier LLM, whose natural errors are graded exactly.
3. Prompted saboteur LLM that is shown the truth.
4. **Computed adversary.** It produces minimum-damage false claims, such as an assignment violating one clause, the false hypothesis with the smallest disagreement mass, or a near-optimal ruler claimed to be optimal. It pairs them with cherry-picked true evidence. The text is rewritten by the same LLM template as honest claims.
5. **Sandbagging track (W3).** Experiment logs degraded on a grid of exact gathering regret.

### 3.3 Protocols
- P0: claim only.
- P1: claim plus evidence chosen by the solver.
- P2: judge budget k ∈ {0, 4, 16} of oracle checks or capped tool calls.
- P4: static debate with oracle-free LLM debaters given the same budget as the solver. One round in the MVP.
- P5: single critique.
- Full version adds P3 consultancy, 3-round debate and P6 consistency probing.

### 3.4 Ground truth, references, metrics

**Truth.** Exact verifiers: clause checks, pairwise differences, exhaustive coverage, truth-table equivalence. pysat with drat-trim for UNSAT. Proven optima for V3.

**References.**
- (a) Bayes-ideal overseer over the judge's own information (W3, small W1).
- (b) Optimal spot-check policy. Its catch probability is exact, e.g. hypergeometric over the clauses an assignment violates.
- (c) **Minimax worst-case false-accept rate**, computed on small instances.

**Metrics.**
- AUROC.
- False-accept rate at 5% false-reject.
- Brier score against the exact posterior.
- Oversight efficiency: OE = (AUROC_judge − 0.5) / (AUROC_ref − 0.5).
- **Exact decomposition**: shortfall = *checking regret* (ideal with optimal checks minus ideal with the judge's own checks) + *persuasion regret* (ideal with the judge's checks minus the judge). Reported separately for honest and adversarial claims.
- Rhetoric sensitivity: acceptance shift between claim pairs with identical exact posteriors.
- Oversight reach: the largest gap at which OE ≥ 0.8.
- Red-team underestimation factor: computed-adversary false-accept rate divided by prompted-saboteur false-accept rate.
- Monitor AUROC as a function of exact sabotage dose.

**Gap axis.** The primary axis is within-family knobs that can be varied continuously: SAT size against the judge's budget, k/B and space size in W3, number of marks in W2. This gives 8–12 gap points per judge. Cross-model IRT ability is a secondary axis.

**Statistics.** Preregistration on OSF, mixed-effects logistic regression, cluster bootstrap over instances, Holm correction, and a power analysis from the pilot.

### 3.5 Contamination and longevity
- Every instance, claim and adversary is regenerated from a private seed at evaluation time, so there is nothing to memorise. The generators can be published.
- There are no human labels to leak or get wrong.
- Difficulty can be raised without a ceiling: instance size, a tighter judge budget, a stronger adversary, a higher share of V3 claims.
- The computed adversary is re-run against each protocol, so better judge heuristics always face the worst case.
- Saturation would mean weak overseers reach ideal oversight against optimal adversaries at large gaps. That is a safety milestone, not an artefact.
- This follows Akhtar et al. (ICML 2026, https://proceedings.mlr.press/v306/akhtar26a.html): private test sets alone did not prevent saturation.

### 3.6 MVP vs full version

| | MVP (enough for ICML) | Full |
|---|---|---|
| Worlds | W1 SAT, W3 Boolean/regular, W2 Golomb (about 200 claims) | Plus colouring, covering designs, codes |
| Claims | about 3k; V1 and V3 headline, V2 in appendix | about 10k; V1–V3 |
| Sources | honest exact, honest LLM, computed adversary, 1 prompted saboteur | plus sandbagging dose grid, more saboteurs |
| Protocols | P0, P1, P2 (k=0/4/16), P4 one round, P5 | plus P3, 3-round P4, P6 |
| Judges | 4: two open-weight sizes, one small proprietary, one frontier anchor | 6–8 |
| Headline figures | OE vs gap per protocol; ladder × protocol interaction; checking vs persuasion | plus sandbagging dose-response, human study |

---

## 4. Experiments

**Models.** Pin exact IDs and dates at run time.
- Judges: an open-weight ladder (e.g. Qwen-class at 4B, 8B and 32B via cheap APIs), Haiku/mini/Flash-class models, and one frontier anchor.
- Strong side: 2–3 frontier models from different providers, plus kissat, CP-SAT and annealers given CPU-hours.

**Baselines.** Always accept, always reject, random spot-checks, a classifier on the solver's stated confidence, and the reference overseers (a)–(c).

**Ablations.**
- Judge warned or not warned about adversaries.
- Base rate 0.5 vs 0.2.
- Low vs high reasoning effort for the judge.
- Raw vs summarised evidence.
- Oracle-free vs oracle-backed debaters.
- Two judge harnesses.
- A style classifier and a content-feature classifier on claims, both of which must be at chance.

**Headline hypotheses** (to preregister; these are not results):
- **H1, gap scaling.** OE falls monotonically with the gap. Against computed adversaries, LLM judges at large gaps do worse than the judge's own random spot-check bound, because persuasion regret is positive.
- **H2, ladder × protocol.** With oracle-free debaters, debate and critique add little on V1, more on V2, and most on V3, where the honest side can exhibit a short witness of falsity. This is a direct empirical test of Irving et al. 2018.
- **H3, persuasion grows with strength.** Persuasion regret, not checking regret, accounts for most of the decline as solvers get stronger.
- **H4, naive receivers.** Under selective but truthful disclosure (P1), acceptance tracks the naive posterior, not the skeptical game-aware one.
- **H5, rhetoric.** At an identical exact posterior, a fluent and confident argument shifts acceptance, more so for weaker judges.
- **H6, sandbagging is harder to catch than lying.** At equal exact damage, sabotage of experiment choice is detected less often than sabotage of conclusions.
- **H7, transfer.** Judge rankings on the synthetic worlds (W1/W3) predict rankings on real-math claims (W2).
- **Robustness.** The red-team underestimation factor, reported per protocol.

---

## 5. Timeline

**Deadline: NOT confirmed.** No ICML 2027 call for papers was found. Third-party trackers estimate abstracts around **16 Jan 2027** and full papers around **22 Jan 2027 AoE**, with others saying 22–28 Jan (opencurious.com, trybibby.com; UNVERIFIED). ICML's Future Meetings page lists 2027 in South America. For reference, ICML 2026 had abstracts due 23 Jan and full papers due 28 Jan 2026, an 8-page main body, and benchmarks in the main track. **Plan to an internal deadline of 13 Jan 2027.** That leaves about 12.5 working weeks, with low capacity over the holidays.

| Phase | Weeks (2026–27) | Work |
|---|---|---|
| 0. Decide and check | Wk 1 (19–25 Oct) | Make the decisions in §10. **Novelty pass** on Elasky 2026, Neural Interactive Proofs, Prover-Verifier Games, ControlArena, arXiv 2504.03731, 2609.29189, 2605.28807 and 2507.19486. Verify the ICML CFP. Draft the preregistration. **Gate A:** if a paper already does exact-reference oversight with a verification ladder, re-scope to the novel parts or switch to the runner-up. |
| 1. Build | Wk 2–4 (26 Oct–15 Nov) | SAT generator plus pysat/drat-trim. Golomb verifier and claim set. Claim and adversary generators on the BITS worlds. Judge harness and protocol runner. Reference overseers, including minimax on small instances. Unit tests proving exactness on tiny cases. |
| 2. Pilot | Wk 5 (16–22 Nov) | About 300 claims, 2 cheap judges, 1 frontier debater, about $150. **GO/NO-GO** (below). |
| 3. Freeze | Wk 6 (23–29 Nov) | Freeze v1, preregister on OSF, generate and cache strong-model transcripts. |
| 4. Main runs | Wk 7–9 (30 Nov–20 Dec) | MVP grid, about 120k judge calls. Ablations on a subset. |
| 5. Analysis | Wk 10–11 (21 Dec–3 Jan, holidays) | Decomposition, oversight curves, H1–H7 tests, transfer analysis. |
| 6. Write | Wk 12–13 (4–17 Jan) | Paper, datasheet, code release. Register the abstract around 16 Jan. |
| Buffer | Wk 14 (18–22 Jan) | Submit. |

**Pilot go/no-go criteria (end of week 5).** All five must pass:
1. The reference overseer's AUROC is between 0.7 and 0.95 in every world.
2. Judge OE moves with k and with instance size, rather than sitting flat at chance or at ceiling.
3. A SAT size exists that the capped judge cannot solve and the strong solver can, within the CPU budget.
4. The style and content classifiers are at chance.
5. Cost per judge call is within 2× of the estimate.

**What to do if criteria fail.**
- If 3 fails: make W2 or W3 primary and present the gap honestly as compute or information asymmetry.
- If 1 or 2 fails: retune difficulty, at a cost of one week.
- If several fail: switch to BeyondRecords-lite (§8).

---

## 6. Budget and resources

| Item | MVP | Full |
|---|---|---|
| Strong-model transcripts (claims, debate, critique; cached) | $300–600 | $500–900 |
| Cheap-judge calls (about 0.5B tokens) | $50–250 | $300–800 |
| Frontier anchor judge (10% subset) | $150–400 | $300–600 |
| Pilots and reruns (30% margin) | $300–500 | about $700 |
| **API total** | **about $1.0–1.8k** | **about $2–3k** |
| CPU for strong solvers (about 1–2k core-hours) | $50–150 on spot instances, or a lab machine | $150–300 |
| GPU | none | none |
| Optional human study (Prolific, 40–60 people) | not included | $1–1.5k plus IRB time; does not fit the deadline |
| People | about 10–12 person-weeks: 1 full-time person plus part-time help | 14–18 person-weeks: 1 full-time plus 1 half-time |

Prices are estimates and change often. Recalibrate them on the pilot.

---

## 7. Risks and mitigations (including how reviewers will attack it)

| Attack or risk | Mitigation |
|---|---|
| "Toy domains, not ASI" | Present the benchmark as a measurement instrument for domain-general oversight failures: persuasion against evidence, cherry-picking, unverifiable universal claims. Include W2 as real mathematics and test H7 transfer explicitly. Do not claim breadth. |
| "The gap is artificial" | Primary worlds give both sides identical information, and the gap is calibrated compute and search capability. W3's information gap is labelled as a contrast condition. |
| "H2 is true by construction" | Primary debaters do not have the oracle and must find the witness. Oracle-backed debate is an upper bound only. |
| "The normaliser is wrong against adversaries" | Minimax reference on small instances, with Bayes-ideal as secondary. State which reference applies to each cell. |
| Judges with tools brute-force small instances | Capped tool budgets with no solver libraries. W1 sizes calibrated against kissat runtime in the pilot. A tool-enabled track reported separately. |
| Prompted saboteurs are not realistic misaligned models | Report the computed adversary (upper bound) and the prompted saboteur (lower bound) side by side. Fine-tuned model organisms are beyond the budget (FLAG). |
| Prior-art collision (2026 moves fast) | Gate A in week 1. The ladder × protocol test and the exact decomposition are the parts most likely to be new. |
| Null or flat results | Preregister so a null is publishable, e.g. "no protocol beats the spot-check bound". Calibrate difficulty in the pilot. |
| Too few gap points (statistical power) | Within-family knobs give 8–12 points per judge. Power analysis before the main runs. |
| ICML dates move earlier, or the policies change | Internal deadline of 13 Jan. NeurIPS 2027 Evaluations & Datasets track as fallback (dates UNVERIFIED). ICML 2026 required authors to review and penalised thin slicing. |
| API models are deprecated mid-study | Pin IDs, cache every transcript, include open-weight judges. |

---

## 8. Runner-up directions

1. **BeyondRecords** (certified combinatorial records, with compute- and dollar-matched attribution). It has the strongest "beyond humanity's best" framing because its verifiers stay exact and unbounded. **Pick it instead** if someone on the team knows combinatorics or SAT, table access and dated record histories are confirmed in week 1, and the team accepts that the headline is likely "classical search explains most AI wins" (super-records will probably be zero at about $3k). Run fewer, deeper instances: 3 families × 20 instances.
2. **Discovery Autopsy** (BITS-Bench extended to construction, gathering, inference and stopping, posed at ASI-Bench-style disclosure levels). It is the closest in spirit to ASI-Bench and the cheapest to build from existing code. **Pick it** only if ACED-Bench (arXiv 2610.14381) and HypoArena (arXiv 2607.15766) do not pre-empt it (both UNVERIFIED, known by title only), and if the team will measure construction from behaviour, not self-reports. It is weaker on ASI relevance.
3. **HEADROOM** (AI R&D scored against Bayes-optimal risk). **Do not pick it for this deadline.** Its tuning-vs-insight split depends on arbitrary baselines and search spaces, it needs the most new infrastructure, and AI4AI-Bench, MLS-Bench and PostTrainBench cover the realistic version. Revisit it only with more time and GPUs, reframed as an ML-methodology paper.

---

## 9. The existing BITS-Bench code: fold it in, do not submit it alone

To be honest, BITS-Bench as built is **not the paper.**
- It gives the agent the hypothesis class and prior, which removes exactly the method-choice failure that ASI-Bench identifies.
- Its spaces are small enough for a code agent to saturate.
- It has no LLM results yet.
- The area around it is crowded: BoxingGym, Wild Guesses, F-ICL, agentic DFA learning (2606.16576).

Its exact-posterior machinery is still valuable. It was already used to compute the Oversight-Gap worked example.

**Reuse** (branch `claude/brave-einstein-p866dj`, `/home/user/lean-mode/bitsbench/src/bitsbench/`):
- `space.py`: Posterior, EIG and disagreement mass, giving W3 truth, adversary search and optimal spot-checks.
- `domains/`: the W3 worlds and rule-equivalence checks.
- `agents/reference.py`: honest solver, spot-check baselines, and the sandbagged-log generator.
- `episodes.py`: seeded private generation.
- `clients.py`: cached clients, so transcripts can be replayed to many judges cheaply.
- `metrics.py`: the regret decomposition, repurposed as checking vs persuasion regret, plus bootstrap CIs.
- `paper/`: the LaTeX skeleton and bibliography. Its VERIFY entries still need checking.

**Drop for now:** the chat-style discovery loop as a standalone paper. Submitting both papers to ICML 2027 risks the thin-slicing rules. If Discovery Autopsy is pursued later, it should be a separate paper that cites this one.

---

## 10. Decisions needed before work starts

1. **Direction:** Oversight-Gap (recommended), BeyondRecords, or Discovery Autopsy?
2. **Team:** how many people, and how many hours a week each between now and January? Does anyone have SAT, combinatorics or Lean background?
3. **Budget:** is about $2k of API spend approved, with up to $3k for the full version? Which providers do you have keys for?
4. **Compute:** is there a lab machine or cloud credits for about 1–2k CPU-hours?
5. **Venue:** ICML 2027 main track, with NeurIPS 2027 Evaluations & Datasets as fallback, or aim for NeurIPS from the start for more time?
6. **Human study:** skip it (recommended for the deadline), or start an IRB application this week?
7. **Name:** keep "Oversight-Gap" (collision not checked) or choose another?
8. **Release:** open-source the generators and the cached transcripts?