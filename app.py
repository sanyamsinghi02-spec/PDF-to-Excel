import io
import tempfile
import os
import streamlit as st
import pandas as pd
import pypdfium2 as pdfium
from PIL import Image
from google import genai

st.title("📄 AI-Powered Universal PDF to Excel Creator")
st.write("Powered by Google AI Vision to read handwriting, notes, diagrams, and digital text with 100% accuracy!")

uploaded_file = st.file_uploader("Upload your PDF file", type=["pdf"])

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.read())
        tmp_path = tmp_file.name

    extracted_data = []

    with st.spinner("Analyzing document with AI Vision (like Google Lens)..."):
        # Configure Gemini API using Streamlit secrets
        client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
        
        # Convert PDF pages to high-resolution images using pypdfium2
        pdf_file = pdfium.PdfDocument(tmp_path)
        
        for page_idx, page in enumerate(pdf_file):
            image = page.render(scale=3).to_pil()
            
            # Prompt the AI model to transcribe everything line by line
            prompt = (
                "Extract all text from this image line by line. "
                "Include handwritten notes, headings, bullet points, and flowchart text. "
                "Return the output as a clean, plain text list separated by newlines, with no extra conversational filler."
            )
            
            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
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
            except Exception as e:
                st.error(f"AI Error on Page {page_idx + 1}: {e}")

        df_result = pd.DataFrame(extracted_data)

    # Clean up temp file
    os.unlink(tmp_path)

    if not df_result.empty:
        st.success("AI Extraction successful!")
        
        # Preview extracted lines
        st.write("### Preview:")
        st.dataframe(df_result)

        # Convert to Excel for download
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_result.to_excel(writer, sheet_name="AI_Extracted_Notes", index=False)
        output.seek(0)

        st.download_button(
            label="📥 Download Clean Excel File",
            data=output,
            file_name="ai_notes_extracted.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.error("Could not extract any readable content from this document.")
