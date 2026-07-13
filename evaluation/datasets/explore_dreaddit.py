from datasets import load_dataset

dataset = load_dataset("andreagasparini/dreaddit", cache_dir=".hf_cache")

print(dataset)

print(dataset["train"][0])
