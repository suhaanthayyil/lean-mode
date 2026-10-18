# Plan: RecordLadder, an ICML 2027 capability benchmark for measuring AI against humanity's best-known results

*This is a plan only; no code exists for it yet. Facts marked UNVERIFIED came from aggregators, from memory, or from sources that could not be reached. No score in this plan has been measured. Every number for RecordLadder is an estimate that the week-5 pilot will replace.*

---

## 1. Recommendation

**Build RecordLadder** (working name; not checked for name collisions). It merges RecordLadder and OpenCells. The ladder structure, reference lines and provenance tags come from RecordLadder. The certified procedural rung and the blinded post-cutoff rung come from OpenCells. The recall/compute/insight decomposition follows the exact-accounting approach of BITS-Bench.

**Three-sentence pitch.** Every frontier benchmark built on a human answer key saturates, because people can only write and grade questions up to their own level. RecordLadder grades AI on open entries in humanity's record tables (covering designs, error-correcting codes, snake-in-the-box, low-autocorrelation sequences) with exact certificate checkers. One continuous scale runs from compute-matched classical search (0), through humanity's best-known value (1), to certified new results (above 1). It reports how much of a model's apparent "discovery" is recall, how much is compute, and how much is genuine insight, at a fixed token and CPU budget.

**ASI construct:** *frontier-extending constructive discovery.* Under a fixed budget, can a system produce verifiable objects that match or beat what humanity, including its computers, has found, across many unrelated problem families, and beat generic search given 30× the compute? The full construct is an ASI-relevant slice of superhuman science, but the paper should frame it as "beyond best-known at matched compute", not as "ASI". ASI-Bench and SuperARC carry the ASI label and have no lab adoption.

**Why it is unsaturated now and should stay that way**
- Nobody knows the answers to the top rung (R2), so it cannot be memorized or leaked.
- When anyone sets a new record, the old cell becomes a fresh R1 cell and the bar rises. The benchmark gets harder exactly where models improve.
- The R0 rung is regenerated from hidden seeds, and its difficulty is a parameter, not new authoring.
- The headline uses log-gap scoring, which does not compress near the record.
- Saturation is measured, not assumed. The 2026 record shows fixed, human-written sets saturate within weeks to months: Chartography went from 45% to 89% in about 2 months, Terminal-Bench-Science from about 30% to 64.6%, and FrontierMath Tier 4 from about 5% to 97.6%.

**Why a lab would adopt it**
- Grading is deterministic, with no LLM judge, and runs on CPU only.
- A frontier run on the 60-cell Lite set costs about $30–60.
- It ships as an Inspect eval with a neutral reference agent.
- It fits the fastest-growing kind of row in launch tables, AI-for-science: Terminal-Bench-Science reached Anthropic's table within about a month.
- Labs have said publicly that their automated autonomy and R&D evals are saturated.
- It turns showcase claims like AlphaEvolve's into a comparable, budget-controlled number.

**How the merged design answers the critics' fatal objections**

| Objection | Fix |
|---|---|
| Reach mostly measures recall of published constructions | Public closed cells are replaced by an **R0 rung of procedurally generated instances, certified by solver, from hidden seeds**. A **recall probe** runs on every cell, with no tools, asking the model to output the construction. The target value is **hidden by default**. The paper's analytical core is a **recall / compute / insight decomposition**. |
| A linear gap score compresses near the record | The headline uses **log-gap closure**. Cells where r* − S_m is less than 3 units are scored only as a match rate. |
| 4×120 s is too small a budget; the record axis reads 0 for everyone | Budgets are **tiers of tokens plus CPU, not dollars**. The Standard tier goes in the system card. The Extended tier is lab-run and is where record attempts are realistic. Records are a secondary ledger and never the headline. |
| "330 independent cells, SE ±0.02" is wrong | **5 families × about 30 cells**, a **family-clustered hierarchical bootstrap**, and effective n reported. |
| "EinsteinArena with a budget" / HorizonMath overlap | The contribution is the **protocol and the findings**: a compute-matched zero point, a blinded time-split rung, provenance and hard/soft lines, and the decomposition. We also re-score with binary HorizonMath-style scoring to show that it collapses the separation between models. We reuse EinsteinArena's verifiers and credit them. |
| A dollar-capped, nightly-refreshed score is not citable | Only **frozen quarterly versions** can be cited. Dollars are reported as a secondary efficiency metric. |
| R1 time-split cells expire, and model cutoffs are unknown | R1 eligibility is decided **per model** from a dated record log, using **finite witnesses only**. The rung is refilled each quarter. **Gate: at least 20 eligible cells, or R1 moves to the appendix.** |
| Solo scope is not credible | Only **5 families** (MVP: 4), the **30× solver line** instead of 1000×, Inspect only, and no human study. |

