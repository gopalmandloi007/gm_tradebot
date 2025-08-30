import io, logging
from datetime import datetime, timedelta
from typing import Optional
import pandas as pd
from .api_client import APIClient

log = logging.getLogger("backend.historical")
log.setLevel(logging.INFO)

class HistoricalService:
    def __init__(self, api_client: APIClient):
        self.api_client = api_client

    @staticmethod
    def _csv_to_df(csv_text: str) -> pd.DataFrame:
        if not csv_text or not csv_text.strip(): return pd.DataFrame()
        return pd.read_csv(io.StringIO(csv_text))

    def previous_close(self, segment: str, token: str, timeframe: str='day', ref_date: Optional[datetime]=None, lookback_days: int=20) -> Optional[float]:
        if ref_date is None: ref_date = datetime.now()
        frm = (ref_date - timedelta(days=lookback_days)).strftime('%Y-%m-%d')
        to = ref_date.strftime('%Y-%m-%d')
        csv_text = self.api_client.historical_csv(segment=segment, token=token, timeframe=timeframe, frm=frm, to=to)
        df = self._csv_to_df(csv_text)
        if df.empty: return None
        dt_col = None
        for c in df.columns:
            cl = c.lower()
            if 'date' in cl or 'time' in cl:
                dt_col = c; break
        if dt_col is None: dt_col = df.columns[0]
        df[dt_col] = pd.to_datetime(df[dt_col], errors='coerce')
        df = df.dropna(subset=[dt_col]).sort_values(dt_col)
        cutoff = pd.to_datetime(ref_date).normalize()
        before = df[df[dt_col] < cutoff]
        if before.empty: return None
        last = before.iloc[-1]
        for k in ('close','Close','c'):
            if k in last.index:
                try: return float(last[k])
                except Exception: pass
        for v in reversed(last.values):
            try: return float(v)
            except Exception: pass
        return None
