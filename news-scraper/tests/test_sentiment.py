from news_scraper.sentiment import score_text


def test_positive():
    assert score_text("The company delighted investors with excellent earnings, surpassing all expectations.") > 0.3


def test_negative():
    assert score_text("The company faces a massive lawsuit after missing revenue targets badly.") < -0.3


def test_neutral():
    score = score_text("The company reported quarterly earnings on Tuesday.")
    assert -0.2 < score < 0.2
