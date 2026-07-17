"""Minimal client for the UpKuajing customs company APIs."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


API_BASE_URL = "https://openapi.upkuajing.com"


class UpKuajingError(RuntimeError):
    """Raised when the API or transport reports an error."""


@dataclass
class ApiResult:
    data: dict[str, Any]
    cost_cents: int


class UpKuajingClient:
    def __init__(self, api_key: str, timeout: float = 120.0) -> None:
        if not api_key.strip():
            raise ValueError("API key must not be empty")
        self.api_key = api_key
        self.timeout = timeout

    def _post(self, endpoint: str, payload: dict[str, Any]) -> ApiResult:
        request = urllib.request.Request(
            f"{API_BASE_URL}{endpoint}",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "upkuajing-tape-masking-film-leads/0.1",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise UpKuajingError(f"HTTP {exc.code}: {detail[:500]}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise UpKuajingError(f"Request failed: {exc}") from exc

        if body.get("code") != 0:
            raise UpKuajingError(
                f"API error {body.get('code')}: {body.get('msg', 'unknown error')}"
            )
        fee = body.get("fee") or {}
        return ApiResult(data=body.get("data") or {}, cost_cents=int(fee.get("apiCost") or 0))

    def search_buyers(self, product: str) -> ApiResult:
        # Phrase searches are exact to prevent "masking film" from matching
        # unrelated terms such as "thick film". Single words stay fuzzy and
        # are filtered again locally.
        is_phrase = len(product.split()) > 1
        return self._post(
            "/agent/customs/company/list",
            {
                "companyType": 2,
                "products": [product],
                "existEmail": 1,
                "isExact": is_phrase,
                "sorting_field": "tradeCount",
                "sorting_direction": "desc",
            },
        )

    def get_company_contacts(self, company_ids: list[int]) -> ApiResult:
        if not 1 <= len(company_ids) <= 20:
            raise ValueError("company_ids must contain between 1 and 20 IDs")
        return self._post(
            "/agent/customs/company/contact/batch", {"companyIds": company_ids}
        )

