import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

_MODEL_NAME = "ProsusAI/finbert"

_tokenizer = AutoTokenizer.from_pretrained(_MODEL_NAME)
_model = AutoModelForSequenceClassification.from_pretrained(_MODEL_NAME)
_model.eval()

_LABELS = ["positive", "negative", "neutral"]


def score_text(text: str) -> float:
    """Score text sentiment using FinBERT.

    Returns a compound score from -1 (very negative) to +1 (very positive),
    computed as P(positive) - P(negative).
    """
    inputs = _tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        outputs = _model(**inputs)
    probs = torch.nn.functional.softmax(outputs.logits, dim=-1)[0]
    return float(probs[_LABELS.index("positive")] - probs[_LABELS.index("negative")])
