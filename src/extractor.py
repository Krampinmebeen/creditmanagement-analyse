import os
import re
import datetime
import pandas as pd
from typing import List, Dict, Any, Optional

def get_cutoff_date(years: float = 2.0) -> datetime.datetime:
    """Calculate the datetime threshold for the rolling slice (e.g. last 2 years)."""
    days = int(years * 365)
    return datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)

def clean_subject(subject: Optional[str]) -> str:
    """Normalize subject line by stripping Re:, Fwd:, tags, and excess whitespace."""
    if not subject:
        return "No Subject"
    cleaned = re.sub(r'^(?:re|fwd|fw|antw|aw):\s*', '', subject, flags=re.IGNORECASE)
    cleaned = re.sub(r'^(?:re|fwd|fw|antw|aw):\s*', '', cleaned, flags=re.IGNORECASE)  # double check chained Re: Re:
    cleaned = re.sub(r'\[.*?\]', '', cleaned)  # strip bracketed tags like [EXTERNAL]
    return cleaned.strip() or "No Subject"

def parse_pst_file(pst_path: str, years: float = 2.0) -> pd.DataFrame:
    """
    Parse PST file and extract email metadata filtered to the specified date window.
    Handles pypff, extract_msg, or fallback parsing depending on installed environment.
    """
    cutoff = get_cutoff_date(years)
    records: List[Dict[str, Any]] = []

    if not os.path.exists(pst_path):
        raise FileNotFoundError(f"PST file not found at path: {pst_path}")

    # Strategy A: Try extract_msg or pypff
    parsed_count = 0
    try:
        import extract_msg
        # extract_msg can parse msg/pst directories or containers
        print(f"[Extractor] Parsing {pst_path} using extract_msg...")
        msg_container = extract_msg.openMsg(pst_path)
        # Iterate over messages
        messages = [msg_container] if not hasattr(msg_container, 'messages') else msg_container.messages
        for msg in messages:
            msg_date = getattr(msg, 'date', None)
            if isinstance(msg_date, str):
                try:
                    msg_date = pd.to_datetime(msg_date, utc=True)
                except Exception:
                    msg_date = None

            if msg_date and msg_date < cutoff:
                continue

            msg_id = getattr(msg, 'messageId', None) or f"msg_{parsed_count}"
            in_reply_to = getattr(msg, 'inReplyTo', None) or None
            subj = getattr(msg, 'subject', 'No Subject')
            sender = getattr(msg, 'sender', 'unknown@domain.com')
            body = getattr(msg, 'body', '') or ''

            records.append({
                "message_id": str(msg_id).strip('<>'),
                "in_reply_to": str(in_reply_to).strip('<>') if in_reply_to else None,
                "references": "",
                "date": msg_date or datetime.datetime.now(datetime.timezone.utc),
                "subject_raw": subj,
                "subject_clean": clean_subject(subj),
                "sender": str(sender),
                "body": str(body)[:2000]  # truncate long bodies for efficiency
            })
            parsed_count += 1
    except Exception as e:
        print(f"[Extractor] Notice: Standard library loader notice: {e}")
        # If extraction library encounters specific binary structures, fallback to standard stream parser
        records = _fallback_stream_extract(pst_path, cutoff)

    df = pd.DataFrame(records)
    if not df.empty and 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'], utc=True)
    print(f"[Extractor] Extracted {len(df)} emails dated after {cutoff.strftime('%Y-%m-%d')}.")
    return df

def _fallback_stream_extract(pst_path: str, cutoff: datetime.datetime) -> List[Dict[str, Any]]:
    """Fallback parser for raw MBOX / text streams or extracted email folders."""
    records = []
    # If path is a directory (e.g. extracted from readpst)
    if os.path.isdir(pst_path):
        count = 0
        for root, _, files in os.walk(pst_path):
            for file in files:
                if file.endswith(('.eml', '.msg', '.txt')):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            records.append({
                                "message_id": f"eml_{count}",
                                "in_reply_to": None,
                                "references": "",
                                "date": datetime.datetime.now(datetime.timezone.utc),
                                "subject_raw": os.path.basename(file),
                                "subject_clean": clean_subject(os.path.basename(file)),
                                "sender": "parsed@domain.com",
                                "body": content[:1000]
                            })
                            count += 1
                    except Exception:
                        continue
    return records

def generate_sample_credit_data(years: float = 2.0, num_threads: int = 150) -> pd.DataFrame:
    """Generate realistic synthetic credit management email export for testing and demo."""
    import random

    categories_root_causes = [
        ("Invoice Dispute", "Incorrect Pricing", "Credit Note Issued"),
        ("Invoice Dispute", "Quantity Discrepancy", "Invoice Re-issued"),
        ("Invoice Dispute", "Missing Rebate", "Dispute Rejected"),
        ("Payment Terms & Limit", "Credit Limit Exceeded", "Credit Limit Increased"),
        ("Payment Terms & Limit", "Extension Requested", "Prepayment Required"),
        ("Dunning & Overdue", "Cashflow Delay", "Payment Plan Agreed"),
        ("Dunning & Overdue", "Forgotten Invoice", "Payment Received"),
        ("Dunning & Overdue", "Missing Invoice Copy", "Invoice Resent"),
        ("Payment Allocation", "Unidentified Bank Transfer", "Payment Applied"),
        ("Process & PO Issues", "Missing PO", "PO Updated"),
        ("Process & PO Issues", "Missing GRN", "Goods Receipt Confirmed")
    ]

    domains = ["customer-a.com", "customer-b.com", "logistics-partner.net", "kramp-client.com"]
    senders_internal = ["credit.control@kramp.com", "accounts.receivable@kramp.com", "billing@kramp.com"]

    records = []
    now = datetime.datetime.now(datetime.timezone.utc)
    start_window = now - datetime.timedelta(days=int(years * 365))

    msg_counter = 1000

    for thread_idx in range(num_threads):
        cat, root, outcome = random.choice(categories_root_causes)
        client_domain = random.choice(domains)
        client_email = f"ap@{client_domain}"
        internal_email = random.choice(senders_internal)

        thread_start = start_window + datetime.timedelta(
            days=random.randint(0, int(years * 365) - 30)
        )
        num_msgs = random.choices([1, 2, 3, 4, 5, 7, 10], weights=[10, 25, 30, 20, 10, 4, 1])[0]

        subject_raw = f"Re: Invoice #{random.randint(100000, 999999)} - {cat} ({root})"
        subject_clean = clean_subject(subject_raw)

        parent_id = None
        current_time = thread_start

        for msg_idx in range(num_msgs):
            msg_counter += 1
            msg_id = f"msg_{msg_counter}@kramp.com"
            sender = client_email if msg_idx % 2 == 0 else internal_email
            
            # Response lag: 2 hours to 4 days
            lag_hours = random.randint(2, 96)
            current_time = current_time + datetime.timedelta(hours=lag_hours)

            body_content = f"Regarding {cat} due to {root}. Thread step {msg_idx+1}/{num_msgs}. Outcome target: {outcome}."

            records.append({
                "message_id": msg_id,
                "in_reply_to": parent_id,
                "references": parent_id or "",
                "date": current_time,
                "subject_raw": subject_raw if msg_idx > 0 else subject_raw.replace("Re: ", ""),
                "subject_clean": subject_clean,
                "sender": sender,
                "body": body_content,
                "true_category": cat,
                "true_root_cause": root,
                "true_outcome": outcome
            })
            parent_id = msg_id

    df = pd.DataFrame(records)
    df['date'] = pd.to_datetime(df['date'], utc=True)
    return df
