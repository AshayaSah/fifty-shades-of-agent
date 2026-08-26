import spacy

from news_scraper import sentiment

_nlp = spacy.load("en_core_web_sm")

_EVENT_RULES = [
    ("earnings", [
        "earnings", "revenue", "profit", "loss", "quarterly results",
        "financial results", "beat estimates", "missed estimates",
        "eps", "net income", "guidance", "forecast", "dividend",
    ]),
    ("lawsuit", [
        "lawsuit", "sue", "sued", "litigation", "settlement",
        "court", "legal action", "alleged", "fraud", " SEC charges",
    ]),
    ("acquisition", [
        "acquire", "acquired", "acquisition", "merger", "buyout",
        "takeover", "deal to buy", "purchase", "stake in",
    ]),
    ("product_launch", [
        "launch", "unveil", "unveiled", "new product", "new device",
        "release", "released", "announce", "debuts", "introduces",
    ]),
    ("market_movement", [
        "stock", "shares", "rally", "surge", "plunge", "drop",
        "fell", "rose", "gained", "lost", "trading", "volatility",
        "all-time high", "record high", "bear", "bull",
    ]),
    ("executive", [
        "ceo", "cfo", "cto", "appoint", "appointed", "resign",
        "resigned", "fired", "hire", "hired", "leadership",
        "executive", "board", "director",
    ]),
    ("regulation", [
        "regulator", "regulation", "fine", "penalty", "investigation",
        "antitrust", "compliance", "sanction", "ban", "approve",
    ]),
]


def extract_entities(text: str) -> dict[str, list[str]]:
    """Extract named entities from text using spaCy.

    Returns a dict with keys: orgs, people, locations — each a deduplicated
    list of entity strings.
    """
    if not text:
        return {"orgs": [], "people": [], "locations": []}
    doc = _nlp(text[:10000])
    orgs, people, locations = set(), set(), set()
    for ent in doc.ents:
        if ent.label_ == "ORG":
            orgs.add(ent.text.strip())
        elif ent.label_ == "PERSON":
            people.add(ent.text.strip())
        elif ent.label_ in ("GPE", "LOC", "COUNTRY"):
            locations.add(ent.text.strip())
    return {
        "orgs": sorted(orgs),
        "people": sorted(people),
        "locations": sorted(locations),
    }


def classify_event(text: str) -> str:
    """Classify the primary event type of an article.

    Returns one of: earnings, lawsuit, acquisition, product_launch,
    market_movement, executive, regulation, other.
    """
    if not text:
        return "other"
    lower = text.lower()
    scores = {}
    for event_type, keywords in _EVENT_RULES:
        count = sum(1 for kw in keywords if kw in lower)
        if count:
            scores[event_type] = count
    if not scores:
        return "other"
    return max(scores, key=scores.get)


def score_entities(text: str, entities: dict[str, list[str]]) -> dict[str, float]:
    """Compute per-entity sentiment scores.

    For each entity, finds sentences mentioning it and averages
    their FinBERT scores. Returns dict mapping entity name -> score.
    """
    if not text or not entities:
        return {}

    doc = _nlp(text[:10000])
    sentences = [sent.text for sent in doc.sents]

    all_entity_names = (
        entities.get("orgs", [])
        + entities.get("people", [])
        + entities.get("locations", [])
    )

    entity_scores = {}
    for name in all_entity_names:
        matching = [s for s in sentences if name in s]
        if matching:
            scores = [sentiment.score_text(s) for s in matching]
            entity_scores[name] = round(sum(scores) / len(scores), 4)

    return entity_scores
