from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from dotenv import load_dotenv


def _as_bool(value: str | None, default: bool = True) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _as_decimal(value: str | None, default: str) -> Decimal:
    raw_value = value if value not in (None, "") else default
    try:
        return Decimal(str(raw_value))
    except InvalidOperation as exc:
        raise ValueError(f"Invalid decimal value: {raw_value}") from exc


def _as_float(value: str | None, default: float) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"Invalid float value: {value}") from exc


@dataclass(frozen=True)
class VertexConfig:
    base_url: str
    username: str
    password: str
    verify_ssl: bool
    company: str
    product_code: str
    unit_price: Decimal
    rate_limit_seconds: float
    timeout_seconds: float = 30.0

    @property
    def supplies_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/v2/supplies"


def load_config(require_vertex_credentials: bool = True) -> VertexConfig:
    load_dotenv()

    config = VertexConfig(
        base_url=os.getenv("VERTEX_BASE_URL", "").strip(),
        username=os.getenv("VERTEX_USERNAME", "").strip(),
        password=os.getenv("VERTEX_PASSWORD", "").strip(),
        verify_ssl=_as_bool(os.getenv("VERTEX_VERIFY_SSL"), default=True),
        company=os.getenv("VERTEX_COMPANY", "").strip(),
        product_code=os.getenv("VERTEX_PRODUCT_CODE", "GENERAL").strip() or "GENERAL",
        unit_price=_as_decimal(os.getenv("VERTEX_UNIT_PRICE"), "100.00"),
        rate_limit_seconds=_as_float(os.getenv("VERTEX_RATE_LIMIT_SECONDS"), 0.0),
    )

    if require_vertex_credentials:
        missing = [
            name
            for name, value in {
                "VERTEX_BASE_URL": config.base_url,
                "VERTEX_USERNAME": config.username,
                "VERTEX_PASSWORD": config.password,
                "VERTEX_COMPANY": config.company,
                "VERTEX_PRODUCT_CODE": config.product_code,
            }.items()
            if not value
        ]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    return config