**Why it beats the alternatives.** LaplaceBench is bounded at 1, uses toy worlds, and a code agent would likely collapse it. KELVIN's human calibration study is not feasible for one person, and its extension beyond human level is circular. RecordLadder is the only option whose top end is literally beyond humanity's known results, checked exactly, and it still gives signal today through R0 and R1.

---

## 2. Honest odds

These are judgment calls, not data.

| Outcome | Solo, as planned | With an advisor or co-author and good pilot results |
|---|---|---|
| ICML 2027 main-track acceptance | about 10–20% | about 25–35% |
| Listed on the Inspect Evals Register, Epoch Benchmarking Hub or Harbor within 6 months | about 30–50%, if maintained | about 50–70% |
| Cited in at least one lab model or system card within 12 months | about 5–10% | about 10–20% |
| "Anthropic uses it in their next eval" | Cannot be promised; under 5% | Still cannot be promised |
| At least one certified hard-cell record in the paper | about 0–10% | Same; it depends on budget, not people |

**What raises the odds**
- **An advisor or co-author** with credibility in evaluation or combinatorics. Ideal partners: the EinsteinArena maintainers (Bianchi, Zou), the Caltech Math-AI group that holds the snake-in-the-box records, or a faculty member in coding theory.
- **API credit programs**, applied for in week 1: the Anthropic AI for Science program; the OpenAI Researcher Access Program; Google Gemini academic or research credits plus the free tier; Snorkel Open Benchmarks Grants (rolling applications, in-kind credits); Laude Institute Slingshots; and asking Epoch or METR to sponsor API costs, as METR did for WeirdML. Details of every program are UNVERIFIED.
- **Distribution:** an Inspect eval plus a listing in the Inspect Evals Register; an Epoch Hub submission (WeirdML is a solo-built precedent); a public leaderboard with exact configurations; and a December preview sent privately to lab eval teams, with any relationships disclosed.
- **Release before the deadline**, so that frontier numbers, and possibly lab feedback, make it into the submission.

**What cannot be promised:** lab adoption, new records, or that 2027 models will not saturate R0. R0 is expected to saturate eventually; its difficulty knob is turned up when that happens.

---

## 3. Design

### 3.1 Task families (5 core, 1 optional)

All checkers use exact integer or rational arithmetic, run in under 60 s on one core, and run **outside** the agent's sandbox.

1. **Covering designs C(v,k,t)**, with v ≤ 32. Source: La Jolla Covering Repository, which is migrating to a new Covering Repository (UNVERIFIED). Checking v=30, k=10, t=4 took 0.023 s in the prototype.
2. **Binary linear codes [n,k], maximizing d**, with k ≤ 20 so minimum distance can be checked exhaustively. Source: codetables.de; terms of use UNVERIFIED. Checking [60,20] took 0.20 s in the prototype.
3. **Snake/coil-in-the-box in Q_n**, n = 7..13. Source: the Caltech Math-AI repository, which has dated 2026 records for n=9..13 and is a source of R1 cells. Read in an earlier session; licence UNVERIFIED.
4. **Constant-weight codes A(n,d,w).** Source: Brouwer's tables. Pairwise-distance check.
5. **Low-autocorrelation binary sequences (LABS)**, N = 20..300. Exhaustive optima exist for small N; records are heuristic beyond that. Energy at N=300 took 0.4 ms in the prototype.
6. *(Optional, only if on schedule)* **csqv circle packing**, checked with exact rationals and zero tolerance. This is an explicitly *soft* calibration zone: 10 AI records were set for $28 (arXiv 2609.05093). It is also an R1 source.

