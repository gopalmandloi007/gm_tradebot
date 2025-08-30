# backend/session.py
import logging
from typing import Optional
import pyotp
from .api_client import APIClient

log = logging.getLogger("backend.session")
log.setLevel(logging.INFO)

class SessionError(Exception):
    pass

class SessionManager:
    """
    Create and maintain a session. Use create_session(otp_code=None) to login.
    If totp_secret is provided, TOTP will be generated automatically.
    Returns an APIClient instance pre-populated with api_session_key & susertoken.
    """
    def __init__(self, api_token: Optional[str] = None, api_secret: Optional[str] = None, totp_secret: Optional[str] = None):
        # You can pass token/secret programmatically or rely on Streamlit secrets (frontend code will pass)
        self.api_token = api_token
        self.api_secret = api_secret
        self.totp_secret = totp_secret

        self.api_session_key: Optional[str] = None
        self.susertoken: Optional[str] = None
        self.uid: Optional[str] = None
        self.actid: Optional[str] = None

    def create_session(self, otp_code: Optional[str] = None) -> APIClient:
        if not self.api_token:
            raise SessionError("api_token required for session creation")
        if not self.api_secret:
            raise SessionError("api_secret required for session creation")

        client = APIClient(api_token=self.api_token, api_secret=self.api_secret)

        # step 1
        try:
            s1 = client.auth_step1()
        except Exception as e:
            log.exception("auth_step1 failed")
            raise SessionError(f"auth_step1 failed: {e}")

        otp_token = None
        if isinstance(s1, dict):
            for k in ("otp_token", "otpToken", "otp_request_token", "request_token"):
                if k in s1:
                    otp_token = s1.get(k)
                    break

        # generate totp if totp_secret provided
        if self.totp_secret and not otp_code:
            try:
                otp_code = pyotp.TOTP(self.totp_secret).now()
            except Exception as e:
                log.exception("TOTP generation failed")
                raise SessionError(f"TOTP generation failed: {e}")

        if not otp_code:
            raise SessionError("OTP code required. Provide totp_secret or pass otp_code to create_session()")

        # step 2
        try:
            s2 = client.auth_step2(otp_token=otp_token or "", otp_code=str(otp_code))
        except Exception as e:
            log.exception("auth_step2 failed")
            raise SessionError(f"auth_step2 failed: {e}")

        if isinstance(s2, dict):
            # flexible extraction
            self.api_session_key = s2.get("api_session_key") or s2.get("apiSessionKey") or s2.get("api_key") or s2.get("apiKey")
            self.susertoken = s2.get("susertoken") or s2.get("susertoken")
            self.uid = s2.get("uid") or s2.get("user") or s2.get("actid")
            self.actid = s2.get("actid") or self.uid

        if not self.api_session_key:
            raise SessionError(f"Login response missing api_session_key: {s2}")

        final_client = APIClient(
            api_token=self.api_token,
            api_secret=self.api_secret,
            api_session_key=self.api_session_key,
            susertoken=self.susertoken,
            uid=self.uid,
            actid=self.actid
        )
        log.info("Session created for uid=%s", self.uid)
        return final_client
