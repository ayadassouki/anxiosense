from datasets import load_dataset
from pathlib import Path

dataset = load_dataset("google-research-datasets/go_emotions")

output_dir = Path("evaluation/datasets/goemotions")
output_dir.mkdir(parents=True, exist_ok=True)

for split in dataset.keys():
    dataset[split].to_csv(output_dir / f"{split}.csv")

print(dataset)
print("Done!")