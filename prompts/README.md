# Prompting Strategy Evaluation

This directory contains the prompt variants used to evaluate the effect of different prompting strategies in AnxioSense.

## Experimental Conditions

Three prompting strategies were evaluated across all agents.

Standalone One-shot prompting was not retained as an experimental condition. The only example-based condition combines one worked example with an explicit reasoning procedure and is therefore classified as One-shot + CoT.

### 1. Zero-shot

The model receives only:

- Task description
- Agent responsibilities
- Constraints
- Output schema

No reasoning procedure or worked example is provided.

---

### 2. Zero-shot + CoT

The Zero-shot prompt is augmented with an internal reasoning procedure that guides the model through the required analysis before producing the final output.

No worked example is included.

---

### 3. One-shot + CoT

The Zero-shot + CoT prompt is further augmented with a single worked example demonstrating the expected reasoning process and output format.

---

## Experimental Control

To ensure a fair comparison, all prompt variants for a given agent share the same:

- Task definition
- Agent responsibilities
- Safety instructions
- Retrieval instructions
- Output schema
- JSON format
- Constraints

The only experimental variable is the prompting strategy:

| Strategy | Reasoning Procedure | Worked Example |
|----------|---------------------|----------------|
| Zero-shot | No | No |
| Zero-shot + CoT | Yes | No |
| One-shot + CoT | Yes | Yes |

## Prompt Variants

Each agent contains three prompt variants:

```
zero-shot.md       → Zero-shot
zero-shot-cot.md   → Zero-shot + CoT
one-shot-cot.md    → One-shot + CoT
```

These prompt variants are used during the evaluation experiments described in the AnxioSense experimental protocol.

## Experiment Labels

New runs use `one-shot-cot-v1` for the One-shot + CoT configuration. Historical run snapshots retain the legacy `cot-oneshot-v1` label and filenames so stored experiment identifiers remain stable.
