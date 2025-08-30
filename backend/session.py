import logging
from typing import Optional
import pyotp
from .api_client import APIClient

log = logging.getLogger("backend.session")
log.setLevel(logging.INFO)

class SessionError(Exception):
    pass

class SessionManager:
    def __init__(self, api_token: str, api_secret: str, totp_secret: Optional[str]=None):
        self.api_token = api_token
        self.api_secret = api_secret
        self.totp_secret = totp_secret
        self.api_session_key = None
        self.susertoken = None
        self.uid = None
        self.actid = None

    def create_session(self, otp_code: Optional[str]=None) -> APIClient:
        ac = APIClient(api_token=self.api_token, api_secret=self.api_secret)
        try:
            s1 = ac.auth_step1()
        except Exception as e:
            raise SessionError(f"auth_step1 failed: {e}")
        otp_token = None
        if isinstance(s1, dict):
            for k in ('otp_token','otpToken','request_token','otp_request_token'):
                if k in s1:
                    otp_token = s1.get(k); break
        if self.totp_secret and not otp_code:
            try:
                otp_code = pyotp.TOTP(self.totp_secret).now()
            except Exception as e:
                raise SessionError(f"TOTP generation failed: {e}")
        if not otp_code:
            raise SessionError("OTP required: pass otp_code or set totp_secret.")
        try:
            s2 = ac.auth_step2(otp_token=otp_token or "", otp_code=str(otp_code))
        except Exception as e:
            raise SessionError(f"auth_step2 failed: {e}")
        if isinstance(s2, dict):
            self.api_session_key = s2.get('api_session_key') or s2.get('apiSessionKey')
            self.susertoken = s2.get('susertoken')
            self.uid = s2.get('uid') or s2.get('actid')
            self.actid = s2.get('actid') or self.uid
        if not self.api_session_key:
            raise SessionError(f"Login response missing api_session_key: {s2}")
        client = APIClient(api_token=self.api_token, api_secret=self.api_secret,
                           api_session_key=self.api_session_key, susertoken=self.susertoken,
                           uid=self.uid, actid=self.actid)
        log.info("Session created uid=%s", self.uid)
        return client
