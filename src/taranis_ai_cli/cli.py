from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Callable

import httpx
from dotenv import load_dotenv

from taranis_ai_cli.client import TaranisApiClient, TaranisApiError
from taranis_ai_cli.config import Settings
from taranis_ai_cli.operations import TaranisOperations


def _parse_json_object(value: str | None, field_name: str) -> dict[str, Any] | None:
    if value is None:
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{field_name} must be valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"{field_name} must be a JSON object")
    return parsed


def _emit(payload: Any, output: str) -> None:
    if output == "json":
        if isinstance(payload, str):
            print(payload)
            return
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True))
        return
    print(payload)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="taranis-ai-cli",
        description="Standalone Taranis CLI (no MCP server required).",
    )
    parser.add_argument("--base-url", help="Override TARANIS_BASE_URL")
    parser.add_argument("--auth-mode", choices=["auto", "jwt", "api_key"], help="Override TARANIS_AUTH_MODE")
    parser.add_argument("--username", help="Override TARANIS_USERNAME")
    parser.add_argument("--password", help="Override TARANIS_PASSWORD")
    parser.add_argument("--api-key", help="Override TARANIS_API_KEY")
    parser.add_argument("--timeout", type=float, help="Override TARANIS_TIMEOUT")
    parser.add_argument("--insecure", action="store_true", help="Disable TLS certificate verification")
    parser.add_argument("--output", choices=["text", "json"], default="json", help="Output format")
    parser.add_argument("--env-file", help="Load environment variables from a specific .env file")

    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("health-check")

    p = sub.add_parser("search-stories")
    p.add_argument("--filters", help="JSON object")
    p = sub.add_parser("get-story")
    p.add_argument("--story-id", required=True)
    p = sub.add_parser("update-story")
    p.add_argument("--story-id", required=True)
    p.add_argument("--payload", required=True, help="JSON object")

    p = sub.add_parser("create-news-item")
    p.add_argument("--payload", required=True, help="JSON object")
    p = sub.add_parser("get-news-item")
    p.add_argument("--item-id", required=True)
    p = sub.add_parser("update-news-item")
    p.add_argument("--item-id", required=True)
    p.add_argument("--payload", required=True, help="JSON object")
    p = sub.add_parser("delete-news-item")
    p.add_argument("--item-id", required=True)

    p = sub.add_parser("list-report-items")
    p.add_argument("--filters", help="JSON object")
    p = sub.add_parser("get-report-item")
    p.add_argument("--report-item-id", required=True)
    p = sub.add_parser("create-report-item")
    p.add_argument("--payload", required=True, help="JSON object")
    p = sub.add_parser("update-report-item")
    p.add_argument("--report-item-id", required=True)
    p.add_argument("--payload", required=True, help="JSON object")
    p = sub.add_parser("delete-report-item")
    p.add_argument("--report-item-id", required=True)

    p = sub.add_parser("list-products")
    p.add_argument("--filters", help="JSON object")
    p = sub.add_parser("get-product")
    p.add_argument("--product-id", required=True)
    p = sub.add_parser("trigger-product-render")
    p.add_argument("--product-id", required=True)
    p = sub.add_parser("publish-product")
    p.add_argument("--product-id", required=True)
    p.add_argument("--publisher-id", required=True)

    p = sub.add_parser("list-osint-sources")
    p.add_argument("--filters", help="JSON object")
    p = sub.add_parser("update-osint-source")
    p.add_argument("--source-id", required=True)
    p.add_argument("--payload", required=True, help="JSON object")
    p = sub.add_parser("delete-osint-source")
    p.add_argument("--source-id", required=True)
    p = sub.add_parser("collect-osint-source")
    p.add_argument("--source-id")

    p = sub.add_parser("list-word-lists")
    p.add_argument("--filters", help="JSON object")
    p = sub.add_parser("gather-word-list")
    p.add_argument("--word-list-id", type=int, required=True)

    p = sub.add_parser("list-bots")
    p.add_argument("--filters", help="JSON object")
    p = sub.add_parser("execute-bot")
    p.add_argument("--bot-id", required=True)

    return parser


