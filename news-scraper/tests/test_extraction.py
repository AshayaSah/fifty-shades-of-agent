from news_scraper.extraction import classify_event, extract_entities


def test_extract_entities_orgs():
    text = "Apple Inc reported strong quarterly results. Tim Cook praised the team."
    result = extract_entities(text)
    assert "Apple Inc" in result["orgs"]
    assert "Tim Cook" in result["people"]


def test_extract_entities_empty():
    assert extract_entities("") == {"orgs": [], "people": [], "locations": []}


def test_extract_entities_deduplication():
    text = "Apple said Apple is growing. Apple reported revenue."
    result = extract_entities(text)
    assert result["orgs"].count("Apple") == 1


def test_classify_event_earnings():
    text = "Apple reported quarterly earnings and revenue that beat analyst estimates."
    assert classify_event(text) == "earnings"


def test_classify_event_lawsuit():
    text = "The company faces a lawsuit alleging fraud and securities violations."
    assert classify_event(text) == "lawsuit"


def test_classify_event_acquisition():
    text = "Microsoft announced plans to acquire the startup for $2 billion."
    assert classify_event(text) == "acquisition"


def test_classify_event_product_launch():
    text = "Apple unveiled its new iPhone at the product launch event."
    assert classify_event(text) == "product_launch"


def test_classify_event_market_movement():
    text = "Shares plunged 15% in after-hours trading following the report."
    assert classify_event(text) == "market_movement"


def test_classify_event_executive():
    text = "The CEO resigned and the board appointed a new director."
    assert classify_event(text) == "executive"


def test_classify_event_regulation():
    text = "Regulators launched an antitrust investigation into the company."
    assert classify_event(text) == "regulation"


def test_classify_event_other():
    text = "The weather was nice on Tuesday."
    assert classify_event(text) == "other"


def test_classify_event_empty():
    assert classify_event("") == "other"
