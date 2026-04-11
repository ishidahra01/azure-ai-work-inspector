---
name: sop-coverage-gap-analyzer
description: 'Compare analyzed work-video artifacts against standard operating procedures and inspection documents. Use when checking SOP coverage, standard work compliance, 手順照合, 標準書突合, observed versus expected steps, missed checks, or gaps against files under data/work_item_descripton.'
argument-hint: 'Provide the selected result directories and, if known, the relevant work standard document or work item name.'
---

# SOP Coverage and Gap Analyzer

Use this skill to measure how well observed work aligns with the written standard.

## When to Use

- The user asks whether the analyzed work covers the expected steps.
- The user wants a standard-work comparison rather than a plain summary.
- The user wants to identify missed checks, weak evidence, or likely deviations.
- The user needs a training or audit-oriented coverage review.

## Inputs to Gather

- Selected result directories.
- Relevant standard document(s) under `data/work_item_descripton`.
- The report and metadata for the corresponding video.

## Procedure

1. Read the most relevant standard document first.
2. Break the standard into auditable steps or checkpoints.
3. Read the report and metadata to map observed work against each checkpoint.
4. Classify each checkpoint with [the coverage template](./assets/coverage-template.md):
   - `confirmed by evidence`
   - `partially evidenced`
   - `not observed`
   - `cannot determine from available artifacts`
5. For weak or missing coverage, identify the exact information gap.
6. Distinguish between a likely operational deviation and a simple visibility limitation.

## Output Requirements

- Provide a coverage table keyed by SOP step.
- Include the evidence source or missing-evidence reason for each step.
- End with a short summary of likely gaps, likely deviations, and plain unknowns.

## Guardrails

- Do not claim non-compliance unless the evidence supports it.
- Use `cannot determine` whenever the artifact scope is insufficient.
- Prefer the most task-specific standard document rather than mixing several standards unless the user requests it.