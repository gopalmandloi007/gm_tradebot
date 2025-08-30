# backend/orders.py
import logging
from backend.session import SessionManager

logger = logging.getLogger(__name__)

class OrderService:
    def __init__(self, session: SessionManager):
        self.session = session
        self.client = session.get_client()

    def place_order(self, symbol: str, qty: int, side: str, price: float = None, order_type: str = "MARKET"):
        """
        Place a simple order
        side = BUY or SELL
        """
        payload = {
            "symbol": symbol,
            "quantity": qty,
            "side": side,
            "type": order_type,
        }
        if price:
            payload["price"] = price

        logger.info(f"Placing order: {payload}")
        return self.client.post("/orders/place", json=payload)

    def place_gtt(self, symbol: str, qty: int, entry: float, stop_loss: float, targets: list):
        """
        Place multiple GTT (Good Till Triggered) orders for a symbol
        Example: entry=100, stop_loss=98, targets=[110,120,130]
        """
        gtt_orders = []

        # Stop Loss Order
        gtt_orders.append({
            "symbol": symbol,
            "trigger_type": "LESS_THAN",
            "trigger_price": stop_loss,
            "side": "SELL",
            "quantity": qty,
            "order_type": "SL",
        })

        # Target Orders
        for tgt in targets:
            gtt_orders.append({
                "symbol": symbol,
                "trigger_type": "GREATER_THAN",
                "trigger_price": tgt,
                "side": "SELL",
                "quantity": qty,
                "order_type": "LIMIT",
            })

        results = []
        for g in gtt_orders:
            logger.info(f"Placing GTT order: {g}")
            res = self.client.post("/gtt/place", json=g)
            results.append(res)

        return results
