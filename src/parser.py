from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any


def _value(obj: Any) -> Any:
    if isinstance(obj, dict) and "value" in obj:
        return obj.get("value")
    return obj


def _decimal_or_none(value: Any) -> Decimal | None:
    value = _value(value)
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _format_decimal(value: Decimal | None, places: str = "0.01") -> str:
    if value is None:
        return ""
    return str(value.quantize(Decimal(places)))


def _format_rate(value: Decimal | None) -> str:
    if value is None:
        return ""
    return str(value.quantize(Decimal("0.000001")))


def _first_decimal(tax: dict[str, Any], keys: list[str]) -> Decimal | None:
    for key in keys:
        value = _decimal_or_none(tax.get(key))
        if value is not None:
            return value
    return None


def _first_text(tax: dict[str, Any], keys: list[str]) -> str:
    for key in keys:
        value = _value(tax.get(key))
        if isinstance(value, dict):
            value = value.get("value") or value.get("name") or value.get("code")
        if value not in (None, ""):
            return str(value)
    return ""


def summarize_jurisdictions(taxes: list[dict[str, Any]]) -> str:
    summaries: list[str] = []
    for tax in taxes:
        jurisdiction = _first_text(tax, ["jurisdiction", "jurisdictionName", "jurisdictionCode"])
        jurisdiction_type = _first_text(tax, ["jurisdictionType", "jurisdictionLevel"])
        imposition = _first_text(tax, ["imposition", "impositionType", "taxType"])
        amount = _first_decimal(tax, ["calculatedTax", "totalTax", "taxAmount", "amount"])
        rate = _first_decimal(tax, ["effectiveRate", "taxRate", "rate"])
        result = _first_text(tax, ["result", "taxResult", "taxabilityResult"])

        label_parts = [part for part in [jurisdiction_type, jurisdiction, imposition] if part]
        label = " ".join(label_parts) if label_parts else "Jurisdiction tax"
        detail_parts = []
        if rate is not None:
            detail_parts.append(f"rate={_format_rate(rate)}")
        if amount is not None:
            detail_parts.append(f"tax={_format_decimal(amount)}")
        if result:
            detail_parts.append(f"result={result}")
        summaries.append(f"{label} ({', '.join(detail_parts)})" if detail_parts else label)

    return " | ".join(summaries)


def parse_supply_response(response: dict[str, Any]) -> dict[str, str]:
    data = response.get("data", {})
    customer = data.get("customer", {})
    destination = customer.get("destination", {})
    line_items = data.get("lineItems") or []
    line_item = line_items[0] if line_items else {}
    taxes = line_item.get("taxes") or []

    tax_area_id = _value(destination.get("taxAreaId"))
    total_tax = _decimal_or_none(line_item.get("totalTax"))
    extended_price = _decimal_or_none(line_item.get("extendedPrice"))
    calculated_effective_rate = None
    if total_tax is not None and extended_price not in (None, Decimal("0")):
        calculated_effective_rate = total_tax / extended_price

    jurisdiction_summary = summarize_jurisdictions(taxes)
    tax_result_summary = _first_text(line_item, ["taxResult", "result", "taxabilityResult"])
    if not tax_result_summary:
        tax_result_summary = "TAXABLE" if total_tax and total_tax > 0 else "NO_TAX_OR_ZERO_TAX"

    return {
        "tax_area_id": str(tax_area_id or ""),
        "total_tax": _format_decimal(total_tax),
        "extended_price": _format_decimal(extended_price),
        "calculated_effective_rate": _format_rate(calculated_effective_rate),
        "jurisdiction_summary": jurisdiction_summary,
        "tax_result_summary": tax_result_summary,
    }

