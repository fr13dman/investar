"""Headline sentiment: FinBERT (finance-tuned BERT, local) when transformers/torch are installed, else VADER."""

import logging
import threading
from dataclasses import dataclass
from typing import Protocol

from app.config import get_settings

log = logging.getLogger(__name__)
FINBERT_MODEL = "ProsusAI/finbert"
VADER_THRESHOLD = 0.05


@dataclass
class Sentiment:
    label: str  # positive | negative | neutral
    score: float  # signed: -1 (negative) .. +1 (positive)


class Analyzer(Protocol):
    name: str

    def analyze(self, texts: list[str]) -> list[Sentiment]: ...


class VaderAnalyzer:
    name = "vader"

    def __init__(self):
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

        self._sia = SentimentIntensityAnalyzer()

    def analyze(self, texts: list[str]) -> list[Sentiment]:
        out = []
        for t in texts:
            c = self._sia.polarity_scores(t)["compound"]
            label = "positive" if c >= VADER_THRESHOLD else "negative" if c <= -VADER_THRESHOLD else "neutral"
            out.append(Sentiment(label, round(c, 4)))
        return out


class FinbertAnalyzer:
    name = "finbert"

    def __init__(self):
        from transformers import pipeline

        self._pipe = pipeline("text-classification", model=FINBERT_MODEL, top_k=None, truncation=True)

    @staticmethod
    def to_sentiment(scores: list[dict]) -> Sentiment:
        probs = {s["label"].lower(): float(s["score"]) for s in scores}
        label = max(probs, key=probs.get)
        return Sentiment(label, round(probs.get("positive", 0.0) - probs.get("negative", 0.0), 4))

    def analyze(self, texts: list[str]) -> list[Sentiment]:
        if not texts:
            return []
        return [self.to_sentiment(r) for r in self._pipe(texts, batch_size=16)]


_analyzer: Analyzer | None = None
_lock = threading.Lock()


def get_analyzer() -> Analyzer:
    global _analyzer
    with _lock:
        if _analyzer is None:
            choice = get_settings().sentiment_model
            if choice in ("auto", "finbert"):
                try:
                    _analyzer = FinbertAnalyzer()
                except Exception as exc:  # noqa: BLE001  (not installed or model download failed)
                    if choice == "finbert":
                        log.warning("FinBERT unavailable (%s); falling back to VADER", exc)
            if _analyzer is None:
                _analyzer = VaderAnalyzer()
        return _analyzer


def set_analyzer(analyzer: Analyzer | None) -> None:
    global _analyzer
    _analyzer = analyzer