def _apply_overrides(settings: Settings, args: argparse.Namespace) -> Settings:
    return Settings(
        base_url=(args.base_url or settings.base_url).rstrip("/"),
        auth_mode=args.auth_mode or settings.auth_mode,
        username=args.username or settings.username,
        password=args.password or settings.password,
        api_key=args.api_key or settings.api_key,
        verify_ssl=False if args.insecure else settings.verify_ssl,
        timeout_seconds=args.timeout or settings.timeout_seconds,
    )


def _dispatch(args: argparse.Namespace, ops: TaranisOperations) -> Any:
    handlers: dict[str, Callable[[], Any]] = {
        "health-check": ops.health_check,
        "search-stories": lambda: ops.search_stories(_parse_json_object(args.filters, "filters")),
        "get-story": lambda: ops.get_story(args.story_id),
        "update-story": lambda: ops.update_story(args.story_id, _parse_json_object(args.payload, "payload") or {}),
        "create-news-item": lambda: ops.create_news_item(_parse_json_object(args.payload, "payload") or {}),
        "get-news-item": lambda: ops.get_news_item(args.item_id),
        "update-news-item": lambda: ops.update_news_item(args.item_id, _parse_json_object(args.payload, "payload") or {}),
        "delete-news-item": lambda: ops.delete_news_item(args.item_id),
        "list-report-items": lambda: ops.list_report_items(_parse_json_object(args.filters, "filters")),
        "get-report-item": lambda: ops.get_report_item(args.report_item_id),
        "create-report-item": lambda: ops.create_report_item(_parse_json_object(args.payload, "payload") or {}),
        "update-report-item": lambda: ops.update_report_item(
            args.report_item_id, _parse_json_object(args.payload, "payload") or {}
        ),
        "delete-report-item": lambda: ops.delete_report_item(args.report_item_id),
        "list-products": lambda: ops.list_products(_parse_json_object(args.filters, "filters")),
        "get-product": lambda: ops.get_product(args.product_id),
        "trigger-product-render": lambda: ops.trigger_product_render(args.product_id),
        "publish-product": lambda: ops.publish_product(args.product_id, args.publisher_id),
        "list-osint-sources": lambda: ops.list_osint_sources(_parse_json_object(args.filters, "filters")),
        "update-osint-source": lambda: ops.update_osint_source(args.source_id, _parse_json_object(args.payload, "payload") or {}),
        "delete-osint-source": lambda: ops.delete_osint_source(args.source_id),
        "collect-osint-source": lambda: ops.collect_osint_source(args.source_id),
        "list-word-lists": lambda: ops.list_word_lists(_parse_json_object(args.filters, "filters")),
        "gather-word-list": lambda: ops.gather_word_list(args.word_list_id),
        "list-bots": lambda: ops.list_bots(_parse_json_object(args.filters, "filters")),
        "execute-bot": lambda: ops.execute_bot(args.bot_id),
    }
    return handlers[args.command]()


def _load_env(args: argparse.Namespace) -> None:
    if args.env_file:
        env_path = Path(args.env_file)
        if not env_path.exists():
            raise ValueError(f"--env-file does not exist: {env_path}")
        load_dotenv(dotenv_path=env_path, override=False)
        return

    # Auto-load project/default .env if present, but keep explicit shell env as higher priority.
    load_dotenv(override=False)


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    try:
        _load_env(args)
        settings = _apply_overrides(Settings.from_env(), args)
        client = TaranisApiClient(settings)
        ops = TaranisOperations(client)
        try:
            result = _dispatch(args, ops)
        finally:
            ops.close()
    except (ValueError, TaranisApiError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
    except httpx.HTTPError as exc:
        print(f"error: request failed ({exc})", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:  # pragma: no cover
        print(f"unexpected error: {exc}", file=sys.stderr)
        sys.exit(1)

    _emit(result, args.output)


if __name__ == "__main__":
    main()
