#!/usr/bin/env python3
"""Filter, deduplicate, persist, and report Bay Area restaurant candidates."""

from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse


REQUIRED_FIELDS = ("name", "city", "google_rating", "google_maps_url", "rednote_url")
AVOIDANCE_TERMS = ("避雷", "踩雷")


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKC", value).casefold()
    return "".join(ch for ch in text if ch.isalnum())


def extract_place_id(url: str) -> str:
    parsed = urlparse(url)
    query_place_id = parse_qs(parsed.query).get("query_place_id", [""])[0]
    if query_place_id:
        return query_place_id.strip()
    match = re.search(r"!1s([^!]+)", unquote(url))
    return match.group(1).strip() if match else ""


def candidate_keys(item: dict[str, Any]) -> set[str]:
    name = normalize_text(str(item.get("name", "")))
    city = normalize_text(str(item.get("city", "")))
    address = normalize_text(str(item.get("address", "")))
    place_id = str(item.get("google_place_id", "")).strip() or extract_place_id(
        str(item.get("google_maps_url", ""))
    )
    keys: set[str] = set()
    if place_id:
        keys.add(f"place:{place_id.casefold()}")
    if name and address:
        keys.add(f"address:{name}|{address}")
    if name and city:
        keys.add(f"city:{name}|{city}")
    return keys


def validate_url(value: str, domains: tuple[str, ...], field: str) -> None:
    parsed = urlparse(value)
    host = (parsed.hostname or "").casefold()
    if parsed.scheme != "https" or not any(host == domain or host.endswith(f".{domain}") for domain in domains):
        raise ValueError(f"{field} must be an HTTPS URL on {', '.join(domains)}")


def validate_rednote_reviews(item: dict[str, Any]) -> None:
    reviews = item.get("rednote_review_posts")
    if not isinstance(reviews, list) or len(reviews) != 5:
        raise ValueError("rednote_review_posts must contain exactly five review objects")
    normalized_reviews: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    seen_authors: set[str] = set()
    recommendation_count = 0
    avoidance_count = 0
    for index, raw_review in enumerate(reviews, start=1):
        if not isinstance(raw_review, dict):
            raise ValueError(f"rednote_review_posts[{index}] must be an object")
        review = dict(raw_review)
        title = str(review.get("title", "")).strip()
        author = str(review.get("author", "")).strip()
        url = str(review.get("url", "")).strip()
        if not title or not author or not url:
            raise ValueError(f"rednote_review_posts[{index}] requires title, author, and url")
        validate_url(url, ("rednote.com",), f"rednote_review_posts[{index}].url")
        if url in seen_urls:
            raise ValueError("rednote_review_posts must use five distinct URLs")
        seen_urls.add(url)
        author_key = normalize_text(author)
        if author_key in seen_authors:
            raise ValueError("rednote_review_posts must use five distinct authors")
        seen_authors.add(author_key)
        recommended = review.get("recommended")
        if not isinstance(recommended, bool):
            raise ValueError(f"rednote_review_posts[{index}].recommended must be boolean")
        recommendation_count += int(recommended)
        avoidance_terms = review.get("avoidance_terms", [])
        if not isinstance(avoidance_terms, list) or not all(
            isinstance(term, str) and term in AVOIDANCE_TERMS for term in avoidance_terms
        ):
            raise ValueError(
                f"rednote_review_posts[{index}].avoidance_terms may contain only 避雷 or 踩雷"
            )
        assessment = str(review.get("assessment", "")).strip()
        detected_terms = [term for term in AVOIDANCE_TERMS if term in f"{title} {assessment}"]
        review["avoidance_terms"] = list(dict.fromkeys([*avoidance_terms, *detected_terms]))
        avoidance_count += int(bool(review["avoidance_terms"]))
        normalized_reviews.append(review)
    item["rednote_review_posts"] = normalized_reviews
    item["rednote_recommendation_count"] = recommendation_count
    item["rednote_avoidance_keyword_count"] = avoidance_count
    if avoidance_count:
        avoidance_summary = str(item.get("avoidance_summary", "")).strip()
        if not avoidance_summary:
            raise ValueError("avoidance_summary is required when a review contains 避雷 or 踩雷")
        annotation = f"有人避雷：{avoidance_summary}"
        warning = str(item.get("warning", "")).strip()
        item["warning"] = f"{annotation} {warning}".strip()


