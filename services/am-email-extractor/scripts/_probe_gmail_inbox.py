"""One-shot: list broker statement hits for a connected user (dev probe)."""
import gmail_integration

UID = "42dc5b05-e171-4845-bb39-5363783144c5"


def main() -> None:
    service, _, _ = gmail_integration.get_gmail_service(UID)
    if not service:
        print("NO_SERVICE")
        raise SystemExit(1)
    print("service_ok")
    for broker in ("groww", "zerodha", "dhan", "mstock", "angleone"):
        msgs = gmail_integration.search_emails(service, broker, days_back=365)
        print(f"BROKER {broker}: {len(msgs)}")
    q = (
        "has:attachment (from:groww.in OR from:zerodha OR from:angelone "
        "OR from:dhan OR from:mstock OR subject:holding OR subject:demat) newer_than:2y"
    )
    r = service.users().messages().list(userId="me", q=q, maxResults=20).execute()
    msgs = r.get("messages") or []
    print(f"BROAD: {len(msgs)}")
    for m in msgs[:15]:
        d = gmail_integration.get_message_details(service, m["id"])
        if not d:
            continue
        print(f"  - {d.get('from', '')[:55]} | {d.get('subject', '')[:75]}")


if __name__ == "__main__":
    main()
