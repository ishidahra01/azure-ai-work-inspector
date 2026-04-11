---
name: coaching-artifact-generator
description: 'Turn analysis artifacts into actionable coaching deliverables. Use when generating worker feedback, supervisor notes, training cases, audit-ready summaries, coaching sheets, 教育資料, 指導メモ, or audience-specific action documents from work-video analysis results.'
argument-hint: 'Provide the selected result directories, the target audience, and the desired artifact type such as worker feedback, supervisor memo, training case, or audit summary.'
---

# Coaching Artifact Generator

Use this skill to transform technical analysis outputs into documents that a real audience can act on.

## When to Use

- The user wants a worker-facing coaching note.
- The user wants a supervisor summary or escalation memo.
- The user wants a training case built from a real run.
- The user wants an audit-style summary with restrained wording.

## Inputs to Gather

- Selected result directories.
- Existing report, metadata, and any standard document if relevant.
- The target audience and tone.

## Procedure

1. Identify the target audience and the decision they need to make.
2. Read the source report and keep only audience-relevant findings.
3. Convert technical findings into concrete actions using [the coaching template](./assets/coaching-template.md).
4. Preserve evidence-backed wording for claims that may be challenged.
5. If the user asks for document replacement, generate a complete, ready-to-paste artifact.

## Output Requirements

- Tailor the structure to one audience at a time.
- Prefer short, specific actions over abstract advice.
- Keep evidence and interpretation distinct when the audience needs traceability.
- If a finding is weakly supported, soften the wording and say what to verify.

## Guardrails

- Do not reuse the same tone for workers, supervisors, and auditors.
- Do not inflate weak evidence into disciplinary language.
- Avoid generic coaching language that is not anchored in the selected artifacts.