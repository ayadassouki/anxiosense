| Strategy | Model A | Model B | A value | B value | Δ (A−B) | 95% CI | p (perm.) | Holm p | Holm sig. |
|---|---|---|---|---|---|---|---|---|---|
| zero-shot | Gemma 4 31B | Llama 4 Scout | 0.675 | 0.752 | -0.077 | [-0.111, -0.045] | <0.0001 | 0.0060 | **yes** |
| zero-shot | Gemma 4 31B | Mistral Small 4 | 0.675 | 0.666 | +0.009 | [-0.013, +0.032] | 0.4222 | 1.0000 | no |
| zero-shot | Gemma 4 31B | Phi-4 | 0.675 | 0.744 | -0.069 | [-0.098, -0.041] | <0.0001 | 0.0060 | **yes** |
| zero-shot | Gemma 4 31B | Qwen3.5 27B | 0.675 | 0.674 | +0.001 | [-0.023, +0.023] | 0.9626 | 1.0000 | no |
| zero-shot | Llama 4 Scout | Mistral Small 4 | 0.752 | 0.666 | +0.086 | [+0.053, +0.120] | <0.0001 | 0.0060 | **yes** |
| zero-shot | Llama 4 Scout | Phi-4 | 0.752 | 0.744 | +0.008 | [-0.014, +0.029] | 0.4467 | 1.0000 | no |
| zero-shot | Llama 4 Scout | Qwen3.5 27B | 0.752 | 0.674 | +0.078 | [+0.045, +0.112] | <0.0001 | 0.0060 | **yes** |
| zero-shot | Mistral Small 4 | Phi-4 | 0.666 | 0.744 | -0.078 | [-0.107, -0.051] | <0.0001 | 0.0060 | **yes** |
| zero-shot | Mistral Small 4 | Qwen3.5 27B | 0.666 | 0.674 | -0.009 | [-0.035, +0.017] | 0.5246 | 1.0000 | no |
| zero-shot | Phi-4 | Qwen3.5 27B | 0.744 | 0.674 | +0.070 | [+0.041, +0.100] | <0.0001 | 0.0060 | **yes** |
| zero-shot-cot | Gemma 4 31B | Llama 4 Scout | 0.650 | 0.742 | -0.092 | [-0.123, -0.062] | <0.0001 | 0.0060 | **yes** |
| zero-shot-cot | Gemma 4 31B | Mistral Small 4 | 0.650 | 0.631 | +0.019 | [-0.004, +0.043] | 0.1283 | 1.0000 | no |
| zero-shot-cot | Gemma 4 31B | Phi-4 | 0.650 | 0.696 | -0.046 | [-0.070, -0.023] | 0.0004 | 0.0120 | **yes** |
| zero-shot-cot | Gemma 4 31B | Qwen3.5 27B | 0.650 | 0.598 | +0.052 | [+0.024, +0.081] | 0.0002 | 0.0066 | **yes** |
| zero-shot-cot | Llama 4 Scout | Mistral Small 4 | 0.742 | 0.631 | +0.111 | [+0.080, +0.144] | <0.0001 | 0.0060 | **yes** |
| zero-shot-cot | Llama 4 Scout | Phi-4 | 0.742 | 0.696 | +0.046 | [+0.023, +0.069] | 0.0004 | 0.0120 | **yes** |
| zero-shot-cot | Llama 4 Scout | Qwen3.5 27B | 0.742 | 0.598 | +0.144 | [+0.108, +0.182] | <0.0001 | 0.0060 | **yes** |
| zero-shot-cot | Mistral Small 4 | Phi-4 | 0.631 | 0.696 | -0.065 | [-0.091, -0.041] | <0.0001 | 0.0060 | **yes** |
| zero-shot-cot | Mistral Small 4 | Qwen3.5 27B | 0.631 | 0.598 | +0.033 | [+0.001, +0.065] | 0.0432 | 0.6911 | no |
| zero-shot-cot | Phi-4 | Qwen3.5 27B | 0.696 | 0.598 | +0.098 | [+0.068, +0.129] | <0.0001 | 0.0060 | **yes** |
| one-shot-cot | Gemma 4 31B | Llama 4 Scout | 0.651 | 0.751 | -0.100 | [-0.132, -0.068] | <0.0001 | 0.0060 | **yes** |
| one-shot-cot | Gemma 4 31B | Mistral Small 4 | 0.651 | 0.648 | +0.003 | [-0.018, +0.024] | 0.8025 | 1.0000 | no |
| one-shot-cot | Gemma 4 31B | Phi-4 | 0.651 | 0.730 | -0.079 | [-0.106, -0.052] | <0.0001 | 0.0060 | **yes** |
| one-shot-cot | Gemma 4 31B | Qwen3.5 27B | 0.651 | 0.610 | +0.040 | [+0.016, +0.066] | 0.0027 | 0.0729 | no |
| one-shot-cot | Llama 4 Scout | Mistral Small 4 | 0.751 | 0.648 | +0.103 | [+0.071, +0.135] | <0.0001 | 0.0060 | **yes** |
| one-shot-cot | Llama 4 Scout | Phi-4 | 0.751 | 0.730 | +0.021 | [-0.001, +0.043] | 0.0679 | 0.9505 | no |
| one-shot-cot | Llama 4 Scout | Qwen3.5 27B | 0.751 | 0.610 | +0.141 | [+0.104, +0.178] | <0.0001 | 0.0060 | **yes** |
| one-shot-cot | Mistral Small 4 | Phi-4 | 0.648 | 0.730 | -0.082 | [-0.110, -0.055] | <0.0001 | 0.0060 | **yes** |
| one-shot-cot | Mistral Small 4 | Qwen3.5 27B | 0.648 | 0.610 | +0.038 | [+0.010, +0.065] | 0.0070 | 0.1750 | no |
| one-shot-cot | Phi-4 | Qwen3.5 27B | 0.730 | 0.610 | +0.120 | [+0.089, +0.153] | <0.0001 | 0.0060 | **yes** |
