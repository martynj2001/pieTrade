import threading
import time

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api", tags=["account"])
_cache: dict = {"value": None, "expires_at": 0.0}
_client = None
_lock = threading.Lock()


@router.get("/account")
def account():
    global _client
    with _lock:
        now = time.monotonic()
        if _cache["value"] is not None and now < _cache["expires_at"]:
            return _cache["value"]
        try:
            import config
            import oanda_api_handler
            from oandapyV20 import API

            if _client is None:
                _client = API(
                    access_token=config.OANDA_API_KEY.strip(),
                    environment=config.OANDA_ENVIRON,
                )
            result = oanda_api_handler.account_summery(_client, retries=1)
            if result is None:
                raise RuntimeError("Account summary unavailable")
            _cache["value"] = result
            _cache["expires_at"] = time.monotonic() + 30
            return result
        except Exception as exc:
            raise HTTPException(status_code=503, detail="Account unavailable") from exc