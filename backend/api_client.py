# backend/api_client.py
import logging
from typing import Any, Dict, Optional
import requests

log = logging.getLogger("backend.api_client")
log.setLevel(logging.INFO)

# Base endpoints as per your API docs
BASE_AUTH = "https://signin.definedgesecurities.com/auth/realms/debroking/dsbpkc"
BASE_API  = "https://integrate.definedgesecurities.com/dart/v1"
BASE_DATA = "https://data.definedgesecurities.com/sds"
BASE_FILES = "https://app.definedgesecurities.com/public"

class APIError(Exception):
    pass

class APIClient:
    """
    Thin HTTP client for Definedge endpoints. Session-key (api_session_key) is placed
    into Authorization header (raw) as required by your docs.
    """
    def __init__(
        self,
        api_token: Optional[str] = None,
        api_secret: Optional[str] = None,
        api_session_key: Optional[str] = None,
        susertoken: Optional[str] = None,
        uid: Optional[str] = None,
        actid: Optional[str] = None,
        timeout: int = 20,
    ):
        self.api_token = api_token
        self.api_secret = api_secret
        self.api_session_key = api_session_key
        self.susertoken = susertoken
        self.uid = uid
        self.actid = actid or uid
        self.timeout = timeout
        self._session = requests.Session()

    # ---------- auth ----------
    def auth_step1(self) -> Dict[str, Any]:
        if not self.api_token:
            raise APIError("api_token missing for auth_step1")
        url = f"{BASE_AUTH}/login/{self.api_token}"
        headers = {}
        if self.api_secret:
            headers["api_secret"] = self.api_secret
        r = self._session.get(url, headers=headers, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def auth_step2(self, otp_token: str, otp_code: str) -> Dict[str, Any]:
        url = f"{BASE_AUTH}/token"
        payload = {"otp_token": otp_token or "", "otp": str(otp_code)}
        r = self._session.post(url, json=payload, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    # ---------- low-level http helpers ----------
    def _headers(self) -> Dict[str, str]:
        hdr = {"Content-Type": "application/json"}
        if self.api_session_key:
            # Per docs: Authorization: Actual value of api_session_key
            hdr["Authorization"] = self.api_session_key
        return hdr

    def get(self, path: str) -> Any:
        url = path if path.startswith("http") else f"{BASE_API}{path}"
        r = self._session.get(url, headers=self._headers(), timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def post(self, path: str, json: Optional[Dict[str, Any]] = None) -> Any:
        url = path if path.startswith("http") else f"{BASE_API}{path}"
        r = self._session.post(url, headers=self._headers(), json=json or {}, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    # ---------- trading endpoints ----------
    def holdings(self) -> Any:
        return self.get("/holdings")

    def positions(self) -> Any:
        return self.get("/positions")

    def orders(self) -> Any:
        return self.get("/orders")

    def order(self, order_id: str) -> Any:
        return self.get(f"/order/{order_id}")

    def trades(self) -> Any:
        return self.get("/trades")

    def place_order(self, payload: Dict[str, Any]) -> Any:
        return self.post("/placeorder", json=payload)

    def modify_order(self, payload: Dict[str, Any]) -> Any:
        return self.post("/modify", json=payload)

    def cancel_order(self, order_id: str) -> Any:
        return self.get(f"/cancel/{order_id}")

    def slice_order(self, payload: Dict[str, Any]) -> Any:
        return self.post("/sliceorder", json=payload)

    def product_conversion(self, payload: Dict[str, Any]) -> Any:
        return self.post("/productconversion", json=payload)

    # ---------- gtt / oco ----------
    def gtt_orders(self) -> Any:
        return self.get("/gttorders")

    def gtt_place(self, payload: Dict[str, Any]) -> Any:
        return self.post("/gttplaceorder", json=payload)

    def gtt_modify(self, payload: Dict[str, Any]) -> Any:
        return self.post("/gttmodify", json=payload)

    def gtt_cancel(self, alert_id: str) -> Any:
        return self.get(f"/gttcancel/{alert_id}")

    def oco_place(self, payload: Dict[str, Any]) -> Any:
        return self.post("/ocoplaceorder", json=payload)

    def oco_modify(self, payload: Dict[str, Any]) -> Any:
        return self.post("/ocomodify", json=payload)

    def oco_cancel(self, alert_id: str) -> Any:
        return self.get(f"/ococancel/{alert_id}")

    # ---------- limits/margin/span ----------
    def limits(self) -> Any:
        return self.get("/limits")

    def margin(self) -> Any:
        return self.get("/margin")

    def span_calculator(self, payload: Dict[str, Any]) -> Any:
        return self.post("/spancalculator", json=payload)

    # ---------- quotes/security ----------
    def quote(self, exchange: str, token: str) -> Any:
        return self.get(f"/quotes/{exchange}/{token}")

    def security_info(self, exchange: str, token: str) -> Any:
        return self.get(f"/securityinfo/{exchange}/{token}")

    # ---------- historical/master ----------
    def download_master_zip(self, segment_zip_name: str, dest_path: str) -> str:
        url = f"{BASE_FILES}/{segment_zip_name}"
        with self._session.get(url, stream=True, timeout=self.timeout) as r:
            r.raise_for_status()
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(1024 * 32):
                    f.write(chunk)
        return dest_path

    def historical_csv(self, segment: str, token: str, timeframe: str, frm: str, to: str) -> str:
        url = f"{BASE_DATA}/history/{segment}/{token}/{timeframe}/{frm}/{to}"
        r = self._session.get(url, headers=self._headers(), timeout=self.timeout)
        r.raise_for_status()
        return r.text
