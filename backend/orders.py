# backend/orders.py
import logging
from typing import Dict, Any, List
from .api_client import APIClient

log = logging.getLogger("backend.orders")
log.setLevel(logging.INFO)

class OrdersService:
    """
    Orders helper: regular orders and GTT generation/placement.
    """

    def __init__(self, api_client: APIClient):
        self.client = api_client

    def place_regular(
        self,
        exchange: str,
        tradingsymbol: str,
        token: str,
        side: str,
        quantity: int,
        price_type: str = "MARKET",
        product_type: str = "MIS",
        price: float = 0.0,
        trigger_price: float = 0.0,
        validity: str = "DAY",
    ) -> Any:
        payload = {
            "exchange": exchange,
            "tradingsymbol": tradingsymbol,
            "token": token,
            "order_type": side.upper(),
            "product_type": product_type.upper(),
            "price_type": price_type.upper(),
            "quantity": str(int(quantity)),
            "price": str(price or 0),
            "trigger_price": str(trigger_price or 0),
            "validity": validity.upper(),
        }
        log.info("Placing order payload: %s", payload)
        return self.client.place_order(payload)

    def build_gtt_oco_payloads_from_holding(
        self,
        exchange: str,
        tradingsymbol: str,
        token: str,
        qty: int,
        avg_price: float,
        sl_pct: float = -2.0,
        target_pcts: List[float] = (10.0, 20.0, 30.0, 40.0),
    ) -> List[Dict[str, Any]]:
        payloads: List[Dict[str, Any]] = []

        # Stop-loss (below avg)
        if sl_pct is not None:
            sl_price = round(avg_price * (1.0 + sl_pct / 100.0), 2)
            payloads.append({
                "exchange": exchange,
                "tradingsymbol": tradingsymbol,
                "token": token,
                "alert_type": "GTT",
                "side": "SELL",
                "quantity": qty,
                "trigger_price": sl_price,
                "limit_price": sl_price,
                "variety": "OCO",
                "remarks": f"Auto SL {sl_pct:.2f}%"
            })

        # Profit targets
        for pct in target_pcts:
            tp = round(avg_price * (1.0 + pct / 100.0), 2)
            payloads.append({
                "exchange": exchange,
                "tradingsymbol": tradingsymbol,
                "token": token,
                "alert_type": "GTT",
                "side": "SELL",
                "quantity": qty,
                "trigger_price": tp,
                "limit_price": tp,
                "variety": "GTT",
                "remarks": f"Auto Target +{pct:.0f}%"
            })
        return payloads

    def place_gtt_bulk(self, gtt_payloads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        for p in gtt_payloads:
            try:
                r = self.client.gtt_place(p)
                results.append({"ok": True, "req": p, "resp": r})
            except Exception as e:
                results.append({"ok": False, "req": p, "error": str(e)})
        return results
