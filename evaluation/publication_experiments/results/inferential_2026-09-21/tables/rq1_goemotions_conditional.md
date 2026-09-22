| Strategy | Model A | Model B | A cond. acc. | B cond. acc. | Δ (A−B) | 95% CI | valid run-outcomes A / B |
|---|---|---|---|---|---|---|---|
| zero-shot | Gemma 4 31B | Llama 4 Scout | 0.820 | 0.727 | +0.093 | [+0.065, +0.122] | 3110 / 2997 |
| zero-shot | Gemma 4 31B | Mistral Small 4 | 0.820 | 0.770 | +0.050 | [+0.025, +0.075] | 3110 / 3093 |
| zero-shot | Gemma 4 31B | Phi-4 | 0.820 | 0.784 | +0.035 | [+0.017, +0.054] | 3110 / 2919 |
| zero-shot | Gemma 4 31B | Qwen3.5 27B | 0.820 | 0.786 | +0.033 | [+0.015, +0.052] | 3110 / 3110 |
| zero-shot | Llama 4 Scout | Mistral Small 4 | 0.727 | 0.770 | -0.043 | [-0.070, -0.016] | 2997 / 3093 |
| zero-shot | Llama 4 Scout | Phi-4 | 0.727 | 0.784 | -0.058 | [-0.085, -0.031] | 2997 / 2919 |
| zero-shot | Llama 4 Scout | Qwen3.5 27B | 0.727 | 0.786 | -0.059 | [-0.088, -0.031] | 2997 / 3110 |
| zero-shot | Mistral Small 4 | Phi-4 | 0.770 | 0.784 | -0.015 | [-0.041, +0.012] | 3093 / 2919 |
| zero-shot | Mistral Small 4 | Qwen3.5 27B | 0.770 | 0.786 | -0.016 | [-0.041, +0.007] | 3093 / 3110 |
| zero-shot | Phi-4 | Qwen3.5 27B | 0.784 | 0.786 | -0.002 | [-0.023, +0.019] | 2919 / 3110 |
| zero-shot-cot | Gemma 4 31B | Llama 4 Scout | 0.817 | 0.728 | +0.090 | [+0.061, +0.119] | 3110 / 2917 |
| zero-shot-cot | Gemma 4 31B | Mistral Small 4 | 0.817 | 0.746 | +0.072 | [+0.044, +0.101] | 3110 / 3091 |
| zero-shot-cot | Gemma 4 31B | Phi-4 | 0.817 | 0.809 | +0.008 | [-0.007, +0.024] | 3110 / 2927 |
| zero-shot-cot | Gemma 4 31B | Qwen3.5 27B | 0.817 | 0.790 | +0.028 | [+0.008, +0.048] | 3110 / 3110 |
| zero-shot-cot | Llama 4 Scout | Mistral Small 4 | 0.728 | 0.746 | -0.018 | [-0.044, +0.009] | 2917 / 3091 |
| zero-shot-cot | Llama 4 Scout | Phi-4 | 0.728 | 0.809 | -0.082 | [-0.109, -0.054] | 2917 / 2927 |
| zero-shot-cot | Llama 4 Scout | Qwen3.5 27B | 0.728 | 0.790 | -0.062 | [-0.088, -0.035] | 2917 / 3110 |
| zero-shot-cot | Mistral Small 4 | Phi-4 | 0.746 | 0.809 | -0.064 | [-0.092, -0.036] | 3091 / 2927 |
| zero-shot-cot | Mistral Small 4 | Qwen3.5 27B | 0.746 | 0.790 | -0.044 | [-0.071, -0.017] | 3091 / 3110 |
| zero-shot-cot | Phi-4 | Qwen3.5 27B | 0.809 | 0.790 | +0.020 | [-0.003, +0.042] | 2927 / 3110 |
| one-shot-cot | Gemma 4 31B | Llama 4 Scout | 0.815 | 0.767 | +0.048 | [+0.024, +0.073] | 3103 / 2967 |
| one-shot-cot | Gemma 4 31B | Mistral Small 4 | 0.815 | 0.786 | +0.029 | [+0.008, +0.050] | 3103 / 3098 |
| one-shot-cot | Gemma 4 31B | Phi-4 | 0.815 | 0.801 | +0.014 | [-0.004, +0.033] | 3103 / 2611 |
| one-shot-cot | Gemma 4 31B | Qwen3.5 27B | 0.815 | 0.773 | +0.042 | [+0.020, +0.066] | 3103 / 3100 |
| one-shot-cot | Llama 4 Scout | Mistral Small 4 | 0.767 | 0.786 | -0.019 | [-0.044, +0.005] | 2967 / 3098 |
| one-shot-cot | Llama 4 Scout | Phi-4 | 0.767 | 0.801 | -0.034 | [-0.058, -0.009] | 2967 / 2611 |
| one-shot-cot | Llama 4 Scout | Qwen3.5 27B | 0.767 | 0.773 | -0.005 | [-0.032, +0.022] | 2967 / 3100 |
| one-shot-cot | Mistral Small 4 | Phi-4 | 0.786 | 0.801 | -0.015 | [-0.039, +0.009] | 3098 / 2611 |
| one-shot-cot | Mistral Small 4 | Qwen3.5 27B | 0.786 | 0.773 | +0.013 | [-0.010, +0.036] | 3098 / 3100 |
| one-shot-cot | Phi-4 | Qwen3.5 27B | 0.801 | 0.773 | +0.029 | [+0.001, +0.056] | 2611 / 3100 |
