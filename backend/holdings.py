import logging
from typing import Any, Dict, List, Tuple
import pandas as pd
from .api_client import APIClient
from .marketdata import MarketDataService
from .historical import HistoricalService

log = logging.getLogger("backend.holdings")
log.setLevel(logging.INFO)

def _choose_nse_record(tradingsymbol_field: Any) -> Dict[str, Any]:
    if isinstance(tradingsymbol_field, list) and tradingsymbol_field:
        for rec in tradingsymbol_field:
            if str(rec.get('exchange','')).upper() == 'NSE': return rec
        return tradingsymbol_field[0]
    if isinstance(tradingsymbol_field, dict): return tradingsymbol_field
    return {'exchange':'NSE','tradingsymbol': str(tradingsymbol_field or ''),'token':''}

class HoldingsService:
    def __init__(self, api_client: APIClient):
        self.client = api_client
        self.market = MarketDataService(api_client)
        self.hist = HistoricalService(api_client)

    def fetch_raw(self) -> List[Dict[str, Any]]:
        resp = self.client.holdings()
        if isinstance(resp, dict):
            data = resp.get('data') or resp.get('holdings') or []
            if isinstance(data, dict): data = list(data.values())
            return data
        if isinstance(resp, list): return resp
        return []

    def enriched_table(self) -> Tuple[pd.DataFrame, Dict[str, float]]:
        items = self.fetch_raw()
        rows: List[Dict[str, Any]] = []
        totals = {'invested':0.0,'current':0.0,'today_pnl':0.0,'overall_pnl':0.0}
        for h in items:
            nse = _choose_nse_record(h.get('tradingsymbol'))
            exch = (nse.get('exchange') or 'NSE').upper()
            token = str(nse.get('token') or '').strip()
            sym = nse.get('tradingsymbol') or h.get('symbol') or token
            qty = float(h.get('trade_qty') or h.get('dp_qty') or h.get('quantity') or 0)
            avg = float(h.get('avg_buy_price') or h.get('avg_price') or 0.0)
            ltp = self.market.ltp(exchange=exch, token=token) if token else None
            prev = self.hist.previous_close(segment=exch, token=token, timeframe='day')
            invested = qty * avg
            current = qty * (ltp or 0.0)
            today_pnl = ((ltp or 0.0) - (prev or 0.0)) * qty if prev is not None else 0.0
            overall = current - invested
            chg_pct = (((ltp or 0.0) - (prev or 0.0)) / prev * 100.0) if (prev and prev != 0) else None
            row = {
                'symbol': sym, 'exchange': exch, 'token': token, 'qty': qty,
                'avg_price': avg, 'ltp': ltp, 'prev_close': prev, 'today_change_%': chg_pct,
                'invested': invested, 'current_value': current, 'today_pnl': today_pnl, 'overall_pnl': overall
            }
            rows.append(row)
            totals['invested'] += invested
            totals['current'] += current
            totals['today_pnl'] += today_pnl
            totals['overall_pnl'] += overall
        df = pd.DataFrame(rows)
        cols = ['symbol','exchange','token','qty','avg_price','ltp','prev_close','today_change_%','invested','current_value','today_pnl','overall_pnl']
        df = df[cols] if not df.empty else df
        return df, totals
