"""Sentiment scoring with two interchangeable FinBERT backends.

The same ProsusAI/finbert weights can run through either engine, chosen by
the device configuration so we keep full-fidelity local development while
fitting the 512 MB Render free tier:

    SECTION A - torch (transformers): the original runtime. Picked first in
    "auto" mode whenever torch + transformers are importable, i.e. on a dev
    machine or any host installed with the `ml` extra (`uv sync --extra ml`).
    RAM: ~0.6-1.1 GB.

    SECTION B - onnxruntime: the *same* weights exported to fp32 ONNX (no
    quantization, no torch). Picked in "auto" mode when torch is absent and
    models/finbert-onnx/model.onnx is present (the deployed image exports it
    at build time). RAM: ~0.4-0.6 GB.

    VADER - last-resort fallback when neither engine is usable.

Force a choice with the environment variable:

    NEWS_SCRAPER_BACKEND=auto|torch|onnx|vader
"""

import importlib.util
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_MODEL_NAME = "ProsusAI/finbert"
_MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "models" / "finbert"
_ONNX_MODEL_FILE = (
    Path(__file__).resolve().parent.parent.parent / "models" / "finbert-onnx" / "model.onnx"
)
_LABELS = ["positive", "negative", "neutral"]

TORCH = "torch"
ONNX = "onnx"
VADER = "vader"
_BACKEND_ENV = "NEWS_SCRAPER_BACKEND"

# ---------------------------------------------------------------------------
# Backend state (resolved once, kept process-wide).
# ---------------------------------------------------------------------------
_backend = None
_torch_tokenizer = None
_torch_model = None
_torch_broken = False
_ort_session = None
_ort_tokenizer = None
_ort_cls = None
_ort_sep = None
_ort_pad = None
_ort_broken = False


# ---------------------------------------------------------------------------
# Backend selection.
# ---------------------------------------------------------------------------
def _torch_importable() -> bool:
    try:
        return importlib.util.find_spec("torch") is not None and importlib.util.find_spec(
            "transformers"
        ) is not None
    except ValueError:
        return False


def _pick_backend() -> str:
    """Auto-select: torch (rich device) > onnx (constrained device) > vader."""
    if _torch_importable():
        return TORCH
    if _ONNX_MODEL_FILE.exists():
        return ONNX
    return VADER


def get_backend() -> str:
    """Return the active scoring backend, resolving it on first call."""
    global _backend
    if _backend is not None:
        return _backend
    force = os.environ.get(_BACKEND_ENV, "auto").strip().lower()
    if force in (TORCH, ONNX, VADER):
        if force == TORCH and _torch_importable():
            _backend = TORCH
        elif force == ONNX and _ONNX_MODEL_FILE.exists():
            _backend = ONNX
        elif force == VADER:
            _backend = VADER
        else:
            logger.warning(
                "requested backend %r unavailable (torch=%s onnx=%s); using auto",
                force, _torch_importable(), _ONNX_MODEL_FILE.exists(),
            )
            _backend = _pick_backend()
    else:
        _backend = _pick_backend()
    logger.info("sentiment backend selected: %s", _backend)
    return _backend


# ---------------------------------------------------------------------------
# SECTION A: torch backend (full-fidelity local / dev / rich hosts).
#   Enabled by NEWS_SCRAPER_BACKEND=torch or auto + torch installed.
#   Loads the original ProsusAI/finbert lazily, fp16 to halve RAM on CPU.
# ---------------------------------------------------------------------------
def _torch_load() -> bool:
    global _torch_tokenizer, _torch_model, _torch_broken
    if _torch_broken:
        return False
    if _torch_model is None:
        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            if _MODEL_DIR.exists():
                _torch_tokenizer = AutoTokenizer.from_pretrained(str(_MODEL_DIR))
                _torch_model = AutoModelForSequenceClassification.from_pretrained(
                    str(_MODEL_DIR), torch_dtype=torch.float16
                )
                logger.info("loaded FinBERT (torch) from %s", _MODEL_DIR)
            else:
                _torch_tokenizer = AutoTokenizer.from_pretrained(_MODEL_NAME)
                _torch_model = AutoModelForSequenceClassification.from_pretrained(
                    _MODEL_NAME, torch_dtype=torch.float16
                )
                logger.warning(
                    "torch weights not found at %s; fell back to HuggingFace Hub", _MODEL_DIR
                )
            _torch_model.eval()
        except Exception as exc:
            _torch_broken = True
            logger.warning("torch backend failed to load: %s", exc)
            return False
    return True


