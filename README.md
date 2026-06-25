# Vertex Store Tax Area Map

Phase 1 proof-of-concept for validating Best Buy store-location tax results with Vertex O Series sandbox `/v2/supplies`.

This project reads store locations from CSV, sends a `QUOTATION` sale request to Vertex, extracts the returned Tax Area ID and tax details, writes normalized results to CSV, and generates an interactive Folium map.

## Architecture

- `src/config.py` loads environment variables and runtime defaults.
- `src/vertex_client.py` builds and sends Vertex `/v2/supplies` quotation requests.
- `src/parser.py` extracts Tax Area ID, tax totals, effective rate, and jurisdiction summaries from Vertex responses.
- `src/pipeline.py` orchestrates CSV input, Vertex calls, raw response storage, result CSV output, and map generation.
- `src/map_generator.py` creates the interactive HTML map.
- `src/mock_data.py` creates synthetic demo data and mock Vertex-like responses for local testing.

Coordinates are used only for map marker placement. Tax lookup/calculation is performed with `/v2/supplies` using the destination address. The TaxGIS `/v2/coordinates-lookup` endpoint is intentionally not used.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` with sandbox credentials and Vertex setup values.

## Environment Variables

- `VERTEX_BASE_URL`
- `VERTEX_USERNAME`
- `VERTEX_PASSWORD`
- `VERTEX_VERIFY_SSL`
- `VERTEX_COMPANY`
- `VERTEX_PRODUCT_CODE`
- `VERTEX_UNIT_PRICE`
- `VERTEX_RATE_LIMIT_SECONDS`

## Input CSV

Populate `data/input/store_locations.csv` with approved store-location data:

```csv
store_id,store_name,street,city,state,postal_code,country,latitude,longitude
```

Required fields:

- `store_id`
- `store_name`
- `street`
- `city`
- `state`
- `postal_code`
- `country`
- `latitude`
- `longitude`

## Run Against Vertex

```powershell
python -m src.pipeline
```

Default outputs:

- Processed CSV: `data/processed/store_tax_results.csv`
- Raw responses: `data/processed/raw_responses/`
- Map: `data/output/store_tax_area_map.html`

## Local Mock Run

Use this when credentials are not available yet:

```powershell
python -m src.mock_data
python -m src.pipeline --input data/input/store_locations_sample.csv --use-mock-vertex
```

## Map Marker Colors

- Red: failed lookup
- Orange: successful lookup with zero effective tax rate
- Blue: normal taxable result with a positive effective tax rate
- Green: successful lookup where no positive/zero rate classification is available

## Important Limitations

- This is a sandbox proof-of-concept.
- Tax rates depend on seller company, product code, customer setup, registration setup, and document date.
- A `$100` quotation is used only to estimate the effective tax rate.
- This is not a legal boundary map.
- Store addresses must come from an approved source.
- If `GENERAL` returns `NO_TAX`, ask the tax team for the correct taxable product code.

