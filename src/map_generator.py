from __future__ import annotations

import csv
import html
from decimal import Decimal, InvalidOperation
from pathlib import Path

import folium


def _decimal_or_none(value: str) -> Decimal | None:
    if value == "":
        return None
    try:
        return Decimal(value)
    except (InvalidOperation, TypeError):
        return None


def _float_or_none(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def marker_color(row: dict[str, str]) -> str:
    if row.get("status") != "success":
        return "red"
    rate = _decimal_or_none(row.get("calculated_effective_rate", ""))
    if rate == Decimal("0"):
        return "orange"
    if rate and rate > 0:
        return "blue"
    return "green"


def _popup_html(row: dict[str, str]) -> str:
    address = ", ".join(
        part
        for part in [
            row.get("street", ""),
            row.get("city", ""),
            row.get("state", ""),
            row.get("postal_code", ""),
        ]
        if part
    )
    rate = row.get("calculated_effective_rate", "")
    rate_display = f"{(Decimal(rate) * Decimal('100')).quantize(Decimal('0.01'))}%" if rate else ""
    fields = [
        ("Store ID", row.get("store_id", "")),
        ("Store Name", row.get("store_name", "")),
        ("Address", address),
        ("Tax Area ID", row.get("tax_area_id", "")),
        ("Effective Tax Rate", rate_display),
        ("Total Tax on Test Sale", row.get("total_tax", "")),
        ("Jurisdictions", row.get("jurisdiction_summary", "")),
        ("Status", row.get("status", "")),
    ]
    rows = "".join(
        f"<tr><th>{html.escape(label)}</th><td>{html.escape(str(value))}</td></tr>"
        for label, value in fields
    )
    return f"""
    <div style="width: 340px">
      <table>{rows}</table>
    </div>
    """


def generate_map(processed_csv_path: str | Path, output_html_path: str | Path) -> Path:
    processed_csv_path = Path(processed_csv_path)
    output_html_path = Path(output_html_path)

    with processed_csv_path.open("r", encoding="utf-8", newline="") as csv_file:
        rows = list(csv.DictReader(csv_file))

    valid_points = [
        (_float_or_none(row.get("latitude", "")), _float_or_none(row.get("longitude", "")))
        for row in rows
    ]
    valid_points = [(lat, lon) for lat, lon in valid_points if lat is not None and lon is not None]
    center = (
        [sum(lat for lat, _ in valid_points) / len(valid_points), sum(lon for _, lon in valid_points) / len(valid_points)]
        if valid_points
        else [39.8283, -98.5795]
    )

    store_map = folium.Map(location=center, zoom_start=4, tiles="CartoDB positron")

    for row in rows:
        latitude = _float_or_none(row.get("latitude", ""))
        longitude = _float_or_none(row.get("longitude", ""))
        if latitude is None or longitude is None:
            continue

        folium.Marker(
            location=[latitude, longitude],
            popup=folium.Popup(_popup_html(row), max_width=380),
            tooltip=f"{row.get('store_id', '')} - {row.get('store_name', '')}",
            icon=folium.Icon(color=marker_color(row), icon="info-sign"),
        ).add_to(store_map)

    output_html_path.parent.mkdir(parents=True, exist_ok=True)
    store_map.save(str(output_html_path))
    return output_html_path

