import spacy

from news_scraper import sentiment

_nlp = None


def _get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp

# Small cache so the same text is only parsed once per article, even when
# entity extraction and entity scoring both need the spaCy Doc.
_doc_cache: dict[int, "spacy.tokens.doc.Doc"] = {}


def parse_article(text: str | None) -> "spacy.tokens.doc.Doc | None":
    if not text:
        return None
    key = hash(text[:10000])
    doc = _doc_cache.get(key)
    if doc is None:
        doc = _get_nlp()(text[:10000])
        if len(_doc_cache) >= 256:
            _doc_cache.clear()
        _doc_cache[key] = doc
    return doc

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


def _extract_entities_from_doc(doc) -> dict[str, list[str]]:
    if doc is None:
        return {"orgs": [], "people": [], "locations": []}
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


def extract_entities(text: str, doc=None) -> dict[str, list[str]]:
    """Extract named entities from text using spaCy.

    Args:
        text: Article text.
        doc: Optional pre-parsed spaCy Doc (via `parse_article`) to avoid a
            second parse when callers have already parsed the text.

    Returns a dict with keys: orgs, people, locations — each a deduplicated
    list of entity strings.
    """
    doc = doc if doc is not None else parse_article(text)
    return _extract_entities_from_doc(doc)


def analyze_article(text: str) -> tuple[dict[str, list[str]], str, dict[str, float]]:
    """Analyze one article with a single spaCy parse.

    Combines entity extraction, event classification, and per-entity sentiment
    scoring so the text is parsed only once (roughly 3x faster than calling
    each helper separately).

    Returns: (entities, event_type, entity_scores).
    """
    doc = parse_article(text)
    entities = _extract_entities_from_doc(doc)
    event_type = classify_event(text)
    entity_scores = score_entities(text, entities, doc=doc)
    return entities, event_type, entity_scores


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


def score_entities(text: str, entities: dict[str, list[str]], doc=None) -> dict[str, float]:
    """Compute per-entity sentiment scores using VADER.

    For each entity, finds sentences mentioning it and averages their
    VADER compound scores. VADER is rule-based and effectively free; running
    FinBERT per entity sentence was the dominant hotspot on constrained
    hardware (~1s per sentence on 2 vCPU) and is only used for article-level
    sentiment now.

    Args:
        text: Article text.
        entities: Entity dict from `extract_entities`.
        doc: Optional pre-parsed spaCy Doc (kept for API compatibility).
    """
    if not text or not entities:
        return {}

    doc = doc if doc is not None else parse_article(text)
    if doc is None:
        return {}
    sentences = [sent.text for sent in doc.sents]

    all_entity_names = (
        entities.get("orgs", [])
        + entities.get("people", [])
        + entities.get("locations", [])
    )

    entity_sentences: dict[str, list[str]] = {}
    for name in all_entity_names:
        matching = [s for s in sentences if name in s]
        if matching:
            entity_sentences[name] = matching

    if not entity_sentences:
        return {}

    all_sents = []
    sent_to_entities: dict[int, list[str]] = {}
    for name, sents in entity_sentences.items():
        for s in sents:
            idx = len(all_sents)
            all_sents.append(s)
            sent_to_entities.setdefault(idx, []).append(name)

    all_scores = {i: sentiment.vader_score(s) for i, s in enumerate(all_sents)}

    entity_accum: dict[str, list[float]] = {}
    for idx, score in all_scores.items():
        for name in sent_to_entities[idx]:
            entity_accum.setdefault(name, []).append(score)

    return {
        name: round(sum(vals) / len(vals), 4)
        for name, vals in entity_accum.items()
    }
