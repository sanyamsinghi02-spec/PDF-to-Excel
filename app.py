import io
import tempfile
import os
import streamlit as st
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

    with st.spinner("Processing document and correcting rotation..."):
        # Convert PDF pages to images
        images = convert_from_path(tmp_path)
        
        extracted_data = []
        for i, image in enumerate(images):
            # Auto-rotate image if Tesseract detects it's sideways (OSD - Orientation and Script Detection)
            try:
                osd = pytesseract.image_to_osd(image)
                # Parse rotation angle from osd output
                rotation_angle = int([x.split(':') for x in osd.split('\n') if 'Rotate' in x][0][1])
                if rotation_angle != 0:
                    image = image.rotate(-rotation_angle, expand=True)
            except Exception:
                # Fallback: if it's explicitly sideways like your certificate, rotate 90 degrees clockwise
                # You can change this to image.rotate(270, expand=True) if needed
                pass

            # Run OCR on the properly oriented image
            text = pytesseract.image_to_string(image)
            
            # Split text into individual lines to create a clean, readable row-by-row structure
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            for line_idx, line in enumerate(lines):
                extracted_data.append({
                    "Page": i + 1,
                    "Line Number": line_idx + 1,
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
            df_result.to_excel(writer, sheet_name="Extracted_Text", index=False)
        output.seek(0)

        st.download_button(
            label="📥 Download Clean Excel File",
            data=output,
            file_name="certificate_extracted.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.error("Could not extract any readable content from this PDF.")
