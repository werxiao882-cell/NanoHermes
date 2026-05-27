#!/usr/bin/env python3
"""
PDF to Markdown Converter

Requirements:
    pip install pymupdf
    (or pip install fitz)

Usage:
    python pdf2md.py input.pdf output.md
"""

import sys
import os

def convert_pdf_to_md(pdf_path, output_md_path=None):
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("Error: 'pymupdf' library is not installed.")
        print("Please install it by running: pip install pymupdf")
        sys.exit(1)

    if not os.path.exists(pdf_path):
        print(f"Error: File '{pdf_path}' not found.")
        sys.exit(1)

    try:
        doc = fitz.open(pdf_path)
        md_parts = []

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            # PyMuPDF 1.24.0+ supports 'markdown' output mode directly
            # It attempts to detect headers, lists, bold/italic text.
            try:
                page_text = page.get_text("markdown")
            except Exception:
                # Fallback for older versions
                page_text = page.get_text("text")
                page_text = f"## Page {page_num + 1}\n\n" + page_text

            md_parts.append(page_text)
        
        full_md = "\n\n".join(md_parts)

        if output_md_path:
            with open(output_md_path, "w", encoding="utf-8") as f:
                f.write(full_md)
            print(f"Successfully converted '{pdf_path}' to '{output_md_path}'")
        else:
            print(full_md)

    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pdf2md.py <input.pdf> [output.md]")
        print("  input.pdf   : Path to the input PDF file")
        print("  output.md   : (Optional) Path to save the output Markdown file. If omitted, output is printed to console.")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    convert_pdf_to_md(input_file, output_file)
