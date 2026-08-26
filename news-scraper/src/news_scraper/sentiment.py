import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

_MODEL_NAME = "ProsusAI/finbert"
_LABELS = ["positive", "negative", "neutral"]

_tokenizer = None
_model = None


def _load_model():
    global _tokenizer, _model
    if _model is None:
        _tokenizer = AutoTokenizer.from_pretrained(_MODEL_NAME)
        _model = AutoModelForSequenceClassification.from_pretrained(_MODEL_NAME)
        _model.eval()


def score_text(text: str) -> float:
    """Score text sentiment using FinBERT.

    Returns a compound score from -1 (very negative) to +1 (very positive),
    computed as P(positive) - P(negative).
    """
    _load_model()
    inputs = _tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        outputs = _model(**inputs)
    probs = torch.nn.functional.softmax(outputs.logits, dim=-1)[0]
    return float(probs[_LABELS.index("positive")] - probs[_LABELS.index("negative")])


def score_texts(texts: list[str]) -> dict[int, float]:
    """Batch-score multiple texts in a single forward pass.

    Returns dict mapping index -> compound score.
    Much faster than calling score_text() in a loop.
    """
    if not texts:
        return {}
    _load_model()
    inputs = _tokenizer(
        texts, return_tensors="pt", truncation=True,
        max_length=512, padding=True,
    )
    with torch.no_grad():
        outputs = _model(**inputs)
    probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
    pos_idx = _LABELS.index("positive")
    neg_idx = _LABELS.index("negative")
    return {
        i: float(probs[i][pos_idx] - probs[i][neg_idx])
        for i in range(len(texts))
    }
