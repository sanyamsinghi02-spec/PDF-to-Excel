import io
import tempfile
import os
import time
import itertools
import streamlit as st
import pandas as pd
import pdfplumber
import pypdfium2 as pdfium
from PIL import Image
from google import genai

st.title("📄 Universal PDF to Excel Creator")
st.write("Instant digital extraction + AI Vision for handwritten notes and diagrams!")

# --- 1. Multi-Key Rotation Setup ---
api_keys = []
for key_name in ["GEMINI_API_KEY_1", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3"]:
    if key_name in st.secrets:
        api_keys.append(st.secrets[key_name])

if not api_keys and "GEMINI_API_KEY" in st.secrets:
    api_keys.append(st.secrets["GEMINI_API_KEY"])

if not api_keys:
    st.error("⚠️ No Gemini API keys found! Please add your API key(s) in Streamlit Secrets.")
    st.stop()

key_pool = itertools.cycle(api_keys)

# --- 2. Active Model Fallback Chain ---
MODELS_TO_TRY = ['gemini-3.8-flash', 'gemini-3.5-flash-lite']

uploaded_file = st.file_uploader("Upload your PDF file", type=["pdf"])

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.read())
        tmp_path = tmp_file.name

    extracted_data = []

    with st.spinner("Processing document..."):
        # STEP A: Fast digital text extraction
        has_digital_text = False
        with pdfplumber.open(tmp_path) as pdf:
            for page_idx, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text and text.strip():
                    has_digital_text = True
                    lines = [line.strip() for line in text.split('\n') if line.strip()]
                    for line_idx, line in enumerate(lines):
                        extracted_data.append({
                            "Page": page_idx + 1,
                            "Line Number": line_idx + 1,
                            "Extracted Content": line
                        })

        # STEP B: Fallback to AI Vision for scans/handwriting
        if not has_digital_text:
            pdf_file = pdfium.PdfDocument(tmp_path)
            
            for page_idx, page in enumerate(pdf_file):
                image = page.render(scale=2).to_pil()
                image.thumbnail((1000, 1000))
                
                prompt = (
                    "Extract all text from this image line by line. "
                    "Include handwritten notes, headings, bullet points, and flowchart text. "
                    "Return the output as a clean, plain text list separated by newlines, with no extra conversational filler."
                )
                
                page_success = False
                last_error = None
                
                for model_name in MODELS_TO_TRY:
                    if page_success:
                        break
                        
                    current_key = next(key_pool)
                    client = genai.Client(api_key=current_key)
                    
                    for attempt in range(2):
                        try:
                            response = client.models.generate_content(
                                model=model_name,
                                contents=[image, prompt]
                            )
                            text = response.text
                            lines = [line.strip() for line in text.split('\n') if line.strip()]
                            
                            for line_idx, line in enumerate(lines):
                                extracted_data.append({
                                    "Page": page_idx + 1,
                                    "Line Number": line_idx + 1,
                                    "Extracted Content": line
                                })
                            page_success = True
                            break
                        except Exception as e:
                            last_error = str(e)
                            time.sleep(1)
                            continue
                
                if not page_success:
                    st.warning(f"⚠️ Page {page_idx + 1} processing warning: {last_error}")

        df_result = pd.DataFrame(extracted_data)

    # Clean up temp file
    os.unlink(tmp_path)

    if not df_result.empty:
        st.success("Extraction successful!")
        
        st.write("### Preview:")
        st.dataframe(df_result)

        # Convert to Excel for download
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_result.to_excel(writer, sheet_name="Extracted_Notes", index=False)
        output.seek(0)

        st.download_button(
            label="📥 Download Clean Excel File",
            data=output,
            file_name="extracted_document.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.error("Could not extract any readable content from this document.")
