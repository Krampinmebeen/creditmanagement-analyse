import re
import pandas as pd
from typing import Tuple

TAXONOMY_RULES = [
    # Category, Root Cause, Outcome, Keywords regex pattern (English & Dutch)
    (
        "Invoice Dispute", 
        "Incorrect Pricing", 
        "Credit Note Issued", 
        r"(price|pricing|incorrect price|unit price|wrong rate|discrepancy in price|prijs|prijsverschil|foutieve prijs|verkeerde prijs|creditnota|credit nota|gecrediteerd)"
    ),
    (
        "Invoice Dispute", 
        "Quantity Discrepancy", 
        "Invoice Re-issued", 
        r"(quantity|qty|shortage|missing items|received fewer|count mismatch|aantal|minder ontvangen|manco|aantalverschil|geleverd)"
    ),
    (
        "Invoice Dispute", 
        "Missing Rebate / Discount", 
        "Dispute Rejected", 
        r"(rebate|discount|bonus|bonus deduction|agreed discount|korting|jaarkorting|staaffelkorting|afspraak)"
    ),
    (
        "Payment Terms & Limit", 
        "Credit Limit Exceeded", 
        "Credit Limit Increased", 
        r"(credit limit|limit exceeded|block account|hold order|credit hold|limiet|kredietlimiet|limiet bereikt|geblokkeerd|order op hold)"
    ),
    (
        "Payment Terms & Limit", 
        "Extension Requested", 
        "Prepayment Required", 
        r"(extension|payment terms|due date extension|longer terms|betalingstermijn|uitstel|uitstel van betaling|verlenging)"
    ),
    (
        "Dunning & Overdue", 
        "Cashflow / Liquidity Delay", 
        "Payment Plan Agreed", 
        r"(cashflow|delay in payment|liquidity|late payment|unable to pay|installment|liquiditeit|betalingsregeling|regeling|later betalen)"
    ),
    (
        "Dunning & Overdue", 
        "Missing Invoice Copy", 
        "Invoice Resent", 
        r"(send copy|missing invoice|copy of invoice|did not receive invoice|resend invoice|geen factuur ontvangen|kopie factuur|ontvangen factuur)"
    ),
    (
        "Dunning & Overdue", 
        "Direct Debit / Incasso Issue", 
        "Payment Received", 
        r"(dunning|overdue|incasso|mislukte incasso|direct debit|herinnering|aanmaning|openstaand|vervallen)"
    ),
    (
        "Payment Allocation", 
        "Unidentified Bank Transfer", 
        "Payment Applied", 
        r"(remittance|bank transfer|unallocated|proof of payment|payment reference|allocat|bankoverschrijving|betalingsbewijs|storno|afschrift)"
    ),
    (
        "Process & PO Issues", 
        "Missing PO / Order Ref", 
        "PO Updated", 
        r"(po number|purchase order|missing po|po required|no po|ordernummer|inkooporder|incoopnummer|geen po)"
    ),
    (
        "Process & PO Issues", 
        "Missing GRN / POD", 
        "Goods Receipt Confirmed", 
        r"(grn|goods received|receipt note|delivery note|pod|proof of delivery|pakbon|ontvangstbewijs|afgeleverd)"
    )
]

def classify_thread_text(text: str) -> Tuple[str, str, str]:
    """Classify thread subject and body text into Category, Root Cause, and Outcome."""
    if not text or not isinstance(text, str):
        return ("General Credit Query", "Unclassified Issue", "Pending Review")

    lower_text = text.lower()
    for cat, root, outcome, pattern in TAXONOMY_RULES:
        if re.search(pattern, lower_text):
            return (cat, root, outcome)

    return ("General Credit Query", "General Communication", "Resolved")

def classify_threads(threads_df: pd.DataFrame) -> pd.DataFrame:
    """Classify all threads in DataFrame and append category, root_cause, outcome columns."""
    if threads_df.empty:
        return threads_df

    categories = []
    root_causes = []
    outcomes = []

    for idx, row in threads_df.iterrows():
        if pd.notna(row.get('true_category')) and str(row.get('true_category')) != 'None':
            categories.append(row['true_category'])
            root_causes.append(row['true_root_cause'])
            outcomes.append(row['true_outcome'])
        else:
            combined_text = f"{row.get('subject_clean', '')} {row.get('concatenated_body', '')}"
            cat, root, outcome = classify_thread_text(combined_text)
            categories.append(cat)
            root_causes.append(root)
            outcomes.append(outcome)

    threads_df['category'] = categories
    threads_df['root_cause'] = root_causes
    threads_df['outcome'] = outcomes

    print(f"[Classifier] Classified {len(threads_df)} threads across {threads_df['category'].nunique()} operational categories.")
    return threads_df
