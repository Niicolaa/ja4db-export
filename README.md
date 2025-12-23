# ja4db-export

This repository automatically downloads and republishes data from the official [**JA4DB**](https://ja4db.com) API.

It stores:
- The **CSV-converted** datasets in `csv/`, including:
  - `csv/all_records.csv` — all records, full schema
  - Separate CSVs per JA4 fingerprint type:
    - `csv/ja4_fingerprin_string_.csv`
    - `csv/ja4_fingerprint.csv`
    - `csv/ja4s_fingerprint.csv`
    - `csv/ja4h_fingerprint.csv`
    - `csv/ja4x_fingerprint.csv`
    - `csv/ja4t_fingerprint.csv`
    - `csv/ja4ts_fingerprint.csv`
    - `csv/ja4tscan_fingerprint.csv`

A GitHub Actions workflow runs **daily** to update the data automatically.

## About JA4DB

[JA4DB](https://ja4db.com) is an open database of **JA4, JA4S, JA4H, JA4X, JA4T, and related TLS fingerprint data** for network and security analysis.  
The dataset enables researchers and analysts to identify, classify, and correlate network clients by their TLS, HTTP, and JA4-derived signatures.

This repository mirrors and reformats the JA4DB dataset into CSV formats for integration into SIEM and analytics tools such as:
- **Microsoft Sentinel**
- **Microsoft Defender for Endpoint**
- **Azure Data Explorer (ADX)**
- **Elastic / Splunk**


## Example Usage in Kusto
```
let JA4Mapping =
externaldata (
  application:string,
  library:string,
  device:string,
  os:string,
  user_agent_string:string,
  certificate_authority:string,
  verified:string,
  notes:string,
  observation_count:int,
  ja4_fingerprint:string,
  ja4_fingerprint_string:string,
  ja4h_fingerprint:string,
  ja4h_fingerprint:string,
  ja4s_fingerprint:string,
  ja4t_fingerprint:string,
  ja4ts_fingerprint:string,
  ja4tscan_fingerprint:string,
  ja4x_fingerprint:string
)
[
  @"https://raw.githubusercontent.com/Niicolaa/ja4db-export/main/csv/all_records.csv"
]
with (format="csv", ignoreFirstRecord=true);

JA4Mapping
| take 10

EntraIdSignInEvents
| join kind=leftouter JA4Mapping on $left.GatewayJA4 == $right.ja4_fingerprint
```

## KQL `externaldata()` limits, file sizes, and hosting

### Size limit
`externaldata()` is meant for small reference tables and supports external artifacts **up to 100 MB**. For larger datasets, ingest into a table/watchlist instead.  
(See Microsoft docs for `externaldata`.) 

### Current dataset sizes (23.12.2025)
As of **23.12.2025** (measured from this repo’s exports):
- raw JSON file is ~**190 MB** → **too large** for `externaldata()`
- `csv/all_records.csv` is ~**25 MB** → works well with `externaldata()`

### Why this repo publishes multiple CSVs
To keep queries fast and resilient as JA4DB grows, the export also produces **smaller per-fingerprint CSVs**
(e.g. `csv/ja4t_fingerprint.csv`, `csv/ja4h_fingerprint.csv`, …).  
If `csv/all_records.csv` ever approaches the 100 MB limit, switch your KQL to fetch **only the specific per-type file(s)** you need.

### Why I don't use GitHub Releases
This repo deliberately serves files via **`raw.githubusercontent.com`** (regular repository files).
Many **GitHub Releases asset URLs redirect**, and `externaldata()` fetches can fail with errors like **“redirects are not allowed”**.
So: keep the artifacts committed in the repo (or host them on Azure Blob Storage), not as Release attachments.


## Local usage

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python ja4db_export.py
```

