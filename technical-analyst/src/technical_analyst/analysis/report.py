from dataclasses import asdict, dataclass, field


@dataclass
class TechnicalAnalysisReport:
    symbol: str
    interval: str
    as_of: str  # ISO 8601 timestamp
    source: str  # which provider produced the underlying price data
    verdict: str
    confidence: float
    reasons: list[str]
    support: float
    resistance: float
    suggested_stop_loss: float
    suggested_take_profit: float
    indicators: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)
