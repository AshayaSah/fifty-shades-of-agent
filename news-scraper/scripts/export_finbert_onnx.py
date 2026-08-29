"""Export ProsusAI/finbert to fp32 ONNX for the constrained-RAM runtime.

Run with the `ml` extra installed (torch + transformers):

    uv sync --extra ml
    python scripts/export_finbert_onnx.py --out models/finbert-onnx

Writes models/finbert-onnx/model.onnx (+ external data) and vocab.txt. The
onnxruntime sentiment backend in news_scraper/sentiment.py loads these files
lazily; the Dockerfile runs this script in a dedicated build stage so the
model ships inside the image without committing the 438 MB weights to git.

No quantization is applied: this is the original model at full fp32 precision.
"""

import argparse
import shutil
import sys
from pathlib import Path

_MODEL_NAME = "ProsusAI/finbert"


def _write_vocab(out_dir: Path, tokenizer) -> None:
    vocab = tokenizer.get_vocab()
    ids = sorted((i, tok) for tok, i in vocab.items())
    with open(out_dir / "vocab.txt", "w") as f:
        for _, tok in ids:
            f.write(tok + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("models/finbert-onnx"))
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("models/finbert"),
        help="Local HF-layout weights dir; falls back to downloading from HuggingFace Hub.",
    )
    args = parser.parse_args()

    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    if args.source.exists():
        tokenizer = AutoTokenizer.from_pretrained(str(args.source))
        model = AutoModelForSequenceClassification.from_pretrained(str(args.source))
    else:
        tokenizer = AutoTokenizer.from_pretrained(_MODEL_NAME)
        model = AutoModelForSequenceClassification.from_pretrained(_MODEL_NAME)
    model.eval()

    args.out.mkdir(parents=True, exist_ok=True)
    ids = torch.tensor([[1, 3, 4, 5]], dtype=torch.long)
    mask = torch.ones_like(ids)
    with torch.no_grad():
        torch.onnx.export(
            model,
            (ids, mask),
            args.out / "model.onnx",
            input_names=["input_ids", "attention_mask"],
            output_names=["logits"],
            dynamic_axes={
                "input_ids": {0: "batch", 1: "seq"},
                "attention_mask": {0: "batch", 1: "seq"},
                "logits": {0: "batch"},
            },
            opset_version=17,
            dynamo=False,
        )

    _write_vocab(args.out, tokenizer)
    size = sum(p.stat().st_size for p in args.out.glob("model.onnx*"))
    print(f"exported FinBERT (fp32, no quantization) to {args.out} ({size / 1e6:.0f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())