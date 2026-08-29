_MODEL_NAME = "ProsusAI/finbert"
_LABELS = ["positive", "negative", "neutral"]

_tokenizer = None
_model = None
_has_torch = None


def _load_model():
    global _tokenizer, _model, _has_torch
    if _has_torch is False:
        return False
    if _model is None:
        try:
            import torch  # noqa: F401
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            _tokenizer = AutoTokenizer.from_pretrained(_MODEL_NAME)
            _model = AutoModelForSequenceClassification.from_pretrained(_MODEL_NAME)
            _model.eval()
            _has_torch = True
            return True
        except Exception:
            _has_torch = False
            return False
    return True


def _vader_score(text: str) -> float:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

    return SentimentIntensityAnalyzer().polarity_scores(text)["compound"]


def score_text(text: str) -> float:
    """Score text sentiment using FinBERT (if available) else VADER fallback.

    Returns a compound score from -1 (very negative) to +1 (very positive),
    computed as P(positive) - P(negative) for FinBERT or compound for VADER.
    """
    if _load_model():
        import torch

        inputs = _tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        with torch.no_grad():
            outputs = _model(**inputs)
        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)[0]
        return float(probs[_LABELS.index("positive")] - probs[_LABELS.index("negative")])
    return _vader_score(text)


def score_texts(texts: list[str]) -> dict[int, float]:
    """Batch-score multiple texts in a single forward pass.

    Returns dict mapping index -> compound score.
    Much faster than calling score_text() in a loop.
    Falls back to VADER if torch/transformers not installed (Vercel).
    """
    if not texts:
        return {}
    if _load_model():
        import torch

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
    return {i: _vader_score(t) for i, t in enumerate(texts)}
