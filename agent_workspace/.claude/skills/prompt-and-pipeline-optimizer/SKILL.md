---
name: prompt-and-pipeline-optimizer
description: 'Improve chunk-caption prompts, report-synthesis prompts, and first-pass video-analysis workflow design. Use when optimizing prompt quality, tuning system prompts, reducing overclaiming, improving chunk captions, improving report synthesis, rerun planning, pipeline diagnosis, プロンプト改善, キャプション改善, or report-generation experiments.'
argument-hint: 'Provide the current chunk-caption prompt, the final report prompt, representative weak outputs, and whether you want prompt rewrites, failure diagnosis, or an experiment plan.'
---

# Prompt and Pipeline Optimizer

Use this skill when the problem is not just the result, but the way the first-pass analysis is being produced.

## When to Use

- Chunk captions are vague, repetitive, or miss the operational point.
- Final reports over-interpret, flatten nuance, or contradict chunk evidence.
- Output quality is unstable across reruns or providers.
- The user wants revised system prompts for caption generation and report synthesis.
- The user wants a structured experiment plan instead of ad hoc prompt tweaks.

## Inputs to Gather

- Current chunk-caption prompt.
- Current final report synthesis prompt.
- Representative chunk captions, metadata, and final reports.
- Error cases, unstable runs, or user complaints.

## Procedure

1. Diagnose whether the failure is primarily in chunk generation, report synthesis, or upstream data selection.
2. Review the chunk-caption prompt against [the optimizer template](./assets/optimizer-template.md):
   - observation versus inference separation
   - time and action granularity
   - evidence traceability
   - controlled improvement suggestions
3. Review the report-synthesis prompt for:
   - cross-chunk consistency
   - conflict handling
   - confidence language
   - avoidance of unsupported claims
4. If the problem is not prompt-only, say whether chunk length, frame sampling, or report structure should change.
5. Produce revised prompt text when enough context exists.
6. End with a before/after experiment plan and evaluation criteria.

## Output Requirements

- Separate diagnosis into `chunk prompt`, `report prompt`, and `pipeline`.
- When proposing rewrites, return copy-ready prompt text.
- Explain which symptom each rewrite is intended to fix.
- Include a compact experiment plan with success criteria.

## Guardrails

- Do not assume prompts are the only cause of weak outputs.
- Keep rewrites specific to work-video analysis, not generic AI-writing advice.
- Prefer small, testable revisions over a full rewrite unless the current prompt is structurally broken.