from __future__ import annotations

from typing import Any

from taranis_ai_cli.client import JsonValue, TaranisApiClient


class TaranisOperations:
    def __init__(self, client: TaranisApiClient):
        self.client = client

    def close(self) -> None:
        self.client.close()

    def health_check(self) -> JsonValue:
        return self.client.request_json("GET", "/api/isalive")

    def search_stories(self, filters: dict[str, Any] | None = None) -> JsonValue:
        return self.client.request_json("GET", "/api/assess/stories", params=filters)

    def get_story(self, story_id: str) -> JsonValue:
        return self.client.request_json("GET", f"/api/assess/story/{story_id}")

    def update_story(self, story_id: str, payload: dict[str, Any]) -> JsonValue:
        return self.client.request_json("PUT", f"/api/assess/story/{story_id}", json_body=payload)

    def create_news_item(self, payload: dict[str, Any]) -> JsonValue:
        return self.client.request_json("POST", "/api/assess/news-items", json_body=payload)

    def get_news_item(self, item_id: str) -> JsonValue:
        return self.client.request_json("GET", f"/api/assess/news-items/{item_id}")

    def update_news_item(self, item_id: str, payload: dict[str, Any]) -> JsonValue:
        return self.client.request_json("PUT", f"/api/assess/news-items/{item_id}", json_body=payload)

    def delete_news_item(self, item_id: str) -> JsonValue:
        return self.client.request_json("DELETE", f"/api/assess/news-items/{item_id}")

    def list_report_items(self, filters: dict[str, Any] | None = None) -> JsonValue:
        return self.client.request_json("GET", "/api/analyze/report-items", params=filters)

    def get_report_item(self, report_item_id: str) -> JsonValue:
        return self.client.request_json("GET", f"/api/analyze/report-items/{report_item_id}")

    def create_report_item(self, payload: dict[str, Any]) -> JsonValue:
        return self.client.request_json("POST", "/api/analyze/report-items", json_body=payload)

    def update_report_item(self, report_item_id: str, payload: dict[str, Any]) -> JsonValue:
        return self.client.request_json("PUT", f"/api/analyze/report-items/{report_item_id}", json_body=payload)

    def delete_report_item(self, report_item_id: str) -> JsonValue:
        return self.client.request_json("DELETE", f"/api/analyze/report-items/{report_item_id}")

    def list_products(self, filters: dict[str, Any] | None = None) -> JsonValue:
        return self.client.request_json("GET", "/api/publish/products", params=filters)

    def get_product(self, product_id: str) -> JsonValue:
        return self.client.request_json("GET", f"/api/publish/products/{product_id}")

    def trigger_product_render(self, product_id: str) -> JsonValue:
        return self.client.request_json("POST", f"/api/publish/products/{product_id}/render")

    def publish_product(self, product_id: str, publisher_id: str) -> JsonValue:
        return self.client.request_json("POST", f"/api/publish/products/{product_id}/publishers/{publisher_id}")

    def list_osint_sources(self, filters: dict[str, Any] | None = None) -> JsonValue:
        return self.client.request_json("GET", "/api/config/osint-sources", params=filters)

    def update_osint_source(self, source_id: str, payload: dict[str, Any]) -> JsonValue:
        return self.client.request_json("PUT", f"/api/config/osint-sources/{source_id}", json_body=payload)

    def delete_osint_source(self, source_id: str) -> JsonValue:
        return self.client.request_json("DELETE", f"/api/config/osint-sources/{source_id}")

    def collect_osint_source(self, source_id: str | None = None) -> JsonValue:
        if source_id:
            return self.client.request_json("POST", f"/api/config/osint-sources/{source_id}/collect")
        return self.client.request_json("POST", "/api/config/osint-sources/collect")

    def list_word_lists(self, filters: dict[str, Any] | None = None) -> JsonValue:
        return self.client.request_json("GET", "/api/config/word-lists", params=filters)

    def gather_word_list(self, word_list_id: int) -> JsonValue:
        return self.client.request_json("POST", f"/api/config/word-lists/gather/{word_list_id}")

    def list_bots(self, filters: dict[str, Any] | None = None) -> JsonValue:
        return self.client.request_json("GET", "/api/config/bots", params=filters)

    def execute_bot(self, bot_id: str) -> JsonValue:
        return self.client.request_json("POST", f"/api/config/bots/{bot_id}/execute")
