import io
import tempfile
import os
import streamlit as st
import pandas as pd
import pdfplumber
import pypdfium2 as pdfium
import pytesseract
from PIL import Image

st.title("📄 Universal PDF to Excel Converter")
st.write("Supports digital text PDFs, scanned certificates, and handwritten study notes!")

uploaded_file = st.file_uploader("Upload your PDF file", type=["pdf"])

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.read())
        tmp_path = tmp_file.name

    extracted_data = []

    with st.spinner("Analyzing document (Digital & OCR Pipeline)..."):
        # Method 1: Try extracting digital text first (Fast & perfect for digital PDFs)
        with pdfplumber.open(tmp_path) as pdf:
            for page_idx, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text and text.strip():
                    lines = [line.strip() for line in text.split('\n') if line.strip()]
                    for line_idx, line in enumerate(lines):
                        extracted_data.append({
                            "Page": page_idx + 1,
                            "Line Number": line_idx + 1,
                            "Content Type": "Digital Text",
                            "Extracted Content": line
                        })

        # Method 2: Fallback to OCR if no digital text layer was found (Scans, Certificates, Handwritten notes)
        if not extracted_data:
            st.info("No digital text layer detected. Running advanced OCR for scanned/handwritten document...")
            
            pdf_file = pdfium.PdfDocument(tmp_path)
            for page_idx, page in enumerate(pdf_file):
                # Render at high resolution for handwriting/certificates
                image = page.render(scale=3).to_pil()
                
                # Preprocess: convert to grayscale for high contrast against paper lines/background
                gray_image = image.convert('L')

                # Run OCR with layout analysis config optimized for unstructured text and notes
                custom_config = r'--oem 3 --psm 6'
                text = pytesseract.image_to_string(gray_image, config=custom_config)
                
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                for line_idx, line in enumerate(lines):
                    extracted_data.append({
                        "Page": page_idx + 1,
                        "Line Number": line_idx + 1,
                        "Content Type": "OCR (Scanned/Handwritten)",
                        "Extracted Content": line
                    })

        df_result = pd.DataFrame(extracted_data)

    # Clean up temp file
    os.unlink(tmp_path)

    if not df_result.empty:
        st.success("Extraction successful!")
        
        # Preview extracted lines
        st.write("### Preview:")
        st.dataframe(df_result)

        # Convert to Excel for download
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_result.to_excel(writer, sheet_name="Extracted_Data", index=False)
        output.seek(0)

        st.download_button(
            label="📥 Download Clean Excel File",
            data=output,
            file_name="universal_extracted.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.error("Could not extract any readable content from this PDF.")
