import io
import os
import re
import tempfile

import pandas as pd
from PIL import Image
import pypdfium2 as pdfium
import pytesseract
import streamlit as st

st.title("📄 Advanced PDF to Excel Converter")
st.write("Supports both digital text PDFs and scanned image-based documents using OCR.")

uploaded_file = st.file_uploader("Upload your PDF file", type=["pdf"])

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.read())
        tmp_path = tmp_file.name

    try:
        with st.spinner("Processing document and correcting rotation..."):
            # Convert PDF pages to PIL images using pypdfium2
            pdf_file = pdfium.PdfDocument(tmp_path)
            images = [page.render(scale=3).to_pil() for page in pdf_file]
            pdf_file.close()

            extracted_data = []
            for i, image in enumerate(images):
                # Auto-rotate image if Tesseract detects it's sideways (OSD)
                try:
                    osd = pytesseract.image_to_osd(image)
                    match = re.search(r"Rotate:\s*(\d+)", osd)
                    if match:
                        rotation_angle = int(match.group(1))
                        if rotation_angle != 0:
                            image = image.rotate(-rotation_angle, expand=True)
                except Exception:
                    # Fallback if OSD fails (e.g., too little text on the page)
                    pass

                # Run OCR on the properly oriented image
                text = pytesseract.image_to_string(image)

                # Split text into individual lines for a row-by-row structure
                lines = [line.strip() for line in text.split("\n") if line.strip()]
                for line_idx, line in enumerate(lines):
                    extracted_data.append({
                        "Page": i + 1,
                        "Line Number": line_idx + 1,
                        "Extracted Content": line,
                    })

            df_result = pd.DataFrame(extracted_data)

        if not df_result.empty:
            st.success("Extraction successful!")

            # Preview extracted lines
            st.write("### Preview:")
            st.dataframe(df_result, use_container_width=True)

            # Convert to Excel for download
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df_result.to_excel(writer, sheet_name="Extracted_Text", index=False)
            output.seek(0)

            st.download_button(
                label="📥 Download Clean Excel File",
                data=output,
                file_name="certificate_extracted.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            st.error("Could not extract any readable content from this PDF.")

    finally:
        # Always clean up the temporary file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
