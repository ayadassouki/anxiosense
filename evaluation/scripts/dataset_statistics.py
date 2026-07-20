from datasets import load_dataset
import statistics

dataset = load_dataset("AIMH/SWMH")
train = dataset["train"]

lengths = [len(x.split()) for x in train["text"]]

print(f"Posts: {len(train)}")
print(f"Average words: {statistics.mean(lengths):.2f}")
print(f"Median words: {statistics.median(lengths)}")
print(f"Shortest: {min(lengths)}")
print(f"Longest: {max(lengths)}")