**Cut entirely:** Ramsey (large checks are slow), Golomb rulers (recall risk), kissing configurations, sorting networks, fast matrix multiplication, Tao constants, moonshots, Track G twins, the constructor track, and the human pilot.

### 3.2 Rungs and cells (about 150 cells, at most 30 per family; Lite = 60 stratified)

- **R0 Certified (about 60).** Procedural variants from hidden seeds. Examples: covering a random subset of t-sets, snake paths in Q_7 with random forbidden vertices, codes under random coordinate constraints, LABS with random weights. Optima are certified by CP-SAT, SAT or exhaustive search, and an instance is discarded if certification takes more than 1 CPU-hour. Difficulty knobs are tuned so the best model scores about 0.6–0.8.
- **R1 Recently improved (target 20–30).** The record improved after a model's training cutoff, with dated public evidence, and the witness is finite. Eligibility is decided per model and requires failing a recall probe. The prompt is identical in form to an R2 prompt.
- **R2 Open (about 70).** Current record at freeze, with a proven bound U above it. Each cell is tagged *hard* if S_30 falls short of the record and *soft* if it reaches it, and tagged by provenance: algebraic or human construction, computer search, or AI-set.

### 3.3 Protocol

- **Headline condition:** the agent sees the cell specification, the certificate format and the checker interface. It is **not** shown the best-known value. A target-shown ablation is run separately.
- **Sandbox:** Docker, no network, Python with numpy, scipy, OR-Tools and PySAT, 2 GB of memory.
- **Standard tier (the system-card number):** at most 6 turns, at most 64k output tokens including thinking, at most 10 CPU-minutes total. Each turn submits a program; the checker returns the value and diagnostics; the final score is the best valid certificate.
- **Extended tier (labs only, reported separately):** about 1M tokens and 4 CPU-hours.
- **Reference agent:** a neutral ReAct-plus-Python agent. Lab scaffolds are accepted with a label.
- **Required baselines:** S_m and K independent samples without feedback, following Gideoni et al.

### 3.4 Scoring and reference lines

**Reference lines for each cell:**
- b: random greedy baseline.
- **S_m:** solver with matched CPU, i.e. the best of simulated annealing, tabu and CP-SAT, median over 3 seeds. This is the zero point.
- **S_30:** the same solver with 30× the budget. Used for the hard/soft split.
- **HB_human** and **HB_now**, with provenance and date. Each incumbent is re-verified from its published construction, or the cell is dropped.
- **U:** the proven bound.

**Headline rows**, each with a family-clustered bootstrap 95% confidence interval:
1. **Certified-Construction score (0–1)** on R0. Per cell: log-gap closure from S_m to the certified optimum.
2. **Frontier score (0–1)** on hard R1 and R2 cells. Per cell: s = 1 − log(1+gap_agent)/log(1+gap_Sm), where gaps are measured to r* and clipped to [0,1]. Reported together with the **best-known match rate**. Cells where r* − S_m is under 3 units count only toward the match rate.
3. **Certified records ledger (unbounded):** hard-cell records verified by two independent checkers and checked against the upstream table on the day of the run. Soft records are listed separately. Gains are reported as the fraction of the remaining gap to U that was closed.

