from __future__ import annotations

import argparse
import csv
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import load_config
from .map_generator import generate_map
from .mock_data import mock_supply_response
from .parser import parse_supply_response
from .vertex_client import VertexAPIError, VertexClient


INPUT_FIELDS = [
    "store_id",
    "store_name",
    "street",
    "city",
    "state",
    "postal_code",
    "country",
    "latitude",
    "longitude",
]

OUTPUT_FIELDS = [
    "store_id",
    "store_name",
    "street",
    "city",
    "state",
    "postal_code",
    "latitude",
    "longitude",
    "tax_area_id",
    "total_tax",
    "extended_price",
    "calculated_effective_rate",
    "jurisdiction_summary",
    "tax_result_summary",
    "status",
    "error_message",
    "response_payload_path",
    "created_at",
]


def _safe_file_stem(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return safe or "store"


def _read_store_rows(input_path: Path) -> list[dict[str, str]]:
    with input_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        missing = [field for field in INPUT_FIELDS if field not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"Input CSV missing required fields: {', '.join(missing)}")
        return [{field: (row.get(field) or "").strip() for field in INPUT_FIELDS} for row in reader]


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as json_file:
        json.dump(payload, json_file, indent=2, sort_keys=True)
    return path


def _base_output_row(store: dict[str, str], created_at: str) -> dict[str, str]:
    return {
        "store_id": store["store_id"],
        "store_name": store["store_name"],
        "street": store["street"],
        "city": store["city"],
        "state": store["state"],
        "postal_code": store["postal_code"],
        "latitude": store["latitude"],
        "longitude": store["longitude"],
        "tax_area_id": "",
        "total_tax": "",
        "extended_price": "",
        "calculated_effective_rate": "",
        "jurisdiction_summary": "",
        "tax_result_summary": "",
        "status": "",
        "error_message": "",
        "response_payload_path": "",
        "created_at": created_at,
    }


def run_pipeline(
    input_path: str | Path = "data/input/store_locations.csv",
    output_csv_path: str | Path = "data/processed/store_tax_results.csv",
    raw_response_dir: str | Path = "data/processed/raw_responses",
    map_output_path: str | Path = "data/output/store_tax_area_map.html",
    use_mock_vertex: bool = False,
) -> dict[str, int | Path]:
    input_path = Path(input_path)
    output_csv_path = Path(output_csv_path)
    raw_response_dir = Path(raw_response_dir)
    map_output_path = Path(map_output_path)

    config = load_config(require_vertex_credentials=not use_mock_vertex)
    client = None if use_mock_vertex else VertexClient(config)
    stores = _read_store_rows(input_path)
    created_at = datetime.now(timezone.utc).isoformat()
    output_rows: list[dict[str, str]] = []
    success_count = 0
    failure_count = 0

    for index, store in enumerate(stores, start=1):
        row = _base_output_row(store, created_at)
        response_path = raw_response_dir / f"{index:04d}_{_safe_file_stem(store['store_id'])}.json"

        try:
            response_payload = (
                mock_supply_response(store, config.unit_price)
                if use_mock_vertex
                else client.quote_store(store)  # type: ignore[union-attr]
            )
            _write_json(response_path, response_payload)
            parsed = parse_supply_response(response_payload)
            row.update(parsed)
            row["status"] = "success"
            row["response_payload_path"] = str(response_path)
            success_count += 1
        except VertexAPIError as exc:
            error_payload = {
                "error": str(exc),
                "status_code": exc.status_code,
                "response_text": exc.response_text,
            }
            _write_json(response_path, error_payload)
            row["status"] = "failed"
            row["error_message"] = str(exc)
            row["response_payload_path"] = str(response_path)
            failure_count += 1
        except Exception as exc:
            row["status"] = "failed"
            row["error_message"] = str(exc)
            failure_count += 1

        output_rows.append(row)

        if config.rate_limit_seconds > 0 and index < len(stores):
            time.sleep(config.rate_limit_seconds)

    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    with output_csv_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(output_rows)

    generate_map(output_csv_path, map_output_path)

    return {
        "stores": len(stores),
        "successes": success_count,
        "failures": failure_count,
        "output_csv_path": output_csv_path,
        "map_output_path": map_output_path,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Vertex store tax area map pipeline.")
    parser.add_argument("--input", default="data/input/store_locations.csv", help="Input store CSV path.")
    parser.add_argument("--output", default="data/processed/store_tax_results.csv", help="Processed output CSV path.")
    parser.add_argument("--raw-dir", default="data/processed/raw_responses", help="Raw response output directory.")
    parser.add_argument("--map-output", default="data/output/store_tax_area_map.html", help="Folium HTML map output path.")
    parser.add_argument("--use-mock-vertex", action="store_true", help="Use synthetic Vertex-like responses.")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    summary = run_pipeline(
        input_path=args.input,
        output_csv_path=args.output,
        raw_response_dir=args.raw_dir,
        map_output_path=args.map_output,
        use_mock_vertex=args.use_mock_vertex,
    )
    print(
        "Pipeline complete: "
        f"{summary['stores']} stores, "
        f"{summary['successes']} successes, "
        f"{summary['failures']} failures"
    )
    print(f"Processed CSV: {summary['output_csv_path']}")
    print(f"Map: {summary['map_output_path']}")


if __name__ == "__main__":
    main()

