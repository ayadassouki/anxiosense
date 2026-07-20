from datasets import load_dataset
from collections import Counter
import pandas as pd

# Load dataset (requires you to be logged into Hugging Face)
dataset = load_dataset("AIMH/SWMH", token=True)

print(dataset)

# Save splits as CSV (optional but recommended)
dataset["train"].to_pandas().to_csv(
    "evaluation/datasets/swmh_train.csv",
    index=False
)

dataset["validation"].to_pandas().to_csv(
    "evaluation/datasets/swmh_validation.csv",
    index=False
)

dataset["test"].to_pandas().to_csv(
    "evaluation/datasets/swmh_test.csv",
    index=False
)

train = dataset["train"]

print("\nColumns:")
print(train.column_names)

print("\nFeatures:")
print(train.features)

print("\nLabel distribution:")
counts = Counter(train["label"])

for label, count in counts.items():
    print(f"{label}: {count}")

print("\nExample anxiety post:")

for row in train:
    if row["label"] == "self.Anxiety":
        print(row)
        break

