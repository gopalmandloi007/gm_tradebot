# pages/holdings.py
import streamlit as st
import pandas as pd
from definedge_api import DefinedgeClient
import traceback

def show():
    st.header("📊 Holdings")
    if "client" not in st.session_state or not st.session_state["client"]:
        st.warning("Please login first from Login page.")
        return

    client: DefinedgeClient = st.session_state["client"]

    try:
        resp = client.get_holdings()
        # typical response might be {"status":"SUCCESS","data":[...]} or {"holdings":[...]}
        data = []
        if isinstance(resp, dict):
            data = resp.get("data") or resp.get("holdings") or []
        elif isinstance(resp, list):
            data = resp
        # normalize items to rows
        rows = []
        for h in data:
            # tradingsymbol might be list or object
            ts = h.get("tradingsymbol")
            if isinstance(ts, list):
                # pick NSE if present
                nse = None
                for t in ts:
                    if str(t.get("exchange","")).upper() == "NSE":
                        nse = t
                        break
                if nse is None and ts:
                    nse = ts[0]
            elif isinstance(ts, dict):
                nse = ts
            else:
                nse = {"tradingsymbol": h.get("symbol") or "", "token": h.get("token") or ""}
            symbol = nse.get("tradingsymbol") or h.get("symbol")
            token = nse.get("token") or h.get("token") or ""
            qty = float(h.get("trade_qty") or h.get("dp_qty") or h.get("quantity") or 0)
            avg = float(h.get("avg_buy_price") or h.get("avg_price") or h.get("avgPrice") or 0)
            rows.append({
                "symbol": symbol,
                "token": token,
                "qty": qty,
                "avg_price": avg,
                "raw": h
            })
        df = pd.DataFrame(rows)
        if df.empty:
            st.info("No holdings returned from API.")
            return

        # fetch LTPs (sequentially; for efficiency you can batch later)
        ltps = []
        for idx, r in df.iterrows():
            token = str(r["token"])
            exch = "NSE"
            try:
                q = client.get_quotes(exch, token)
                # extract likely ltp fields
                ltp = None
                if isinstance(q, dict):
                    for k in ("lp","ltp","last_price","lastTradedPrice","lastPrice"):
                        if k in q and q[k] not in (None,""):
                            try:
                                ltp = float(q[k])
                                break
                            except:
                                pass
                    # nested fallback
                    if ltp is None:
                        for v in q.values():
                            if isinstance(v, dict):
                                for k in ("lp","ltp","last_price","lastPrice"):
                                    if k in v and v[k] not in (None,""):
                                        try:
                                            ltp = float(v[k])
                                            break
                                        except:
                                            pass
                ltps.append(ltp)
            except Exception:
                ltps.append(None)

        df["ltp"] = ltps

        # get previous close via historical API (day timeframe)
        prevs = []
        import datetime
        for idx, r in df.iterrows():
            token = str(r["token"])
            exch = "NSE"
            prev = None
            try:
                # build from /to format: ddMMyyyyHHmm
                today = datetime.datetime.now()
                frm = (today - datetime.timedelta(days=30)).strftime("%d%m%Y%H%M")
                to  = today.strftime("%d%m%Y%H%M")
                csv_text = client.historical_csv(segment=exch, token=token, timeframe="day", frm=frm, to=to)
                if csv_text:
                    # CSV without headers — each line: Dateandtime,Open,High,Low,Close,Volume,OI...
                    # we'll parse last non-empty line's 5th value (Close)
                    lines = [ln.strip() for ln in csv_text.splitlines() if ln.strip()]
                    if lines:
                        # find last line before today (or last line)
                        last = lines[-1]
                        parts = last.split(",")
                        if len(parts) >= 5:
                            try:
                                prev = float(parts[4])
                            except:
                                prev = None
                prevs.append(prev)
            except Exception:
                prevs.append(None)

        df["prev_close"] = prevs

        # compute pnl columns
        df["invested"] = df["qty"] * df["avg_price"]
        df["current_value"] = df["qty"] * df["ltp"].fillna(0)
        df["today_pnl"] = (df["ltp"].fillna(0) - df["prev_close"].fillna(0)) * df["qty"]
        df["overall_pnl"] = df["current_value"] - df["invested"]
        # pretty show
        st.dataframe(df[["symbol","token","qty","avg_price","ltp","prev_close","today_pnl","overall_pnl"]], use_container_width=True)
    except Exception as e:
        st.error(f"Failed to fetch holdings: {e}")
        st.text(traceback.format_exc())
