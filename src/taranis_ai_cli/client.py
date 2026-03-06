from __future__ import annotations

from typing import Any

import httpx

from taranis_ai_cli.config import Settings


JsonValue = dict[str, Any] | list[Any] | str | int | float | bool | None


class TaranisApiError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None, details: JsonValue = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details


class TaranisApiClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._access_token: str | None = None
        self._client = httpx.Client(
            base_url=settings.base_url,
            timeout=settings.timeout_seconds,
            verify=settings.verify_ssl,
        )

    def close(self) -> None:
        self._client.close()

    def request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | list[Any] | None = None,
    ) -> JsonValue:
        response = self.request(method, path, params=params, json_body=json_body)
        content_type = response.headers.get("content-type", "")
        if "json" not in content_type:
            raise TaranisApiError(
                f"Expected JSON response from {path}, received {content_type or 'unknown content type'}",
                status_code=response.status_code,
                details=response.text,
            )
        return response.json()

    def request_text(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | list[Any] | None = None,
    ) -> str:
        return self.request(method, path, params=params, json_body=json_body).text

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | list[Any] | None = None,
        retry_on_unauthorized: bool = True,
    ) -> httpx.Response:
        auth_mode = self._select_auth_mode()
        headers = self._build_auth_headers(path)
        response = self._client.request(method, path, params=params, json=json_body, headers=headers)

        if response.status_code == 401 and retry_on_unauthorized and auth_mode == "jwt":
            self._access_token = None
            headers = self._build_auth_headers(path)
            response = self._client.request(method, path, params=params, json=json_body, headers=headers)

        if response.is_error:
            raise self._build_error(response)

        return response

    def _build_auth_headers(self, path: str) -> dict[str, str]:
        if path in {"/api/auth/login", "/api/isalive", "/api/static/openapi3_1.yaml"}:
            return {}

        auth_mode = self._select_auth_mode()
        if auth_mode is None:
            return {}

        if auth_mode == "api_key":
            if not self.settings.api_key:
                raise TaranisApiError("TARANIS_API_KEY is required for api_key auth mode")
            return {"Authorization": f"Bearer {self.settings.api_key}"}

        return {"Authorization": f"Bearer {self._ensure_access_token()}"}

    def _select_auth_mode(self) -> str | None:
        if self.settings.auth_mode == "jwt":
            return "jwt"
        if self.settings.auth_mode == "api_key":
            return "api_key"
        if self.settings.username and self.settings.password:
            return "jwt"
        if self.settings.api_key:
            return "api_key"
        return None

    def _ensure_access_token(self) -> str:
        if self._access_token:
            return self._access_token

        if not self.settings.username or not self.settings.password:
            raise TaranisApiError("TARANIS_USERNAME and TARANIS_PASSWORD are required for jwt auth mode")

        response = self._client.post(
            "/api/auth/login",
            json={"username": self.settings.username, "password": self.settings.password},
        )
        if response.is_error:
            raise self._build_error(response)

        payload = response.json()
        access_token = payload.get("access_token")
        if not access_token:
            raise TaranisApiError("Taranis login succeeded but no access_token was returned", details=payload)

        self._access_token = access_token
        return access_token

    @staticmethod
    def _build_error(response: httpx.Response) -> TaranisApiError:
        details: JsonValue
        message = f"Taranis API request failed with status {response.status_code}"

        try:
            details = response.json()
            if isinstance(details, dict):
                message = str(details.get("error") or details.get("message") or message)
        except ValueError:
            details = response.text
            if response.text:
                message = response.text

        return TaranisApiError(message=message, status_code=response.status_code, details=details)
