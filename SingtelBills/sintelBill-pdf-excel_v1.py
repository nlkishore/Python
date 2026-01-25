import pdfplumber
import pandas as pd
import re
from pathlib import Path

BILLS_FOLDER = "C:/Singtel-Bills"
OUTPUT_FILE = "C:/Singtel-Bills/Singtel_Consolidated_Bills.xlsx"


def extract_text(pdf_path):
    print(f"\n--- Extracting text from {pdf_path.name} ---")
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            page_text = page.extract_text()
            if page_text:
                print(f"[Page {i+1}] Text extracted")
                text += page_text + "\n"
            else:
                print(f"[Page {i+1}] NO text extracted")
    return text


def extract_bill_month(text):
    print("\n--- Detecting Bill Month ---")
    print(text[text.find("Bill Period"): text.find("Bill Period") + 80])

    match = re.search(
        r"Bill Period[\s\S]{0,50}?-\s*\d+\s+(\w+\s+\d{4})",
        text
    )

    if match:
        print("Bill Month Found:", match.group(1))
        return match.group(1)

    print("❌ Bill Month NOT found")
    return "Unknown Month"


def extract_summary(text):
    print("\n--- Extracting Summary ---")

    patterns = {
        "Enhance Fibre Home Bundle": r"Enhance Fibre Home Bundle\s+([\d]+\.\d{2})",
        "Singtel TV": r"Singtel TV\s+([\d]+\.\d{2})",
        "Mobile (All Lines)": r"Mobile\s+([\d]+\.\d{2})",
        "GST": r"GST\s+([\d]+\.\d{2})",
        "Total Bill": r"Total Current Charges\s+([\d]+\.\d{2})"
    }

    rows = []
    for label, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            print(f"{label}: {match.group(1)}")
            rows.append([label, float(match.group(1))])
        else:
            print(f"❌ {label} NOT found")

    return pd.DataFrame(rows, columns=["Category", "Amount (SGD)"])


def extract_mobile_lines(text):
    print("\n--- Extracting Mobile Lines ---")

    pattern = re.compile(
        r"Mobile\s*-\s*(\d{8})[\s\S]*?Total\s+([\d]+\.\d{2})"
    )

    rows = []
    for match in pattern.finditer(text):
        print(f"Mobile {match.group(1)} → {match.group(2)}")
        rows.append([match.group(1), float(match.group(2))])

    if not rows:
        print("❌ No mobile lines detected")

    return pd.DataFrame(rows, columns=["Mobile Number", "Total Charge (SGD)"])


def build_month_sheet(text, bill_month):
    summary_df = extract_summary(text)
    mobile_df = extract_mobile_lines(text)

    rows = [
        ["BILL MONTH", bill_month],
        [],
        ["SUMMARY"],
        ["Category", "Amount (SGD)"]
    ]

    rows.extend(summary_df.values.tolist())
    rows.extend([[], ["MOBILE LINES"], ["Mobile Number", "Total Charge (SGD)"]])
    rows.extend(mobile_df.values.tolist())

    return pd.DataFrame(rows)


def main():
    pdfs = list(Path(BILLS_FOLDER).glob("*.pdf"))

    if not pdfs:
        print("❌ No PDFs found in 'bills' folder")
        return

    with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
        for pdf in pdfs:
            print(f"\n========== {pdf.name} ==========")
            text = extract_text(pdf)
            bill_month = extract_bill_month(text)
            df = build_month_sheet(text, bill_month)

            df.to_excel(
                writer,
                sheet_name=bill_month[:31],
                index=False,
                header=False
            )

    print("\n✅ Excel created:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
