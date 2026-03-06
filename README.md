# taranis-ai-cli

Standalone CLI for the Taranis API, without an MCP server runtime dependency.

## Setup

```powershell
cd taranis-ai-cli
uv sync
```

## Configuration (Environment Variables)

```powershell
$env:TARANIS_BASE_URL = "http://127.0.0.1:5000"
$env:TARANIS_AUTH_MODE = "jwt"   # auto|jwt|api_key
$env:TARANIS_USERNAME = "admin"
$env:TARANIS_PASSWORD = "admin"
$env:TARANIS_VERIFY_SSL = "true"
$env:TARANIS_TIMEOUT = "30"
```

Alternative worker API auth:

```powershell
$env:TARANIS_AUTH_MODE = "api_key"
$env:TARANIS_API_KEY = "..."
```

## Usage

```powershell
uv run taranis-ai-cli --help
uv run taranis-ai-cli health-check
uv run taranis-ai-cli search-stories --filters '{"search":"threat","limit":5}'
uv run taranis-ai-cli get-story --story-id 123
uv run taranis-ai-cli create-news-item --payload '{"title":"Example","content":"..."}'
uv run taranis-ai-cli update-osint-source --source-id 42 --payload '{"name":"new-name"}'
```

All commands return JSON on stdout by default.

## OpenAPI Compatibility Check

```powershell
python .\tools\check_openapi_compat.py
```

Script: `tools/check_openapi_compat.py`

What the script does:
- Loads OpenAPI from the latest `taranis-ai` release (or a local file via `--spec`).
- Extracts all implemented `METHOD + PATH` pairs from `operations.py`.
- Compares implemented pairs with OpenAPI pairs.
- Prints coverage by API group (`checked / available`).
- Prints, per group:
  - implemented and spec-matching endpoints (`SPEC_MATCH`)
  - implemented but spec-mismatching endpoints (`SPEC_MISMATCH`)
  - endpoints present in OpenAPI but not implemented in this CLI (`NOT_IMPLEMENTED`)

Important options:
- `--latest-release`: explicitly check against latest GitHub release.
- `--spec <path>`: check against a local OpenAPI file.
- `--operations <path>`: use a different `operations.py`.
- `--color auto|always|never`: control colored output.

Status meaning:
- `SPEC_MATCH`: endpoint exists in the CLI and matches OpenAPI (path + method).
- `SPEC_MISMATCH`: endpoint exists in the CLI but does not match OpenAPI.
- `NOT_IMPLEMENTED`: endpoint exists in OpenAPI but is not implemented in this CLI.

Latest release check:

```powershell
python .\tools\check_openapi_compat.py --latest-release
```

Local file check:

```powershell
python .\tools\check_openapi_compat.py --spec .\openapi3_1.yaml
```

PR summary line format:

```text
OPENAPI-COMPAT PASS|FAIL | source=... | checked=... | spec_match=... | spec_mismatch=... | coverage=... (.../...)
```
