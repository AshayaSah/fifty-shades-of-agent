from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_analyzer = SentimentIntensityAnalyzer()


def score_text(text: str) -> float:
    return _analyzer.polarity_scores(text)["compound"]
