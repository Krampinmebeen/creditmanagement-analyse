import re
import pandas as pd
from typing import Tuple

# Hierarchical Taxonomy Rules: Evaluated strictly in order of precedence.
# Substantive operational root causes (PO, Pricing, GRN) take precedence over generic Dunning triggers.
TAXONOMY_RULES = [
    # 1. PROCESS & PO ISSUES (Highest Priority: Root cause of invoice rejection / delayed payment)
    (
        "Process & PO Issues", 
        "Missing PO / Inkooporder", 
        "PO Provided & Invoice Resent", 
        r"(po number|purchase order|missing po|po required|no po|inkooporder|ordernummer|incoopnummer|geen po|po-nummer|po ontbreekt|inkoop order|bestelnummer|verplicht po|afgekeurde factuur.*po)"
    ),
    (
        "Process & PO Issues", 
        "Missing GRN / Proof of Delivery", 
        "Goods Receipt Confirmed", 
        r"(grn|goods received|receipt note|delivery note|pod|proof of delivery|pakbon|ontvangstbewijs|afgeleverd|afleverbon|CMR|verzendbewijs|ontvangstbevestiging)"
    ),

    # 2. INVOICE / PRICING DISPUTES (Disputes that stall payment)
    (
        "Invoice Dispute", 
        "Incorrect Pricing / Rate Mismatch", 
        "Credit Note Issued", 
        r"(price|pricing|incorrect price|unit price|wrong rate|discrepancy in price|prijs|prijsverschil|foutieve prijs|verkeerde prijs|creditnota|credit nota|gecrediteerd|tarief|prijscorrectie|afgekeurde factuur)"
    ),
    (
        "Invoice Dispute", 
        "Quantity Discrepancy / Shortage", 
        "Invoice Re-issued", 
        r"(quantity|qty|shortage|missing items|received fewer|count mismatch|aantal|minder ontvangen|manco|aantalverschil|geleverd|retour|beschadigd|retouren)"
    ),
    (
        "Invoice Dispute", 
        "Missing Rebate / Discount", 
        "Dispute Rejected / Adjusted", 
        r"(rebate|discount|bonus|bonus deduction|agreed discount|korting|jaarkorting|staffelkorting|betalingskorting|afspraak)"
    ),

    # 3. PAYMENT ALLOCATION & BANK ISSUES
    (
        "Payment Allocation", 
        "Unidentified Remittance / Storno", 
        "Payment Applied", 
        r"(remittance|bank transfer|unallocated|proof of payment|payment reference|allocat|bankoverschrijving|betalingsbewijs|storno|gestorneerd|afschrift|kruispost|zoekgeraakte betaling|betaalbewijs)"
    ),

    # 4. PAYMENT TERMS & CREDIT LIMIT
    (
        "Payment Terms & Limit", 
        "Credit Limit Exceeded / Account Block", 
        "Credit Limit Increased / Prepayment", 
        r"(credit limit|limit exceeded|block account|hold order|credit hold|limiet|kredietlimiet|limiet bereikt|geblokkeerd|order op hold|kredietwaardigheid|geblokkeerde levering)"
    ),
    (
        "Payment Terms & Limit", 
        "Extension / Terms Requested", 
        "Payment Extension Granted", 
        r"(extension|payment terms|due date extension|longer terms|betalingstermijn|uitstel|uitstel van betaling|verlenging|vervaldatum aanpassen)"
    ),

    # 5. SPECIFIC DUNNING CAUSES (Substantive reasons within dunning)
    (
        "Dunning & Overdue", 
        "Cashflow / Payment Plan Request", 
        "Payment Plan Agreed", 
        r"(cashflow|delay in payment|liquidity|late payment|unable to pay|installment|liquiditeit|betalingsregeling|regeling|later betalen|termijn betaling|faillissement|surseance|schuldsanering)"
    ),
    (
        "Dunning & Overdue", 
        "Missing Invoice Copy / Resend Request", 
        "Invoice Resent", 
        r"(send copy|missing invoice|copy of invoice|did not receive invoice|resend invoice|geen factuur ontvangen|kopie factuur|ontvangen factuur|factuur kwijt|niet aangekomen)"
    ),
    (
        "Dunning & Overdue", 
        "Legal / Florijn Incasso Collection", 
        "Forwarded to Agency", 
        r"(florijn|incassobureau|deurwaarder|gerechtsdeurwaarder|incassokosten|sommatie|aanmaning 2e)"
    ),

    # 6. GENERIC DUNNING / AUTOMATED REMINDERS (Evaluated last among triggers)
    (
        "Dunning & Overdue", 
        "Direct Debit / Incasso Follow-up", 
        "Payment Received", 
        r"(dunning|overdue|incasso|mislukte incasso|direct debit|herinnering|aanmaning|openstaand|vervallen|debiteuren|debiteur|rekeninguittreksel|betalingsherinnering)"
    )
]

def classify_thread_text(text: str) -> Tuple[str, str, str]:
    """Classify thread subject and body text into Category, Root Cause, and Outcome."""
    if not text or not isinstance(text, str):
        return ("General Credit Query", "General Communication", "Resolved")

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
        # Evaluate clean subject + full thread body
        combined_text = f"{row.get('subject_clean', '')} {row.get('concatenated_body', '')}"
        cat, root, outcome = classify_thread_text(combined_text)
        categories.append(cat)
        root_causes.append(root)
        outcomes.append(outcome)

    threads_df['category'] = categories
    threads_df['root_cause'] = root_causes
    threads_df['outcome'] = outcomes

    print(f"[Classifier] Classified {len(threads_df):,} threads across {threads_df['category'].nunique()} operational categories.")
    return threads_df
