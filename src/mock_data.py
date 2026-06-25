from __future__ import annotations

import csv
import hashlib
from decimal import Decimal
from pathlib import Path
from typing import Any


SAMPLE_STORES = [
    {
        "store_id": "BBY-DEMO-001",
        "store_name": "Best Buy Demo North",
        "street": "100 Demo Way",
        "city": "Minneapolis",
        "state": "MN",
        "postal_code": "55401",
        "country": "US",
        "latitude": "44.9778",
        "longitude": "-93.2650",
    },
    {
        "store_id": "BBY-DEMO-002",
        "store_name": "Best Buy Demo Central",
        "street": "200 Proof Point Ave",
        "city": "Chicago",
        "state": "IL",
        "postal_code": "60601",
        "country": "US",
        "latitude": "41.8781",
        "longitude": "-87.6298",
    },
    {
        "store_id": "BBY-DEMO-003",
        "store_name": "Best Buy Demo Zero Tax",
        "street": "300 Sandbox Blvd",
        "city": "Portland",
        "state": "OR",
        "postal_code": "97201",
        "country": "US",
        "latitude": "45.5152",
        "longitude": "-122.6784",
    },
]


def create_sample_csv(path: str | Path = "data/input/store_locations_sample.csv") -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(SAMPLE_STORES[0].keys()))
        writer.writeheader()
        writer.writerows(SAMPLE_STORES)
    return path


def mock_supply_response(store: dict[str, str], unit_price: Decimal) -> dict[str, Any]:
    is_zero_tax = store.get("state") == "OR"
    rate = Decimal("0.0000") if is_zero_tax else Decimal("0.0825")
    total_tax = (unit_price * rate).quantize(Decimal("0.01"))
    tax_area_key = f"{store.get('postal_code', '')}|{store.get('state', '')}".encode("utf-8")
    tax_area_id_suffix = int(hashlib.sha256(tax_area_key).hexdigest()[:12], 16) % 1000000000

    return {
        "data": {
            "customer": {
                "destination": {
                    "taxAreaId": str(tax_area_id_suffix),
                }
            },
            "lineItems": [
                {
                    "extendedPrice": str(unit_price.quantize(Decimal("0.01"))),
                    "totalTax": str(total_tax),
                    "taxResult": "NO_TAX" if is_zero_tax else "TAXABLE",
                    "taxes": [
                        {
                            "jurisdictionType": "STATE",
                            "jurisdiction": {"value": store.get("state", "")},
                            "imposition": {"value": "Sales and Use Tax"},
                            "effectiveRate": str(rate),
                            "calculatedTax": str(total_tax),
                            "result": "NO_TAX" if is_zero_tax else "TAXABLE",
                        }
                    ],
                }
            ],
        }
    }


if __name__ == "__main__":
    created_path = create_sample_csv()
    print(f"Created sample CSV: {created_path}")