**Secondary metrics:**
- **Decomposition** (the paper's core): *recall* is the value reached by the no-execution probe; *compute* is the agent's position relative to S_m and S_30; *insight residual* is the agent beating S_30 at equal or lower cost. Reported per rung and per provenance class.
- R1 recovery rate.
- Claim calibration: precision of the agent's "I beat the best known" claims.
- Cost in tokens, dollars and CPU-seconds per cell.
- A static code taxonomy: solver call, local search, or algebraic construction.

### 3.5 Expected current scores (estimates, NOT MEASURED)

| Metric | Frontier models | Cheap open-weight |
|---|---|---|
| Certified-Construction score (R0) | 0.6–0.85 (tuned) | 0.2–0.45 |
| Frontier score, hard cells | 0.2–0.45 | 0.05–0.2 |
| Best-known match rate, open hard cells | 5–20% | 0–5% |
| R1 recovery | 5–20% | 0–5% |
| Hard-cell records at Standard tier | 0–2 | 0 |

**Signal exists:** AlphaEvolve recovered the known Ramsey bounds (arXiv 2603.09172), and cheap Packomania records exist. **Headroom exists:** FrontierCO finds classical solvers still lead on hard instances; the best HorizonMath score is 11.5% (secondary source); the best FrontierMath Erdős score is 2.9%.

### 3.6 Minimum viable version vs full

- **MVP, the submission floor:** 4 families (covering designs, binary codes, snake-in-the-box, LABS); about 110 cells; R1 only if at least 20 cells are eligible; 1 frontier model on Lite plus 3 open models; Standard tier only; Inspect only; hypotheses H1–H4.
- **Full, as submitted if on schedule:** 5 families, about 150 cells, 2–3 frontier models, R1, the ablations.
- **Camera-ready / v1.1:** add packing, run a fresh quarterly freeze with new R1 cells to show the benchmark is not saturated, Harbor packaging, and Extended-tier runs if credits allow.

---

## 4. Closest prior work and the exact gap

1. **HorizonMath** (ICML 2026): about 113 unsolved problems with automatic verifiers and a calibration tier; binary scoring; top score 11.5%. https://arxiv.org/abs/2603.15617
2. **EinsteinArena**: about 35 open problems with verifiers (MIT licence); agents in the wild, no budget control. https://arxiv.org/abs/2606.10402 ; https://github.com/vinid/einstein-arena
3. **FrontierCO** (ICLR 2026): primal gap to best-known solutions on combinatorial-optimization instances. https://arxiv.org/abs/2505.16952
4. **AlphaEvolve repository of 67 problems**: a showcase, with no budgets or baselines. https://github.com/google-deepmind/alphaevolve_repository_of_problems
5. **FrontierMath Erdős / Open Problems** (Epoch): tiny n, binary, expensive, requires Lean or a paid verifier. https://epoch.ai/latest/announcing-frontiermath-erdos
6. **Simple baselines are competitive with code evolution** (Gideoni et al.), plus solvers matching AlphaEvolve on packing (Berthold et al.). https://arxiv.org/abs/2602.16805 ; https://arxiv.org/abs/2605.04850
7. **UQ** (unsolved Stack Exchange questions; LLM validators and community review). https://arxiv.org/abs/2508.17580
8. **CO-Bench / ALE-Bench**: algorithm search against human algorithms, or against human percentiles (which saturate once AI ranks first). https://arxiv.org/abs/2504.04310 ; https://arxiv.org/abs/2506.09050

**The exact gap.** None of these combines all of the following:
- (a) a **compute-matched classical zero point** together with a 30× hard/soft line;
- (b) a **blinded, per-model post-cutoff rung** that turns "open until recently" into signal today with limited contamination;
- (c) **provenance-tagged** human vs computer vs AI reference lines;
- (d) a **recall / compute / insight decomposition**;
- (e) a continuous scale from certified cells to beyond best-known, with a family-clustered power analysis.

Pre-emption by "Leaps in Bounds" (leapsinbounds.org) or a HorizonMath v2 is UNCHECKED and is the week-1 kill switch.

---

## 5. Evaluation plan (under $500, works with no credits)

**Assumptions per cell:** about 4–6 turns, about 60k input tokens (mostly cached) and about 40k output tokens. Pin model IDs at run time. Prices are third-party or reported and UNVERIFIED; reprice them in week 1.

| Run | Model class | Cells × seeds | Est. $/cell | Est. cost |
|---|---|---|---|---|
| Pilot and debugging | 2 cheap + 1 frontier | 40 | — | $40 |
| Cheap open model (about $0.14/$0.28 per M) | open-weight | 150 × 3 | $0.02 | $9 |
| 2 mid open-weight models (about $0.5/$2 per M) | open-weight | 150 × 1, plus 60 × 2 extra seeds on one | $0.11 | $46 |
| Recall probes (no tools, short) | all models | 150 each | small | $10 |
| Frontier A (top-tier model, about $4/$20 per M, Batch API) | frontier | 150 × 1 | about $0.50 | $75 |
| Frontier B (OpenAI or Google) | frontier | 60 (Lite) × 1 | up to $1.00 | $60 |
| Ablations: target shown, no solver libraries, no-feedback sampling | cheap model full; Frontier A Lite with target shown | — | — | $40 |
| Budget-scaling curve | cheap model, 40 cells × 4 budgets × 3 seeds | — | — | $10 |
| **Total** | | | | **about $290** |
| **Reserve** (token overruns, optional Frontier C on Lite) | | | | **about $210** |

- **CPU:** about 450 core-hours, mostly for S_30. Options: a 16-core machine for about 1.5 days, a university cluster, Oracle Always Free (UNVERIFIED), or about $10–30 of rented VM time. No GPUs needed.
- **Required safeguards:** hard max_tokens caps, round-synchronous Batch API calls, per-run cost logging, and a stop rule at 1.5× the estimate.
- **If credits arrive:** add a third frontier model, run every frontier model on all 150 cells with 3 seeds, run the Extended tier on 20 hard cells (record attempts), and run a second scaffold for the frontier models. None of these is on the critical path.

---

## 6. Timeline (2026-10-18 to about 2027-01-22)

The ICML 2027 deadline is **UNCONFIRMED**; check it in week 1. The plan assumes **18–20 h/week**, about 240 hours in total. At 15 h/week, use the MVP.

| Week | Dates | Work |
|---|---|---|
| 1 | Oct 19–25 | **Kill-switch checks:** Leaps in Bounds, HorizonMath v2, EinsteinArena updates, the ICML 2027 dates, terms for LJCR, codetables and Caltech data, model cutoffs, prices. Apply for credits. Contact a potential advisor. Freeze the cell schema. |
| 2 | Oct 26–Nov 1 | Harness: port BITS clients and runner, add Batch API, Docker sandbox. Checkers for covering designs, codes and LABS, each with a second independent implementation. |
| 3 | Nov 2–8 | Curate covering-design and code cells with provenance and bounds; re-verify incumbents; S_m baselines. |
| 4 | Nov 9–15 | Snake-in-the-box and constant-weight codes; R0 generators and certification; start S_30 runs in the background. |
| **5** | Nov 16–22 | **GO/NO-GO PILOT** on 40 cells with 2 cheap models and Frontier A. See the gates below. |
| 6 | Nov 23–29 | Red-team the verifiers; recall probe; select R1 cells; **freeze v0.9**. |
| 7 | Nov 30–Dec 6 | Inspect packaging; main runs on open-weight models. |
| 8 | Dec 7–13 | Frontier runs. **Public release v1.0** (dev split, harness, leaderboard). Submit to the Epoch Hub and Inspect Register; send previews to lab eval teams. |
| 9 | Dec 14–20 | Ablations, scaling curve, extra seeds. |
| 10 | Dec 21–27 | Light week. Decomposition analysis. |
| 11 | Dec 28–Jan 3 | Figures and statistics; double-check any candidate records. |
| 12 | Jan 4–10 | Full paper draft. |
| 13 | Jan 11–17 | Advisor review; abstract (deadline UNVERIFIED). |
| 14 | Jan 18–22 | Final submission. |

**Go/no-go gates in week 5:**
- R0: the best model scores 0.5–0.85 and the cheap model 0.15–0.5. Otherwise retune the knobs.
- Frontier A beats the cheap model by more than 2 SE on the Frontier score, and no model scores above 0.6 on hard open cells.
- At least 20 eligible R1 cells. Otherwise R1 moves to the appendix.
- The exploit audit is clean, and cost per cell is within 1.5× the estimate.

**Fallbacks:**
- If two or more gates fail, or curation slips past week 4, fall back to the MVP.
- If curation is fundamentally broken, pivot to LaplaceBench (§8).
- The backup venue is NeurIPS 2027 Evaluations & Datasets.

---

## 7. Risks and reviewer attacks

| Attack or risk | Mitigation |
|---|---|
| "This is toy combinatorics, not ASI." | Claim only "beyond best-known at matched compute". These are the domains where going beyond humanity can be verified today, and they are the ones labs showcase. State the scope limits plainly. |
| "This is HorizonMath or EinsteinArena again." | Lead with the protocol and the decomposition findings. Show that binary re-scoring collapses the separation between models. Reuse EinsteinArena verifiers with credit, and offer to collaborate. |
| "Gains are just solver assembly." | That is hypothesis H2, measured through the S_m and S_30 lines, the no-solver ablation and the code taxonomy. Either answer is a finding. |
| "Records are on neglected cells." | The S_30 hard/soft split; soft records reported separately; record age reported as a covariate. |
| Contamination of R0 and R1 | Hidden-seed regeneration, per-model R1 eligibility, recall probes, and scores reported with flagged cells removed. |
| Verifier exploits or tolerance bugs | Exact integers and rationals with zero tolerance, checkers outside the sandbox, two implementations per family, a published exploit audit. |
| Baseline strength disputed | Publish baseline code, version the zero point, invite stronger baselines. |
| Harness sensitivity | Fixed reference agent, labelled lab scaffolds, budget-scaling curves. |
| Zero records | Expected. The continuous score and the decomposition carry the paper. |
| Errors or licences in record tables | Re-verify from published constructions or drop the cell. Redistribute values and citations only. Ask maintainers. |
| Budget overrun | Token caps, Batch API, Lite set for frontier models, $210 reserve. |
| Solo schedule | MVP defined up front; gates in week 5; the human study is cut entirely. |
| Maintenance after ICML | Quarterly frozen versions only; no nightly service; look for a host or co-maintainer (Epoch, EinsteinArena). |

---

## 8. Runner-ups

- **LaplaceBench (the fallback):** distance to an exact Bayes-optimal scientist, with the hypothesis class hidden. It provides an invention/design/inference decomposition and reuses about half of BITS-Bench. It is the most rigorous and most feasible option, but it is bounded at 1, the worlds are toys, and code agents can likely collapse it. It is weak as a model-card row. Use it if RecordLadder fails the week-5 gates, or for a later diagnostic paper.
- **KELVIN:** a human-anchored IRT "thermometer" extended past human level by generators. It is the most interesting measurement idea, but the expert calibration study is not feasible for one person in 13 weeks, and its extension beyond human level relies on model linking that its own differential-item-functioning hypothesis would invalidate. Defer it to a collaborative project in 2027 or later; its IRT layer could be reused as an analysis over RecordLadder cells.

---

## 9. What happens to the BITS-Bench code

Location: `bitsbench/src/bitsbench` on this branch.

- **Reuse as infrastructure:**
  - `clients.py` (Anthropic and OpenAI-compatible clients, cache, usage logging). Add Batch API support, about 6 hours.
  - `runner.py` (resumable runs).
  - `report.py`.
  - The seeding pattern in `episodes.py`, adapted to R0 hidden seeds.
  - The test scaffolding.
- **Do not use for grading:** `safe_eval.py`. RecordLadder checkers run outside the sandbox as separate, independently written programs.
- **Shelve:** `space.py`, `metrics.py`, the domains and agents (the exact Bayesian machinery). Keep them intact as the starting point for the LaplaceBench fallback, or as an optional workshop paper. Do not add a BITS track to the RecordLadder paper.
- **Prototype checkers to extend:** `plan/prototypes/checkers.py`. These are timings only; large Ramsey checks were never tested.

---

## 10. Decisions and questions for the student

1. Can you commit **18–20 h/week**? If not, start with the 4-family MVP now.
2. Do you have, or can you recruit by week 2, an **advisor or co-author**?
3. Do you accept **no "ASI" in the title**, with ASI used only as motivation?
4. Will you **maintain quarterly versions** after ICML? Without that, labs will not adopt it.
5. Which frontier models can you access or get credits for? Frontier A and B need to be chosen by week 5.
6. Where will the **CPU** come from (about 450 core-hours)?
7. Are you willing to submit any records to table maintainers with AI provenance disclosed?
8. Is **NeurIPS 2027 Evaluations & Datasets** an acceptable backup venue if the week-5 gates fail?