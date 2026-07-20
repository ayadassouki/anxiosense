# Prompting Strategy Evaluation

This directory contains the prompt variants used to evaluate the effect of different prompting strategies in AnxioSense.

## Experimental Conditions

Three prompting strategies were evaluated across all agents.

### 1. Zero-shot

The model receives only:

- Task description
- Agent responsibilities
- Constraints
- Output schema

No reasoning procedure or worked example is provided.

---

### 2. Zero-shot + Chain-of-Thought (CoT)

The Zero-shot prompt is augmented with an internal reasoning procedure that guides the model through the required analysis before producing the final output.

No worked example is included.

---

### 3. One-shot + Chain-of-Thought (CoT)

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
baseline.md       → Zero-shot
cot.md            → Zero-shot + CoT
cot-one-shot.md   → One-shot + CoT
```

These prompt variants are used during the evaluation experiments described in the AnxioSense experimental protocol.