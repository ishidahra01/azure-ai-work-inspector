---
name: evidence-audit-confidence-map
description: 'Audit generated findings against metadata, chunk captions, timestamps, and frame paths. Use when validating evidence, checking confidence, separating observation from inference, tracing a claim back to source frames, 根拠確認, 証拠監査, or explaining what is grounded versus speculative in a work-video analysis.'
argument-hint: 'Provide the selected result directories, the report or claim set to audit, and whether you want a confidence table, a missing-evidence list, or a source trace.'
---

# Evidence Audit and Confidence Map

Use this skill to test whether a generated report is actually supported by the underlying artifacts.

## When to Use

- A user asks which findings are directly visible versus inferred.
- A report feels persuasive, but the confidence level is unclear.
- You need to trace a statement back to chunk captions, timestamps, or frame paths.
- You need to prepare a review output that avoids overclaiming.

## Inputs to Gather

- Selected result directories.
- The report file, report section, or explicit claims to audit.
- Matching metadata JSON and frame paths.

## Procedure

1. Read the report or extract the concrete claims the user wants audited.
2. Read the matching metadata and locate candidate chunks, timestamps, and frame paths.
3. Split each claim into the smallest auditable unit.
4. Classify each unit using the confidence rubric in [the audit template](./assets/audit-template.md):
   - `directly observed`
   - `strong inference`
   - `weak inference`
   - `unsupported with current artifacts`
5. Quote the exact evidence source whenever possible: chunk time range, chunk caption fragment, and relevant frame path.
6. Call out where the report mixes observation and interpretation.
7. Recommend the minimum additional evidence needed to upgrade confidence.

## Output Requirements

- Start with a short conclusion about overall confidence.
- Then produce a claim-by-claim table or bullet list.
- For each claim, include:
  - claim text
  - confidence class
  - evidence used
  - what remains uncertain
- Do not silently promote an inference to an observation.

## Guardrails

- Prefer under-claiming to over-claiming.
- If a frame path exists but the visual content is not explicitly inspected, say so.
- If the report contains multiple interpretations, keep them separate instead of averaging them into one vague answer.
- Stay within the selected artifacts unless the user broadens scope.