
import streamlit as st
import google.generativeai as genai
import PyPDF2 as pdf
import pandas as pd
import tempfile
import openpyxl
from openpyxl.utils import get_column_letter
from PIL import Image
import easyocr
import numpy as np  # Make sure to import numpy

# Configure API key
genai.configure(api_key="AIzaSyDm0pOQKmzLMPU9omEOIr8nsFdGld9cuG8")

# Initialize the OCR reader
reader = easyocr.Reader(['en'])

# Function to get response from Generative AI model
def get_gemini_response(input):
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content(input)
    return response

# Convert PDF to text
def input_pdf_text(uploaded_file):
    reader_pdf = pdf.PdfReader(uploaded_file)
    text = ""
    for page in range(len(reader_pdf.pages)):
        page = reader_pdf.pages[page]
        text += str(page.extract_text())
    return text

# Extract text from images using EasyOCR
def input_image_text(uploaded_file):
    # Open the image using PIL
    image = Image.open(uploaded_file)
    # Convert the image to a NumPy array
    image_np = np.array(image)
    # Perform OCR on the image
    text = reader.readtext(image_np, detail=0)  # Extract text as a list of strings
    return ' '.join(text)  # Join the extracted text into a single string

# Extract information based on each criterion
def extract_information_per_criterion(text, criteria_list):
    extracted_data = {}
    for criterion in criteria_list:
        prompt = f"Please analyze the following text and extract the key points related to '{criterion}'. Provide the output as a simple string without any extra formatting or labels. Here’s the text:\n{text}"
        response = get_gemini_response(prompt)
        extracted_text = response.candidates[0].content.parts[0].text.strip().replace('*', '')  # Remove asterisks
        extracted_data[criterion] = extracted_text
    return extracted_data



# Store extracted information into a DataFrame
def information_to_df(extracted_data, sr_no):
    data = {criterion: [extracted_data.get(criterion, "")] for criterion in extracted_data}
    df = pd.DataFrame(data)
    df.insert(0, "Sr. No", sr_no)
    return df

# Adjust Excel columns to fit content
def adjust_excel_columns(writer, df):
    worksheet = writer.sheets['Sheet1']
    for idx, col in enumerate(df.columns, 1):  # 1-indexed.
        max_length = max(df[col].astype(str).map(len).max(), len(col))
        worksheet.column_dimensions[get_column_letter(idx)].width = max_length + 2

# Streamlit App
st.title("File Information Extractor")
st.text("Upload PDFs, JPGs, or PNGs and specify criteria for information extraction")

uploaded_files = st.file_uploader("Upload your files (PDF, JPG, PNG)", type=["pdf", "jpg", "png"], accept_multiple_files=True)

if uploaded_files:
    user_input = st.text_area("Enter the criteria for extracting information, separated by commas.")

    if user_input:
        criteria_list = [criterion.strip() for criterion in user_input.split(',')]  # Split and clean criteria
        all_dfs = []

        for i, uploaded_file in enumerate(uploaded_files, start=1):
            # Determine file type and handle accordingly
            if uploaded_file.type == "application/pdf":
                text = input_pdf_text(uploaded_file)
                extracted_data = extract_information_per_criterion(text, criteria_list)

                st.subheader(f"Extracted Information from PDF File {i}")
                st.write(extracted_data)

                df = information_to_df(extracted_data, i)
                all_dfs.append(df)

            elif uploaded_file.type in ["image/jpeg", "image/png"]:
                text = input_image_text(uploaded_file)  # Extract text from image using OCR
                extracted_data = extract_information_per_criterion(text, criteria_list)

                st.subheader(f"Extracted Information from Image File {i}")
                st.write(extracted_data)

                df = information_to_df(extracted_data, i)
                all_dfs.append(df)

        # Combine all DataFrames into one
        combined_df = pd.concat(all_dfs, ignore_index=True)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_file:
            with pd.ExcelWriter(tmp_file.name, engine='openpyxl') as writer:
                combined_df.to_excel(writer, index=False)
                adjust_excel_columns(writer, combined_df)

            excel_path = tmp_file.name

        with open(excel_path, "rb") as file:
            st.download_button(
                label="Download Extracted Information as Excel",
                data=file,
                file_name="extracted_information.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
