from pathlib import Path

from datasets import load_dataset


OUTPUT_DIR = Path("evaluation/datasets/aimh_swmh")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Your Hugging Face login is already stored locally.
    dataset = load_dataset("AIMH/SWMH")

    for split_name in ("train", "validation", "test"):
        output_path = OUTPUT_DIR / f"{split_name}.csv"

        dataset[split_name].to_pandas().to_csv(
            output_path,
            index=False,
        )

        print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()