from PyPDF2 import PdfMerger
import os

def merge_pdfs(pdf_list, output_path):
    merger = PdfMerger()
    for pdf in pdf_list:
        if os.path.exists(pdf):
            merger.append(pdf)
        else:
            print(f"Warning: File not found - {pdf}")
    merger.write(output_path)
    merger.close()
    print(f"Merged PDF saved to: {output_path}")

# Example usage
pdf_files = [
    "C:/Kishore-Resume/LaxmiKishoreNalluri_resume.pdf",
    "C:/Kishore-Resume/Kishore N-v1.pdf"
    
]

merge_pdfs(pdf_files, "C:/Kishore-Resume/combinedResume.pdf")