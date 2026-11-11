from app.services import sentiment
from app.services.sentiment import FinbertAnalyzer, VaderAnalyzer


def test_vader_labels():
    out = VaderAnalyzer().analyze(["Record profits and a great quarter", "Company faces fraud lawsuit and huge losses", "The meeting is on Tuesday"])
    assert [s.label for s in out] == ["positive", "negative", "neutral"]
    assert out[0].score > 0 > out[1].score


def test_finbert_score_mapping():
    s = FinbertAnalyzer.to_sentiment([{"label": "positive", "score": 0.7}, {"label": "negative", "score": 0.1},
                                      {"label": "neutral", "score": 0.2}])
    assert s.label == "positive" and round(s.score, 2) == 0.6
    s = FinbertAnalyzer.to_sentiment([{"label": "Negative", "score": 0.8}, {"label": "neutral", "score": 0.2}])
    assert s.label == "negative" and s.score == -0.8


def test_get_analyzer_vader_setting(monkeypatch):
    from app.config import get_settings

    sentiment.set_analyzer(None)
    monkeypatch.setattr(get_settings(), "sentiment_model", "vader")
    assert sentiment.get_analyzer().name == "vader"
    sentiment.set_analyzer(None)


def test_get_analyzer_falls_back_when_finbert_unavailable(monkeypatch):
    from app.config import get_settings

    def boom(self):
        raise ImportError("no transformers")

    sentiment.set_analyzer(None)
    monkeypatch.setattr(get_settings(), "sentiment_model", "auto")
    monkeypatch.setattr(FinbertAnalyzer, "__init__", boom)
    assert sentiment.get_analyzer().name == "vader"
    sentiment.set_analyzer(None)
