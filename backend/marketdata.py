import logging
from typing import Optional
from .api_client import APIClient

log = logging.getLogger("backend.marketdata")
log.setLevel(logging.INFO)

class MarketDataService:
    def __init__(self, api_client: APIClient):
        self.api_client = api_client

    def ltp(self, exchange: str, token: str) -> Optional[float]:
        try:
            q = self.api_client.quote(exchange, token)
        except Exception as e:
            log.error("quote error: %s", e); return None
        if not isinstance(q, dict): return None
        for k in ("lp","ltp","last_price","lastTradedPrice","lastPrice"):
            v = q.get(k)
            if v not in (None,""):
                try:
                    return float(v)
                except Exception:
                    pass
        # nested dict fallback
        for v in q.values():
            if isinstance(v, dict):
                for k in ("lp","ltp","last_price","lastTradedPrice","lastPrice"):
                    if k in v and v[k] not in (None,""):
                        try:
                            return float(v[k])
                        except Exception:
                            pass
        return None
