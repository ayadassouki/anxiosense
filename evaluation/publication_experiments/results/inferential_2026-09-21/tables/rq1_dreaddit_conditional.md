| Strategy | Model A | Model B | A cond. acc. | B cond. acc. | Δ (A−B) | 95% CI | valid run-outcomes A / B |
|---|---|---|---|---|---|---|---|
| zero-shot | Gemma 4 31B | Llama 4 Scout | 0.693 | 0.752 | -0.059 | [-0.092, -0.028] | 3495 / 3389 |
| zero-shot | Gemma 4 31B | Mistral Small 4 | 0.693 | 0.686 | +0.007 | [-0.012, +0.026] | 3495 / 3494 |
| zero-shot | Gemma 4 31B | Phi-4 | 0.693 | 0.745 | -0.051 | [-0.079, -0.024] | 3495 / 3389 |
| zero-shot | Gemma 4 31B | Qwen3.5 27B | 0.693 | 0.692 | +0.001 | [-0.019, +0.020] | 3495 / 3488 |
| zero-shot | Llama 4 Scout | Mistral Small 4 | 0.752 | 0.686 | +0.066 | [+0.033, +0.100] | 3389 / 3494 |
| zero-shot | Llama 4 Scout | Phi-4 | 0.752 | 0.745 | +0.008 | [-0.014, +0.029] | 3389 / 3389 |
| zero-shot | Llama 4 Scout | Qwen3.5 27B | 0.752 | 0.692 | +0.060 | [+0.027, +0.094] | 3389 / 3488 |
| zero-shot | Mistral Small 4 | Phi-4 | 0.686 | 0.745 | -0.058 | [-0.086, -0.031] | 3494 / 3389 |
| zero-shot | Mistral Small 4 | Qwen3.5 27B | 0.686 | 0.692 | -0.006 | [-0.030, +0.016] | 3494 / 3488 |
| zero-shot | Phi-4 | Qwen3.5 27B | 0.745 | 0.692 | +0.052 | [+0.024, +0.082] | 3389 / 3488 |
| zero-shot-cot | Gemma 4 31B | Llama 4 Scout | 0.675 | 0.744 | -0.069 | [-0.099, -0.040] | 3495 / 3443 |
| zero-shot-cot | Gemma 4 31B | Mistral Small 4 | 0.675 | 0.661 | +0.014 | [-0.006, +0.033] | 3495 / 3494 |
| zero-shot-cot | Gemma 4 31B | Phi-4 | 0.675 | 0.706 | -0.031 | [-0.053, -0.011] | 3495 / 3466 |
| zero-shot-cot | Gemma 4 31B | Qwen3.5 27B | 0.675 | 0.653 | +0.022 | [0.000, +0.044] | 3495 / 3226 |
| zero-shot-cot | Llama 4 Scout | Mistral Small 4 | 0.744 | 0.661 | +0.083 | [+0.052, +0.115] | 3443 / 3494 |
| zero-shot-cot | Llama 4 Scout | Phi-4 | 0.744 | 0.706 | +0.038 | [+0.015, +0.061] | 3443 / 3466 |
| zero-shot-cot | Llama 4 Scout | Qwen3.5 27B | 0.744 | 0.653 | +0.092 | [+0.058, +0.126] | 3443 / 3226 |
| zero-shot-cot | Mistral Small 4 | Phi-4 | 0.661 | 0.706 | -0.045 | [-0.068, -0.023] | 3494 / 3466 |
| zero-shot-cot | Mistral Small 4 | Qwen3.5 27B | 0.661 | 0.653 | +0.009 | [-0.016, +0.032] | 3494 / 3226 |
| zero-shot-cot | Phi-4 | Qwen3.5 27B | 0.706 | 0.653 | +0.054 | [+0.029, +0.079] | 3466 / 3226 |
| one-shot-cot | Gemma 4 31B | Llama 4 Scout | 0.676 | 0.752 | -0.076 | [-0.108, -0.045] | 3495 / 3487 |
| one-shot-cot | Gemma 4 31B | Mistral Small 4 | 0.676 | 0.674 | +0.002 | [-0.016, +0.020] | 3495 / 3495 |
| one-shot-cot | Gemma 4 31B | Phi-4 | 0.676 | 0.733 | -0.058 | [-0.085, -0.032] | 3495 / 3479 |
| one-shot-cot | Gemma 4 31B | Qwen3.5 27B | 0.676 | 0.648 | +0.027 | [+0.007, +0.047] | 3495 / 3491 |
| one-shot-cot | Llama 4 Scout | Mistral Small 4 | 0.752 | 0.674 | +0.078 | [+0.047, +0.111] | 3487 / 3495 |
| one-shot-cot | Llama 4 Scout | Phi-4 | 0.752 | 0.733 | +0.019 | [-0.004, +0.040] | 3487 / 3479 |
| one-shot-cot | Llama 4 Scout | Qwen3.5 27B | 0.752 | 0.648 | +0.104 | [+0.068, +0.139] | 3487 / 3491 |
| one-shot-cot | Mistral Small 4 | Phi-4 | 0.674 | 0.733 | -0.060 | [-0.086, -0.033] | 3495 / 3479 |
| one-shot-cot | Mistral Small 4 | Qwen3.5 27B | 0.674 | 0.648 | +0.025 | [+0.004, +0.047] | 3495 / 3491 |
| one-shot-cot | Phi-4 | Qwen3.5 27B | 0.733 | 0.648 | +0.085 | [+0.056, +0.116] | 3479 / 3491 |
