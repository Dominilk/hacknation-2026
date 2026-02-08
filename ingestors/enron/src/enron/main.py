"""Enron email dataset ingestor — loads from HuggingFace and POSTs to the core /ingest endpoint."""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone

import httpx
from datasets import load_dataset
from shared import IngestEvent

DATE_START = datetime(2001, 6, 1, tzinfo=timezone.utc)
DATE_END = datetime(2001, 12, 1, tzinfo=timezone.utc)

KEY_EMPLOYEES = [
    "lay-k",
    "skilling-j",
    "lavorato-j",
    "dasovich-j",
    "kaminski-v",
    "kitchen-l",
    "kean-s",
    "delainey-d",
]
SENT_FOLDERS = {"_sent_mail", "sent_mail", "sent_items", "sent"}
INGEST_URL = "http://localhost:8000/ingest"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ingest Enron emails into the knowledge graph")
    p.add_argument("--url", default=INGEST_URL, help="Core service /ingest URL")
    p.add_argument("--limit", type=int, default=0, help="Max emails to send (0 = all)")
    p.add_argument("--dry-run", action="store_true", help="Preview without sending")
    return p.parse_args()


def is_sent_by_key_employee(file_path: str) -> bool:
    """Check if the email is in a sent folder of one of our key employees."""
    parts = file_path.strip("/").split("/")
    if len(parts) < 2:
        return False
    custodian = parts[0]
    folder = parts[1]
    return custodian in KEY_EMPLOYEES and folder in SENT_FOLDERS


def clean_addrs(raw: list[str]) -> list[str]:
    return [a for a in raw if a.strip()]


def make_event(row: dict) -> IngestEvent | None:
    body = row.get("body") or ""
    if len(body) < 50 or len(body) > 10_000:
        return None

    to = clean_addrs(row.get("to") or [])
    cc = clean_addrs(row.get("cc") or [])
    bcc = clean_addrs(row.get("bcc") or [])

    header_parts = [
        f"Subject: {row.get('subject', '')}",
        f"From: {row.get('from', '')}",
    ]
    if to:
        header_parts.append(f"To: {', '.join(to)}")
    if cc:
        header_parts.append(f"Cc: {', '.join(cc)}")
    if bcc:
        header_parts.append(f"Bcc: {', '.join(bcc)}")

    content = "\n".join(header_parts) + "\n\n" + body

    return IngestEvent(
        content=content,
        timestamp=row["date"],
        metadata={
            "source": "enron",
            "message_id": row.get("message_id", ""),
            "from": row.get("from", ""),
            "subject": row.get("subject", ""),
        },
    )


def load_emails() -> list[IngestEvent]:
    """Load and filter Enron emails from HuggingFace, return sorted by timestamp."""
    ds = load_dataset("corbt/enron-emails", split="train", streaming=True)

    events: list[IngestEvent] = []
    for row in ds:
        file_path = row.get("file_name", "")
        if not is_sent_by_key_employee(file_path):
            continue
        dt = row.get("date")
        if dt is None or dt < DATE_START or dt >= DATE_END:
            continue
        event = make_event(row)
        if event:
            events.append(event)

    events.sort(key=lambda e: e.timestamp)
    return events


async def send_events(events: list[IngestEvent], url: str) -> None:
    async with httpx.AsyncClient(timeout=120.0) as client:
        for i, event in enumerate(events, 1):
            resp = await client.post(url, json=event.to_dict())
            resp.raise_for_status()
            print(f"[{i}/{len(events)}] Ingested: {event.metadata.get('subject', '')[:60]}")


def main():
    args = parse_args()
    print(f"Loading Enron emails from HuggingFace (Jun–Nov 2001, {len(KEY_EMPLOYEES)} key employees)...")
    events = load_emails()

    if args.limit > 0:
        events = events[: args.limit]

    print(f"Found {len(events)} emails after filtering")

    if args.dry_run:
        for i, e in enumerate(events[:20], 1):
            print(f"  {i}. [{e.timestamp.date()}] {e.metadata.get('from', '')} — {e.metadata.get('subject', '')[:60]}")
        if len(events) > 20:
            print(f"  ... and {len(events) - 20} more")
        return

    if not events:
        print("No emails to ingest.")
        return

    print(f"Sending {len(events)} emails to {args.url}...")
    asyncio.run(send_events(events, args.url))
    print("Done.")


if __name__ == "__main__":
    main()