def validate_candidate(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("each candidate must be a JSON object")
    item = dict(raw)
    missing = [field for field in REQUIRED_FIELDS if item.get(field) in (None, "")]
    if missing:
        raise ValueError(f"missing required fields: {', '.join(missing)}")
    try:
        rating = float(item["google_rating"])
    except (TypeError, ValueError) as exc:
        raise ValueError("google_rating must be numeric") from exc
    if not 0 <= rating <= 5:
        raise ValueError("google_rating must be between 0 and 5")
    item["google_rating"] = rating
    review_count = item.get("google_review_count", 0)
    if isinstance(review_count, bool):
        raise ValueError("google_review_count must be a non-negative integer")
    try:
        review_count = int(review_count)
    except (TypeError, ValueError) as exc:
        raise ValueError("google_review_count must be a non-negative integer") from exc
    if review_count < 0:
        raise ValueError("google_review_count must be a non-negative integer")
    item["google_review_count"] = review_count
    validate_url(str(item["google_maps_url"]), ("google.com", "goo.gl"), "google_maps_url")
    validate_url(str(item["rednote_url"]), ("rednote.com",), "rednote_url")
    validate_rednote_reviews(item)
    dishes = item.get("recommended_dishes", [])
    if isinstance(dishes, str):
        dishes = [dishes]
    if not isinstance(dishes, list) or not all(isinstance(dish, str) for dish in dishes):
        raise ValueError("recommended_dishes must be a string or list of strings")
    item["recommended_dishes"] = [dish.strip() for dish in dishes if dish.strip()]
    if not candidate_keys(item):
        raise ValueError("candidate must produce at least one deduplication key")
    return item


def load_candidates(path: str) -> list[dict[str, Any]]:
    if path == "-":
        payload = json.load(sys.stdin)
    else:
        with open(path, encoding="utf-8") as handle:
            payload = json.load(handle)
    if isinstance(payload, dict) and "restaurants" in payload:
        payload = payload["restaurants"]
    if not isinstance(payload, list):
        raise ValueError("input must be a JSON array or an object with a restaurants array")
    return [validate_candidate(item) for item in payload]


def load_history(path: Path) -> tuple[list[dict[str, Any]], set[str]]:
    records: list[dict[str, Any]] = []
    keys: set[str] = set()
    if not path.exists():
        return records, keys
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid history JSON on line {line_number}: {exc}") from exc
            if not isinstance(record, dict):
                raise ValueError(f"invalid history record on line {line_number}")
            records.append(record)
            keys.update(candidate_keys(record))
    return records, keys


def markdown_link(label: str, url: str) -> str:
    return f"[{label}]({url})" if url else label


def write_report(path: Path, run_date: str, added: list[dict[str, Any]], skipped: list[dict[str, Any]]) -> None:
    lines = [f"# Bay Area restaurant discoveries — {run_date}", ""]
    if not added:
        lines.extend(["No new qualifying restaurants were found.", ""])
    for item in added:
        rating = item["google_rating"]
        reviews = item.get("google_review_count", 0)
        lines.extend(
            [
                f"## {item['name']} — {item['city']}",
                "",
                f"- Google Maps: {rating:g} ({reviews:,} reviews)",
                f"- Address: {item.get('address', '') or 'Not recorded'}",
                f"- Discovery: {item.get('discovery_type', 'recent_discovery')}",
                f"- RedNote date: {item.get('rednote_published_at', '') or 'Unknown'}",
                f"- RedNote recommendations: {item.get('rednote_recommendation_count', 0)}/5",
                f"- Sources: {markdown_link('RedNote', item['rednote_url'])} · {markdown_link('Google Maps', item['google_maps_url'])}",
            ]
        )
        if item.get("recommended_dishes"):
            lines.append(f"- Recommended dishes: {', '.join(item['recommended_dishes'])}")
        if item.get("summary"):
            lines.append(f"- Why consider it: {item['summary']}")
        if item.get("warning"):
            lines.append(f"- Warning: {item['warning']}")
        review_posts = item.get("rednote_review_posts", [])
        if review_posts:
            lines.append("- Five RedNote reviews:")
            for review in review_posts:
                verdict = "recommended" if review.get("recommended") else "not recommended"
                lines.append(
                    f"  - {markdown_link(review.get('title', 'Review'), review.get('url', ''))} — {verdict}"
                )
        lines.append("")
    low_rating = sum(1 for row in skipped if row["reason"] == "rating_below_threshold")
    duplicate = sum(1 for row in skipped if row["reason"] == "duplicate")
    insufficient_recommendations = sum(
        1 for row in skipped if row["reason"] == "insufficient_rednote_recommendations"
    )
    lines.extend(
        [
            "## Run summary",
            "",
            f"- Added: {len(added)}",
            f"- Skipped below rating threshold: {low_rating}",
            f"- Skipped with four or fewer RedNote recommendations: {insufficient_recommendations}",
            f"- Skipped as duplicates: {duplicate}",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def default_state_root() -> Path:
    codex_root = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    return codex_root / "data" / "bay-area-food"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Candidate JSON file, or - for stdin")
    parser.add_argument("--run-date", default=dt.date.today().isoformat(), help="Run date in YYYY-MM-DD")
    parser.add_argument("--min-rating", type=float, default=3.0)
    parser.add_argument("--store", type=Path)
    parser.add_argument("--report-dir", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        dt.date.fromisoformat(args.run_date)
        if not 0 <= args.min_rating <= 5:
            raise ValueError("--min-rating must be between 0 and 5")
        candidates = load_candidates(args.input)
        state_root = default_state_root()
        store = args.store or state_root / "restaurants.jsonl"
        report_dir = args.report_dir or state_root / "reports"
        store.parent.mkdir(parents=True, exist_ok=True)
        lock_path = store.with_suffix(store.suffix + ".lock")
        with lock_path.open("a+", encoding="utf-8") as lock_handle:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
            history_records, seen_keys = load_history(store)
            added: list[dict[str, Any]] = []
            skipped: list[dict[str, Any]] = []
            run_keys: set[str] = set()
            for item in candidates:
                if item["rednote_recommendation_count"] <= 4:
                    skipped.append(
                        {"name": item["name"], "reason": "insufficient_rednote_recommendations"}
                    )
                    continue
                if item["google_rating"] < args.min_rating:
                    skipped.append({"name": item["name"], "reason": "rating_below_threshold"})
                    continue
                keys = candidate_keys(item)
                if keys & (seen_keys | run_keys):
                    skipped.append({"name": item["name"], "reason": "duplicate"})
                    continue
                record = dict(item)
                record["first_seen_date"] = args.run_date
                record["saved_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
                record["dedupe_keys"] = sorted(keys)
                added.append(record)
                run_keys.update(keys)
            if added:
                with store.open("a", encoding="utf-8") as handle:
                    for record in added:
                        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
                    handle.flush()
                    os.fsync(handle.fileno())
            report_path = report_dir / f"{args.run_date}.md"
            report_items = [
                record
                for record in history_records
                if record.get("first_seen_date") == args.run_date
            ]
            report_items.extend(added)
            write_report(report_path, args.run_date, report_items, skipped)
        result = {
            "added_count": len(added),
            "skipped_count": len(skipped),
            "added": added,
            "skipped": skipped,
            "store": str(store),
            "report": str(report_path),
        }
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
