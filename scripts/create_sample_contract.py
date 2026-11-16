"""Generate a fictional contract PDF for local demo testing."""

from pathlib import Path

import pymupdf


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = PROJECT_ROOT / "data" / "sample_contract.pdf"

SAMPLE_TEXT = """+SERVICE AGREEMENT

This fictional Service Agreement is made between Northstar Analytics LLC
(the Provider) and Cedar Grove Market Inc. (the Client).

1. Effective Date and Term
This Agreement begins on January 1, 2026 and continues through June 30, 2026,
unless ended earlier under this Agreement.

2. Services
The Provider will prepare monthly inventory and sales analytics reports for
the Client and provide one remote review meeting each month.

3. Fees and Payment
The Client will pay a service fee of USD 2,500 per month. The Provider will
issue an invoice on the first business day of each month. Payment is due
within fifteen (15) calendar days after the invoice date. Late balances may
accrue interest at 1.5% per month, or the maximum amount allowed by law,
whichever is lower.

4. Confidentiality
Each party will use the other party's confidential information only to perform
this Agreement and will take reasonable steps to protect it.

5. Termination
Either party may terminate this Agreement by giving thirty (30) days' written
notice to the other party.

6. Signatures
The parties may sign separate copies of this Agreement. This sample is
fictional and is provided only to demonstrate document extraction.

Provider: Northstar Analytics LLC
Authorized representative: Morgan Lee

Client: Cedar Grove Market Inc.
Authorized representative: Jamie Patel
"""


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    document = pymupdf.open()
    page = document.new_page()
    page.insert_textbox(
        pymupdf.Rect(56, 52, 540, 745),
        SAMPLE_TEXT,
        fontname="helv",
        fontsize=10.5,
        lineheight=1.3,
        color=(0.12, 0.18, 0.16),
    )
    document.set_metadata(
        {
            "title": "Fictional Service Agreement",
            "author": "Clausewise Demo",
            "subject": "Synthetic contract for local testing",
        }
    )
    document.save(OUTPUT_PATH)
    document.close()
    print(f"Created sample contract: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
