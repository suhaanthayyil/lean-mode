# Verdict: how far can the doctrine actually cut tokens?

Target set by the user: **−30%**. Answer: **reached on exploration-type tasks, not on a mixed task
mix.** Best aggregate = **−17.3% total tokens / −12.3% cost / −16.7% turns**.

120 runs, sonnet, 73-file Go repo, 4 tasks × 5 arms, **n=6 per cell, median** (not mean — one
thrashing run must not carry a cell). Harness: `bench2.sh`, scorer: `score3.py`, raw: `RESULTS-v2.txt`.

## Arms

| arm | doctrine | Δtotal | Δcost | Δout | Δturns |
|---|---|---|---|---|---|
| `lean1` | v1, ~1.5k tokens (the originally shipped one) | +0.7% | −1.7% | +14.0% | 0% |
| `lean3` | ~120 tok + hard ranged-read + **answer from search output alone** | **−17.3%** | **−12.3%** | +22.9% | **−16.7%** |
| `lean4` | lean3 + named-file skip rule | −0.3% | −4.7% | +13.6% | 0% |
| `lean5` | lean4 + **Bash-only tool surface** (fewer tool schemas in the cached prefix) | −5.8% | −10.7% | **−25.6%** | 0% |

## Where −30% IS reached (per task)

| task | best arm | Δtotal |
|---|---|---|
| T2 impact / who-calls | `lean5` | **−36.9% (only SIGNAL-labelled result in the study)** |
| T3 multi-hop explain | `lean3` | **−66.9%** (base thrashes: spread ±357,605 — direction clear, magnitude not) |
| T1 locate | `lean5` | −6.7% |
| T4 named-file **control** | `lean5` | −4.6% (`lean3` **+34.9% WORSE** — doctrine is pure overhead here) |

So the honest statement is: **−33% to −67% on impact/multi-hop work; ~0 or negative on trivial
named-file work; −17% on a mix of the two.** Quoting a single aggregate number for "lean-mode" hides
which of those you're buying.

## Two findings that invalidated earlier numbers

**1. `real` tokens is a contaminated metric — my own first headline (−12.2%) was partly artifact.**
Measured floor (`FLOOR.txt`): the identical trivial run gave `real=8767` (cache_creation=8760) on a
cold cache and `real=7` (cache_creation=0) on a warm one. The ~8.8k harness prefix flips between
`cache_creation` and `cache_read` on **run interleaving, not treatment**. Everything is now reported
in `total` (prefix counted exactly once either way), `$cost`, `output`, `turns`.

**2. A *tiny* doctrine has no cache discount.** Cache reads bill at 0.1× base, but only if the block
actually caches — below the model's minimum cacheable prefix (**1024 tokens for Sonnet**) caching
*silently no-ops* and those tokens bill at full **1.0×**. So the ~120-token doctrines had a 1.0×
ceiling, not a 0.1× floor. "Make the instructions shorter" is a ~10×-attenuated lever at best, and
below the cache minimum it stops being a lever at all. (Anthropic's own guidance: *"minimal does not
necessarily mean short."*)

## Why the aggregate stalls at −17%

- **Turn count is the dominant lever, and it has a floor.** `lean3` cut median turns 3.0 → 2.5 and
  that is where its −17.3% comes from. On T3 it went 7 → 2 turns → −66.9%. You cannot go below ~2
  turns (one retrieval + answer), so per-task savings cap out.
- **The doctrine itself costs tokens on every turn** and is a net loss on tasks with nothing to
  explore (T4: `lean3` +34.9%).
- **Terse-output instructions do not reduce output.** `lean3` output *+22.9%* — the model complied
  with the style and then said more. Only the reduced-tool arm (`lean5`) actually cut output
  (−25.6%), which is a tool-surface effect, not a style effect.
- **Noise dominates variant-vs-variant comparison.** Spreads run ±34k–357k on total against deltas
  of ~18k. Only one cell (T2/`lean5`) exceeded its own spread. Separating −17% from −30% reliably
  needs n≈20+ or a broader task set; I stopped rather than over-read n=6.

## What would actually get a mix to −30% (research-ranked, not folklore)

Ranked by *measured* effect on uncached tokens in the published record — note the top levers are
**harness-level, not prompt-level**, which is why a doctrine alone plateaus:

1. **Keep tool definitions / bulk payloads out of context** — 98.7% (vendor, n=1) and 78.5%
   (third-party, N=50, unverified). This repo's `lean5` is a weak version of it and it produced the
   only clean signal plus the only real output reduction.
2. **Clear stale tool results** — ~48% in the one first-party artifact that discloses methodology
   (84% vendor headline has none).
3. **Shape tool-result payloads** — 65% on a single JSON blob. (`--format agent --top-k 3` is this
   lever; already in the doctrine.)
4. **Prompt-cache hygiene** — 41–80% on *cost* against a cache-busted baseline; dollars, not tokens.
5. **Shortening instructions** — 0.1×-attenuated, and negative below the cache minimum.
6. **Sub-agent isolation** — preserves the coordinator's context but inflates *total* tokens ~15×.
   Not a token-saving lever.

There is **no published measurement** for turn-capping, ranged reads, top-k tuning, or terse-output
instructions — so the numbers in this file are, as far as the research sweep found, novel data.

## Honest limits

4 tasks, 1 repo, 1 model, read-only locate/explain work. n=6 with large spreads. RTK is still
unmeasured (neither arm has the hook; these tasks aren't shell-heavy). Treat per-task signs as
directional and the aggregate as approximate.
