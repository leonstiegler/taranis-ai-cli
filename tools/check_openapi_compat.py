from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
import urllib.request


LATEST_RELEASE_API = "https://api.github.com/repos/taranis-ai/taranis-ai/releases/latest"
RAW_OPENAPI_TEMPLATE = (
    "https://raw.githubusercontent.com/taranis-ai/taranis-ai/{tag}/src/core/core/static/openapi3_1.yaml"
)


def _normalize_path(path: str) -> str:
    path = path.strip()
    if path.startswith("/api"):
        path = path[4:]
    return re.sub(r"\{[^}]+\}", "{}", path)


def _parse_openapi_methods(openapi_text: str) -> dict[str, set[str]]:
    methods_by_path: dict[str, set[str]] = {}
    in_paths = False
    current_path: str | None = None

    for line in openapi_text.splitlines():
        if line.startswith("paths:"):
            in_paths = True
            continue
        if in_paths and line.startswith("components:"):
            break
        if not in_paths:
            continue

        path_match = re.match(r"^  (/[A-Za-z0-9_\-{}\/]+):\s*$", line)
        if path_match:
            current_path = _normalize_path(path_match.group(1))
            methods_by_path.setdefault(current_path, set())
            continue

        method_match = re.match(r"^    (get|post|put|delete|patch):\s*$", line)
        if method_match and current_path:
            methods_by_path[current_path].add(method_match.group(1).upper())

    return methods_by_path


def _parse_cli_endpoints(operations_text: str) -> set[tuple[str, str]]:
    endpoints: set[tuple[str, str]] = set()
    pattern = re.compile(r'request_(?:json|text)\("([A-Z]+)",\s*f?"(/api[^"]+)"')
    for method, path in pattern.findall(operations_text):
        endpoints.add((method, _normalize_path(path)))
    return endpoints


def _group_name(path: str) -> str:
    trimmed = path.lstrip("/")
    if not trimmed:
        return "root"
    return trimmed.split("/", 1)[0]


class _Color:
    def __init__(self, mode: str):
        auto_enabled = sys.stdout.isatty() and os.getenv("NO_COLOR") is None
        self.enabled = mode == "always" or (mode == "auto" and auto_enabled)

    def _wrap(self, text: str, code: str) -> str:
        if not self.enabled:
            return text
        return f"\033[{code}m{text}\033[0m"

    def green(self, text: str) -> str:
        return self._wrap(text, "32")

    def red(self, text: str) -> str:
        return self._wrap(text, "31")

    def yellow(self, text: str) -> str:
        return self._wrap(text, "33")

    def cyan(self, text: str) -> str:
        return self._wrap(text, "36")


