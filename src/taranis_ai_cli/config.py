from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal


AuthMode = Literal["auto", "jwt", "api_key"]


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


@dataclass(slots=True)
class Settings:
    base_url: str
    auth_mode: AuthMode
    username: str | None
    password: str | None
    api_key: str | None
    verify_ssl: bool
    timeout_seconds: float

    @classmethod
    def from_env(cls) -> "Settings":
        base_url = os.getenv("TARANIS_BASE_URL", "http://127.0.0.1:5000").rstrip("/")
        auth_mode = os.getenv("TARANIS_AUTH_MODE", "auto").strip().lower()
        if auth_mode not in {"auto", "jwt", "api_key"}:
            raise ValueError("TARANIS_AUTH_MODE must be one of: auto, jwt, api_key")

        return cls(
            base_url=base_url,
            auth_mode=auth_mode,
            username=os.getenv("TARANIS_USERNAME"),
            password=os.getenv("TARANIS_PASSWORD"),
            api_key=os.getenv("TARANIS_API_KEY"),
            verify_ssl=_env_bool("TARANIS_VERIFY_SSL", True),
            timeout_seconds=float(os.getenv("TARANIS_TIMEOUT", "30")),
        )

    def resolved_auth_mode(self) -> Literal["jwt", "api_key"]:
        if self.auth_mode == "jwt":
            return "jwt"
        if self.auth_mode == "api_key":
            return "api_key"
        if self.username and self.password:
            return "jwt"
        if self.api_key:
            return "api_key"
        raise ValueError(
            "No usable Taranis credentials configured. Set TARANIS_USERNAME/TARANIS_PASSWORD or TARANIS_API_KEY."
        )
