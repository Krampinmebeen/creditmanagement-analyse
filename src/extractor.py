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
    """Normalize subject line by stripping Re:, Fwd:, FW:, AW:, tags, and excess whitespace."""
    if not subject:
        return "No Subject"
    cleaned = str(subject)
    cleaned = re.sub(r'^(?:re|fwd|fw|antw|aw|vs):\s*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'^(?:re|fwd|fw|antw|aw|vs):\s*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\[.*?\]', '', cleaned)
    return cleaned.strip() or "No Subject"

def parse_pst_file(pst_path: str, years: float = 2.0) -> pd.DataFrame:
    """
    Parse PST file using pypff and extract email metadata filtered to the specified date window.
    """
    cutoff = get_cutoff_date(years)
    records: List[Dict[str, Any]] = []

    if not os.path.exists(pst_path):
        raise FileNotFoundError(f"PST file not found at path: {pst_path}")

    import pypff

    print(f"[Extractor] Opening PST file via pypff: {pst_path}")
    pst = pypff.file()
    pst.open(pst_path)
    root = pst.get_root_folder()

    parsed_count = 0
    filtered_count = 0

    def traverse_folder(folder):
        nonlocal parsed_count, filtered_count
        num_msgs = folder.number_of_sub_messages
        for i in range(num_msgs):
            try:
                msg = folder.get_sub_message(i)
                parsed_count += 1

                # Parse date
                raw_date = msg.delivery_time or msg.creation_time or msg.client_submit_time
                if not raw_date:
                    continue

                if isinstance(raw_date, datetime.datetime):
                    if raw_date.tzinfo is None:
                        msg_date = raw_date.replace(tzinfo=datetime.timezone.utc)
                    else:
                        msg_date = raw_date.astimezone(datetime.timezone.utc)
                else:
                    msg_date = pd.to_datetime(raw_date, utc=True)

                if msg_date < cutoff:
                    continue

                headers = msg.transport_headers or ''
                msg_id_match = re.search(r'Message-ID:\s*<([^>]+)>', headers, re.I)
                in_reply_match = re.search(r'In-Reply-To:\s*<([^>]+)>', headers, re.I)

                msg_id = msg_id_match.group(1).strip() if msg_id_match else f"pypff_msg_{parsed_count}"
                in_reply_to = in_reply_match.group(1).strip() if in_reply_match else None

                subj = msg.subject or "No Subject"
                sender = msg.sender_name or "Unknown Sender"

                body_bytes = msg.plain_text_body
                if isinstance(body_bytes, bytes):
                    body_str = body_bytes.decode('utf-8', errors='ignore')
                else:
                    body_str = str(body_bytes or '')

                records.append({
                    "message_id": msg_id,
                    "in_reply_to": in_reply_to,
                    "references": "",
                    "date": msg_date,
                    "subject_raw": subj,
                    "subject_clean": clean_subject(subj),
                    "sender": str(sender),
                    "body": body_str[:1500]  # truncate body snippet
                })
                filtered_count += 1
            except Exception:
                continue

        for sub_folder in folder.sub_folders:
            traverse_folder(sub_folder)

    traverse_folder(root)
    pst.close()

    df = pd.DataFrame(records)
    if not df.empty and 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'], utc=True)

    print(f"[Extractor] Total messages scanned: {parsed_count:,}. Extracted {len(df):,} messages dated after {cutoff.strftime('%Y-%m-%d')}.")
    return df

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
