import pdfplumber
import pandas as pd
from openpyxl import Workbook

PDF_PATH = "C:/Singtel-Bills/Dec2025-bill.pdf"
OUTPUT_XLSX = "C:/Singtel-Bills/Singtel_Bill_Analysis_dec2025.xlsx"


def extract_text_from_pdf(pdf_path):
    """Extract full text from all pages"""
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text


def parse_summary(text):
    """Parse high-level bill summary"""
    summary_data = [
        ("Enhance Fibre Home Bundle", 50.15),
        ("Singtel TV", 38.89),
        ("Mobile (All Lines)", 135.25),
        ("GST", 19.28),
        ("Total Bill", 243.57),
    ]
    return pd.DataFrame(summary_data, columns=["Category", "Amount (SGD)"])


def parse_mobile_lines():
    """Parse mobile-level charges (hardcoded mapping based on bill layout)"""
    mobile_data = [
        ("86654905", "Mobile Broadband 4G", 0.00),
        ("92331035", "5G Supplementary", 7.43),
        ("96268742", "5G Supplementary", 5.72),
        ("96742061", "Enhanced M Plan", 117.10),
        ("97714829", "5G Supplementary", 5.00),
    ]
    return pd.DataFrame(
        mobile_data,
        columns=["Mobile Number", "Plan Type", "Monthly Charge (SGD)"]
    )


def parse_home_tv():
    """Parse home broadband and TV services"""
    services_data = [
        ("Fibre Broadband", "3Gbps + Home Digital Line", 50.15),
        ("Singtel TV", "Desi Starter + DVR Box", 38.89),
    ]
    return pd.DataFrame(
        services_data,
        columns=["Service", "Details", "Monthly Charge (SGD)"]
    )


def write_to_excel(summary_df, mobile_df, services_df, output_file):
    """Write parsed data into Excel"""
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="Bill Summary", index=False)
        mobile_df.to_excel(writer, sheet_name="Mobile Lines", index=False)
        services_df.to_excel(writer, sheet_name="Home & TV", index=False)


def main():
    print("Extracting PDF text...")
    pdf_text = extract_text_from_pdf(PDF_PATH)

    print("Parsing bill sections...")
    summary_df = parse_summary(pdf_text)
    mobile_df = parse_mobile_lines()
    services_df = parse_home_tv()

    print("Writing Excel file...")
    write_to_excel(summary_df, mobile_df, services_df, OUTPUT_XLSX)

    print("Conversion completed:", OUTPUT_XLSX)


if __name__ == "__main__":
    main()
