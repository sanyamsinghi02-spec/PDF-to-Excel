import io
import tempfile
import os
import streamlit as st
import pandas as pd
import pdfplumber
import pypdfium2 as pdfium
import pytesseract
from PIL import Image

st.title("📄 Universal PDF to Excel Creator")
st.write("Convert any document into an Excel spreadsheet effortlessly. Supports digital text PDFs, scanned certificates, and handwritten notes!")

uploaded_file = st.file_uploader("Upload your PDF file", type=["pdf"])

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.read())
        tmp_path = tmp_file.name

    extracted_data = []

    with st.spinner("Processing document using Universal & OCR pipeline..."):
        # Step 1: Try extracting digital text first (Fast & perfect for clean digital PDFs)
        with pdfplumber.open(tmp_path) as pdf:
            for page_idx, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text and text.strip():
                    lines = [line.strip() for line in text.split('\n') if line.strip()]
                    for line_idx, line in enumerate(lines):
                        extracted_data.append({
                            "Page": page_idx + 1,
                            "Line Number": line_idx + 1,
                            "Extraction Mode": "Digital Text",
                            "Extracted Content": line
                        })

        # Step 2: Fallback to OCR if no digital text layer was found (Scans, Certificates, Handwritten Notes)
        if not extracted_data:
            st.info("No digital text layer detected. Running advanced OCR pipeline for scanned/handwritten content...")
            
            pdf_file = pdfium.PdfDocument(tmp_path)
            for page_idx, page in enumerate(pdf_file):
                # Render at high resolution (scale=3) so handwritten loops and fonts stay crisp
                image = page.render(scale=3).to_pil()
                
                # Preprocess: Grayscale and thresholding to filter out notebook lines/background noise
                gray = image.convert('L')
                threshold = 170
                processed_image = gray.point(lambda p: 255 if p > threshold else 0)

                # Run OCR with sparse text mode (--psm 11) to handle handwritten notes and flowcharts
                custom_config = r'--oem 3 --psm 11'
                text = pytesseract.image_to_string(processed_image, config=custom_config)
                
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                for line_idx, line in enumerate(lines):
                    extracted_data.append({
                        "Page": page_idx + 1,
                        "Line Number": line_idx + 1,
                        "Extraction Mode": "OCR (Scanned/Handwritten)",
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
            df_result.to_excel(writer, sheet_name="Universal_Extracted", index=False)
        output.seek(0)

        st.download_button(
            label="📥 Download Clean Excel File",
            data=output,
            file_name="universal_pdf_extracted.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.error("Could not extract any readable content from this PDF.")
