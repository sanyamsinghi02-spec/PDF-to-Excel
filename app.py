import io
import tempfile
import os
import streamlit as st
import pdfplumber
import pandas as pd
from pdf2image import convert_from_path
import pytesseract
from PIL import Image

st.title("📄 Advanced PDF to Excel Converter")
st.write("Supports both digital text PDFs and scanned image-based documents using OCR.")

uploaded_file = st.file_uploader("Upload your PDF file", type=["pdf"])

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.read())
        tmp_path = tmp_file.name

    with st.spinner("Processing PDF and extracting text/tables..."):
        extracted_tables = []
        
        # Method 1: Try reading text digitally using pdfplumber first
        with pdfplumber.open(tmp_path) as pdf:
            for page_idx, page in enumerate(pdf.pages):
                tables = page.extract_tables()
                if tables:
                    for table in tables:
                        df = pd.DataFrame(table)
                        extracted_tables.append(df)

        # Method 2: Fallback to OCR if no digital text tables were found (Scanned PDF)
        if not extracted_tables:
            st.info("No digital text layer detected. Running OCR for scanned document...")
            images = convert_from_path(tmp_path)
            
            ocr_text_data = []
            for i, image in enumerate(images):
                text = pytesseract.image_to_string(image)
                ocr_text_data.append({"Page": i + 1, "Extracted Text": text})
            
            df_ocr = pd.DataFrame(ocr_text_data)
            extracted_tables.append(df_ocr)

    # Clean up temp file
    os.unlink(tmp_path)

    if extracted_tables:
        st.success("Conversion successful!")
        
        # Preview extracted data
        st.write("### Preview:")
        st.dataframe(extracted_tables[0])

        # Convert to Excel for download
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for idx, df in enumerate(extracted_tables):
                df.to_excel(writer, sheet_name=f"Sheet_{idx+1}", index=False, header=False)
        output.seek(0)

        st.download_button(
            label="📥 Download Excel File",
            data=output,
            file_name="converted_output.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.error("Could not extract any readable content from this PDF.")
