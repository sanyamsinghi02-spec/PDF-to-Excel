import streamlit as st
import pdfplumber
import pandas as pd
import io

# App Title & Description
st.title("📄 PDF to Excel Converter")
st.write("Upload a text-based PDF to convert its tables and layout into an Excel spreadsheet seamlessly without breaking characters.")

# File Uploader widget
uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

if uploaded_file is not None:
    st.info("Processing your PDF... Please wait.")
    
    all_tables = []
    
    # Read the uploaded PDF file in memory
    with pdfplumber.open(uploaded_file) as pdf:
        for page_index, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            if tables:
                for table in tables:
                    df = pd.DataFrame(table)
                    all_tables.append((f"Page_{page_index+1}_Table", df))
            else:
                text = page.extract_text(layout=True)
                if text:
                    lines = [line.split() for line in text.split('\n') if line.strip()]
                    if lines:
                        df = pd.DataFrame(lines)
                        all_tables.append((f"Page_{page_index+1}_Text", df))

    if all_tables:
        # Generate Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for sheet_name, df in all_tables:
                safe_sheet_name = sheet_name[:31]  # Excel sheet limit
                df.to_excel(writer, sheet_name=safe_sheet_name, index=False, header=False)
        output.seek(0)
        
        st.success("Conversion complete!")
        
        # Download button
        st.download_button(
            label="📥 Download Excel File",
            data=output,
            file_name="converted_output.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("No readable text or tables found. The PDF might be a scanned image.")