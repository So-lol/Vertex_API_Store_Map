from __future__ import annotations

from decimal import Decimal
from typing import Any

import requests

from .config import VertexConfig


StoreRow = dict[str, str]


class VertexAPIError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None, response_text: str = "") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


def _money_as_number(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01")))


def build_supply_payload(store: StoreRow, config: VertexConfig) -> dict[str, Any]:
    return {
        "saleMessageType": "QUOTATION",
        "transactionType": "SALE",
        "seller": {
            "company": config.company,
        },
        "customer": {
            "customerCode": {
                "value": str(store["store_id"]),
            },
            "destination": {
                "streetAddress1": store["street"],
                "city": store["city"],
                "mainDivision": store["state"],
                "postalCode": store["postal_code"],
                "country": store["country"],
            },
        },
        "lineItems": [
            {
                "lineItemNumber": 1,
                "lineType": {
                    "value": "SALE",
                },
                "product": {
                    "value": config.product_code,
                },
                "quantity": {
                    "value": 1,
                },
                "unitPrice": _money_as_number(config.unit_price),
            }
        ],
    }


class VertexClient:
    def __init__(self, config: VertexConfig) -> None:
        self.config = config
        self.session = requests.Session()
        self.session.auth = (config.username, config.password)
        self.session.headers.update({"Accept": "application/json"})

    def quote_store(self, store: StoreRow) -> dict[str, Any]:
        payload = build_supply_payload(store, self.config)
        try:
            response = self.session.post(
                self.config.supplies_url,
                json=payload,
                timeout=self.config.timeout_seconds,
                verify=self.config.verify_ssl,
            )
        except requests.RequestException as exc:
            raise VertexAPIError(f"Vertex request failed: {exc}") from exc

        if not response.ok:
            raise VertexAPIError(
                f"Vertex returned HTTP {response.status_code}",
                status_code=response.status_code,
                response_text=response.text,
            )

        try:
            return response.json()
        except ValueError as exc:
            raise VertexAPIError("Vertex response was not valid JSON", response_text=response.text) from exc

