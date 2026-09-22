| Strategy | Model A | Model B | A value | B value | Δ (A−B) | 95% CI | p (perm.) | Holm p | Holm sig. |
|---|---|---|---|---|---|---|---|---|---|
| zero-shot | Gemma 4 31B | Llama 4 Scout | 0.593 | 0.520 | +0.073 | [-0.013, +0.145] | 0.0271 | 0.9179 | no |
| zero-shot | Gemma 4 31B | Mistral Small 4 | 0.593 | 0.561 | +0.032 | [-0.029, +0.088] | 0.2624 | 1.0000 | no |
| zero-shot | Gemma 4 31B | Phi-4 | 0.593 | 0.534 | +0.059 | [+0.003, +0.113] | 0.0212 | 0.7419 | no |
| zero-shot | Gemma 4 31B | Qwen3.5 27B | 0.593 | 0.572 | +0.021 | [-0.018, +0.058] | 0.2501 | 1.0000 | no |
| zero-shot | Llama 4 Scout | Mistral Small 4 | 0.520 | 0.561 | -0.041 | [-0.097, +0.017] | 0.0966 | 1.0000 | no |
| zero-shot | Llama 4 Scout | Phi-4 | 0.520 | 0.534 | -0.014 | [-0.069, +0.048] | 0.6125 | 1.0000 | no |
| zero-shot | Llama 4 Scout | Qwen3.5 27B | 0.520 | 0.572 | -0.052 | [-0.120, +0.031] | 0.0956 | 1.0000 | no |
| zero-shot | Mistral Small 4 | Phi-4 | 0.561 | 0.534 | +0.027 | [-0.021, +0.077] | 0.2997 | 1.0000 | no |
| zero-shot | Mistral Small 4 | Qwen3.5 27B | 0.561 | 0.572 | -0.011 | [-0.063, +0.044] | 0.6763 | 1.0000 | no |
| zero-shot | Phi-4 | Qwen3.5 27B | 0.534 | 0.572 | -0.038 | [-0.091, +0.013] | 0.1472 | 1.0000 | no |
| zero-shot-cot | Gemma 4 31B | Llama 4 Scout | 0.583 | 0.530 | +0.054 | [-0.036, +0.128] | 0.1327 | 1.0000 | no |
| zero-shot-cot | Gemma 4 31B | Mistral Small 4 | 0.583 | 0.536 | +0.048 | [-0.022, +0.114] | 0.1468 | 1.0000 | no |
| zero-shot-cot | Gemma 4 31B | Phi-4 | 0.583 | 0.563 | +0.020 | [-0.031, +0.070] | 0.4213 | 1.0000 | no |
| zero-shot-cot | Gemma 4 31B | Qwen3.5 27B | 0.583 | 0.579 | +0.004 | [-0.033, +0.042] | 0.8333 | 1.0000 | no |
| zero-shot-cot | Llama 4 Scout | Mistral Small 4 | 0.530 | 0.536 | -0.006 | [-0.059, +0.048] | 0.8053 | 1.0000 | no |
| zero-shot-cot | Llama 4 Scout | Phi-4 | 0.530 | 0.563 | -0.034 | [-0.090, +0.030] | 0.2278 | 1.0000 | no |
| zero-shot-cot | Llama 4 Scout | Qwen3.5 27B | 0.530 | 0.579 | -0.050 | [-0.123, +0.036] | 0.1457 | 1.0000 | no |
| zero-shot-cot | Mistral Small 4 | Phi-4 | 0.536 | 0.563 | -0.028 | [-0.073, +0.022] | 0.3000 | 1.0000 | no |
| zero-shot-cot | Mistral Small 4 | Qwen3.5 27B | 0.536 | 0.579 | -0.044 | [-0.101, +0.021] | 0.1359 | 1.0000 | no |
| zero-shot-cot | Phi-4 | Qwen3.5 27B | 0.563 | 0.579 | -0.016 | [-0.063, +0.031] | 0.5216 | 1.0000 | no |
| one-shot-cot | Gemma 4 31B | Llama 4 Scout | 0.585 | 0.544 | +0.041 | [-0.036, +0.105] | 0.2095 | 1.0000 | no |
| one-shot-cot | Gemma 4 31B | Mistral Small 4 | 0.585 | 0.594 | -0.009 | [-0.067, +0.045] | 0.7415 | 1.0000 | no |
| one-shot-cot | Gemma 4 31B | Phi-4 | 0.585 | 0.541 | +0.045 | [-0.001, +0.094] | 0.0719 | 1.0000 | no |
| one-shot-cot | Gemma 4 31B | Qwen3.5 27B | 0.585 | 0.567 | +0.018 | [-0.026, +0.061] | 0.3963 | 1.0000 | no |
| one-shot-cot | Llama 4 Scout | Mistral Small 4 | 0.544 | 0.594 | -0.050 | [-0.113, +0.022] | 0.0847 | 1.0000 | no |
| one-shot-cot | Llama 4 Scout | Phi-4 | 0.544 | 0.541 | +0.004 | [-0.052, +0.070] | 0.9050 | 1.0000 | no |
| one-shot-cot | Llama 4 Scout | Qwen3.5 27B | 0.544 | 0.567 | -0.023 | [-0.084, +0.049] | 0.4478 | 1.0000 | no |
| one-shot-cot | Mistral Small 4 | Phi-4 | 0.594 | 0.541 | +0.053 | [+0.004, +0.103] | 0.0369 | 1.0000 | no |
| one-shot-cot | Mistral Small 4 | Qwen3.5 27B | 0.594 | 0.567 | +0.027 | [-0.015, +0.072] | 0.2231 | 1.0000 | no |
| one-shot-cot | Phi-4 | Qwen3.5 27B | 0.541 | 0.567 | -0.027 | [-0.072, +0.016] | 0.2838 | 1.0000 | no |
