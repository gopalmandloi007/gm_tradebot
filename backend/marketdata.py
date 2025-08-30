# backend/market_data.py
import logging
from typing import Optional
from .api_client import APIClient

log = logging.getLogger("backend.market_data")
log.setLevel(logging.INFO)

class MarketDataService:
    def __init__(self, api_client: APIClient):
        self.api_client = api_client

    def ltp(self, exchange: str, token: str) -> Optional[float]:
        try:
            q = self.api_client.quote(exchange, token)
        except Exception as e:
            log.error("quote failed for %s|%s: %s", exchange, token, e)
            return None

        if isinstance(q, dict):
            for k in ("lp", "ltp", "last_price", "lastTradedPrice", "lastPrice"):
                if k in q and q[k] not in (None, ""):
                    try:
                        return float(q[k])
                    except Exception:
                        continue
            # nested fallback
            for v in q.values():
                if isinstance(v, dict):
                    for k in ("lp", "ltp", "last_price", "lastTradedPrice", "lastPrice"):
                        if k in v and v[k] not in (None, ""):
                            try:
                                return float(v[k])
                            except Exception:
                                continue
        return None