def _torch_score(texts: list[str]) -> dict[int, float]:
    import torch

    inputs = _torch_tokenizer(
        texts, return_tensors="pt", truncation=True, padding=True, max_length=512
    )
    with torch.no_grad():
        logits = _torch_model(**inputs).logits
    probs = torch.nn.functional.softmax(logits, dim=-1)
    pos, neg = _LABELS.index("positive"), _LABELS.index("negative")
    return {i: float(probs[i, pos] - probs[i, neg]) for i in range(len(texts))}


# ---------------------------------------------------------------------------
# SECTION B: onnxruntime backend (constrained RAM / serverless, e.g. 512 MB
#   Render free tier). Same weights in full fp32 - no quantization, no torch.
#   Requires models/finbert-onnx/model.onnx (generated at image build time).
# ---------------------------------------------------------------------------
def _onnx_load() -> bool:
    global _ort_session, _ort_tokenizer, _ort_cls, _ort_sep, _ort_pad, _ort_broken
    if _ort_broken:
        return False
    if _ort_session is None:
        try:
            import onnxruntime as ort
            from tokenizers import Tokenizer, models, normalizers, pre_tokenizers

            vocab_path = _ONNX_MODEL_FILE.parent / "vocab.txt"
            vocab = {}
            with open(vocab_path) as f:
                vocab = {line.rstrip(): i for i, line in enumerate(f)}

            tokenizer = Tokenizer(
                models.WordPiece(vocab, unk_token="[UNK]", max_input_chars_per_word=100)
            )
            tokenizer.normalizer = normalizers.BertNormalizer(lowercase=True)
            tokenizer.pre_tokenizer = pre_tokenizers.BertPreTokenizer()
            tokenizer.enable_truncation(max_length=510)

            options = ort.SessionOptions()
            options.intra_op_num_threads = 1
            session = ort.InferenceSession(
                str(_ONNX_MODEL_FILE), options, providers=["CPUExecutionProvider"]
            )

            _ort_tokenizer = tokenizer
            _ort_cls = vocab["[CLS]"]
            _ort_sep = vocab["[SEP]"]
            _ort_pad = vocab["[PAD]"]
            _ort_session = session
            logger.info("loaded FinBERT (onnxruntime) from %s", _ONNX_MODEL_FILE)
        except Exception as exc:
            _ort_broken = True
            logger.warning("onnxruntime backend failed to load: %s", exc)
            return False
    return True


def _onnx_score(texts: list[str]) -> dict[int, float]:
    import numpy as np

    rows = []
    for text in texts:
        ids = [_ort_cls] + _ort_tokenizer.encode(text).ids[:510] + [_ort_sep]
        rows.append(ids)
    width = max(len(ids) for ids in rows) if rows else 0

    input_ids = np.zeros((len(rows), width), dtype=np.int64)
    attention_mask = np.zeros((len(rows), width), dtype=np.int64)
    for r, ids in enumerate(rows):
        input_ids[r, : len(ids)] = ids
        attention_mask[r, : len(ids)] = 1

    logits = _ort_session.run(["logits"], {"input_ids": input_ids, "attention_mask": attention_mask})[0]
    maxv = logits.max(axis=-1, keepdims=True)
    e = np.exp(logits - maxv)
    probs = e / e.sum(axis=-1, keepdims=True)
    pos, neg = _LABELS.index("positive"), _LABELS.index("negative")
    return {i: float(probs[i, pos] - probs[i, neg]) for i in range(len(texts))}


# ---------------------------------------------------------------------------
# VADER fallback (no model / no engine).
# ---------------------------------------------------------------------------
def _vader_score(text: str) -> float:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

    return SentimentIntensityAnalyzer().polarity_scores(text)["compound"]


def _score_texts(texts: list[str]) -> dict[int, float]:
    if not texts:
        return {}
    backend = get_backend()
    if backend == TORCH and _torch_load():
        return _torch_score(texts)
    if backend == ONNX and _onnx_load():
        return _onnx_score(texts)
    logger.warning("no model backend available; scoring with VADER")
    return {i: _vader_score(t) for i, t in enumerate(texts)}


def score_text(text: str) -> float:
    """Score a single text. Returns -1 (very negative) to +1 (very positive)."""
    scores = _score_texts([text])
    return scores.get(0, 0.0)


def score_texts(texts: list[str]) -> dict[int, float]:
    """Batch-score texts in a single forward pass. Returns dict index -> score."""
    return _score_texts(texts)