---
name: pattern-miner-across-runs
description: 'Mine repeated patterns across multiple analysis runs. Use when comparing many videos or reruns to find recurring strengths, waste patterns, risk signals, instability, variability, 横断分析, 傾向抽出, or common improvement themes across work-video artifacts.'
argument-hint: 'Provide the selected result directories, the work type if known, and whether you want repeated inefficiencies, good practices, risk signals, or variability across providers and reruns.'
---

# Pattern Miner Across Runs

Use this skill when one-by-one comparison is too narrow and the user needs reusable findings across multiple runs.

## When to Use

- The user wants recurring waste patterns or repeated best practices.
- The user wants to summarize a group of videos or reruns into themes.
- The user wants to know what is stable versus what varies across runs.
- The user wants a shortlist of improvement opportunities with evidence.

## Inputs to Gather

- Multiple selected result directories.
- Their report files and metadata files.
- Any user-provided grouping, such as same task, same operator, same provider, or before/after change.

## Procedure

1. Read each run's report and metadata summary.
2. Normalize similar findings into shared categories using [the pattern template](./assets/pattern-template.md).
3. Count recurrence and note which runs support each pattern.
4. Separate patterns into:
   - repeated strengths
   - repeated inefficiencies
   - repeated risks
   - run-to-run variability
5. Highlight patterns that appear often enough to justify training or SOP review.
6. Identify patterns that might instead be caused by prompt or provider instability.

## Output Requirements

- Start with the top 3 to 5 cross-run patterns.
- For each pattern, include recurrence, representative evidence, and expected impact.
- Explicitly separate stable patterns from noisy or uncertain ones.
- If the run set is too small, say so.

## Guardrails

- Do not force unrelated findings into the same pattern bucket.
- Distinguish task variation from model variation when possible.
- Preserve uncertainty when the sample size is weak.