def _http_get_text(url: str) -> str:
    request = urllib.request.Request(
        url=url,
        headers={
            "Accept": "application/json",
            "User-Agent": "taranis-ai-cli-openapi-check",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:  # nosec: B310
        return response.read().decode("utf-8")


def _load_latest_release_openapi() -> tuple[str, str]:
    release_payload = json.loads(_http_get_text(LATEST_RELEASE_API))
    tag_name = release_payload.get("tag_name")
    if not tag_name:
        raise RuntimeError("Could not resolve latest release tag from GitHub API response.")
    spec_url = RAW_OPENAPI_TEMPLATE.format(tag=tag_name)
    return _http_get_text(spec_url), tag_name


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate CLI endpoints against Taranis OpenAPI path/method pairs.")
    parser.add_argument(
        "--spec",
        help="Path to local openapi3_1.yaml (optional). If omitted, latest release is used.",
    )
    parser.add_argument(
        "--latest-release",
        action="store_true",
        help="Use the newest release OpenAPI from github.com/taranis-ai/taranis-ai",
    )
    parser.add_argument(
        "--operations",
        default=str(pathlib.Path(__file__).resolve().parents[1] / "src" / "taranis_ai_cli" / "operations.py"),
        help="Path to operations.py",
    )
    parser.add_argument(
        "--color",
        choices=["auto", "always", "never"],
        default="auto",
        help="Color output mode",
    )
    args = parser.parse_args()
    color = _Color(args.color)

    if args.spec and not args.latest_release:
        openapi_text = pathlib.Path(args.spec).read_text(encoding="utf-8")
        source_label = str(pathlib.Path(args.spec))
    else:
        openapi_text, tag_name = _load_latest_release_openapi()
        source_label = f"latest release ({tag_name})"
    operations_text = pathlib.Path(args.operations).read_text(encoding="utf-8")

    methods_by_path = _parse_openapi_methods(openapi_text)
    cli_endpoints = _parse_cli_endpoints(operations_text)
    openapi_pairs = sum(len(methods) for methods in methods_by_path.values())
    checks: list[dict[str, object]] = []
    for method, path in sorted(cli_endpoints, key=lambda x: (x[1], x[0])):
        openapi_methods = methods_by_path.get(path)
        if openapi_methods is None:
            checks.append(
                {
                    "group": _group_name(path),
                    "method": method,
                    "path": path,
                    "status": "SPEC_MISMATCH",
                    "reason": "path_missing",
                    "openapi_methods": [],
                }
            )
            continue
        if method not in openapi_methods:
            checks.append(
                {
                    "group": _group_name(path),
                    "method": method,
                    "path": path,
                    "status": "SPEC_MISMATCH",
                    "reason": "method_mismatch",
                    "openapi_methods": sorted(openapi_methods),
                }
            )
            continue
        checks.append(
            {
                "group": _group_name(path),
                "method": method,
                "path": path,
                "status": "SPEC_MATCH",
                "reason": "",
                "openapi_methods": sorted(openapi_methods),
            }
        )

    match_count = sum(1 for c in checks if c["status"] == "SPEC_MATCH")
    mismatch_count = len(checks) - match_count
    checked_pairs = {(str(c["method"]), str(c["path"])) for c in checks}
    openapi_method_pairs = {(method, path) for path, methods in methods_by_path.items() for method in methods}
    missing_pairs = sorted(openapi_method_pairs - checked_pairs, key=lambda x: (x[1], x[0]))

    available_by_group: dict[str, int] = {}
    for path, methods in methods_by_path.items():
        group = _group_name(path)
        available_by_group[group] = available_by_group.get(group, 0) + len(methods)

    checked_by_group: dict[str, int] = {}
    for c in checks:
        group = str(c["group"])
        checked_by_group[group] = checked_by_group.get(group, 0) + 1

    groups = sorted(set(list(available_by_group.keys()) + list(checked_by_group.keys())))
    overall_coverage = (len(checks) / openapi_pairs * 100.0) if openapi_pairs else 0.0

    if mismatch_count:
        print(color.red("OpenAPI compatibility check failed."))
    else:
        print(color.green("OpenAPI compatibility check passed."))
    print(f"Source: {source_label}")
    print(f"OpenAPI paths parsed: {len(methods_by_path)}")
    print(f"OpenAPI method/path pairs: {openapi_pairs}")
    print(f"CLI endpoints checked: {len(checks)}")
    print(f"Results: SPEC_MATCH={match_count} SPEC_MISMATCH={mismatch_count}")
    print("")
    print(color.yellow("Coverage by group (checked/available):"))
    for group in groups:
        checked = checked_by_group.get(group, 0)
        available = available_by_group.get(group, 0)
        pct = (checked / available * 100.0) if available else 0.0
        print(f"- {group}: {checked}/{available} ({pct:.1f}%)")

    print("")
    print(color.yellow("Validated CLI endpoints by group:"))
    grouped_checks: dict[str, list[dict[str, object]]] = {}
    for c in checks:
        grouped_checks.setdefault(str(c["group"]), []).append(c)
    missing_by_group: dict[str, list[tuple[str, str]]] = {}
    for method, path in missing_pairs:
        missing_by_group.setdefault(_group_name(path), []).append((method, path))

    for group in groups:
        items = sorted(grouped_checks.get(group, []), key=lambda c: (str(c["path"]), str(c["method"])))
        missing_items = sorted(missing_by_group.get(group, []), key=lambda x: (x[1], x[0]))
        print(color.cyan(f"[{group}] ({len(items)} checks, {len(missing_items)} missing)"))
        for c in items:
            method = str(c["method"])
            path = str(c["path"])
            status = str(c["status"])
            supported = c["openapi_methods"]
            reason = str(c["reason"])
            reason_suffix = f" reason={reason}" if reason else ""
            status_colored = color.green(status) if status == "SPEC_MATCH" else color.red(status)
            print(f"- [{status_colored}] {method:6} {path}  (openapi: {supported}){reason_suffix}")
        if missing_items:
            print(color.yellow("  Not implemented in CLI:"))
            for method, path in missing_items:
                print(f"- [{color.red('NOT_IMPLEMENTED')}] {method:6} {path}")
        print("")

    release_label = source_label
    summary = (
        f"OPENAPI-COMPAT {'PASS' if mismatch_count == 0 else 'FAIL'} | "
        f"source={release_label} | "
        f"checked={len(checks)} | spec_match={match_count} | spec_mismatch={mismatch_count} | "
        f"coverage={overall_coverage:.1f}% ({len(checks)}/{openapi_pairs})"
    )
    if mismatch_count:
        print(color.red(summary))
    else:
        print(color.green(summary))

    if mismatch_count:
        sys.exit(1)


if __name__ == "__main__":
    main()
