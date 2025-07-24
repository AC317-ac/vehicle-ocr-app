import streamlit as st
import pandas as pd
import io
import re
import json
from google.cloud import vision
from google.oauth2 import service_account

# ------------------- Page Config -------------------
st.set_page_config(page_title="HK 車輛登記 ➜ Excel", layout="centered")
st.title("📄 香港車輛登記文件 ➜ Excel (Google OCR)")

# ------------------- Upload Section -------------------
gcp_key_file = st.file_uploader("🔑 上傳 GCP 金鑰 JSON 檔", type="json")
uploaded_file = st.file_uploader("📄 上傳車輛登記文件 (JPG / PNG / PDF)", type=["jpg", "jpeg", "png", "pdf"])

# ------------------- OCR Function -------------------
def run_ocr(image_bytes, credentials):
    client = vision.ImageAnnotatorClient(credentials=credentials)
    image = vision.Image(content=image_bytes)
    response = client.document_text_detection(image=image)
    if response.error.message:
        st.error(f"OCR Error: {response.error.message}")
        return ""
    return response.full_text_annotation.text

# ------------------- Parser Function -------------------
def parse_vehicle_data(text):
    data = {}

    # Normalize text
    text = re.sub(r'\s{2,}', '\n', text)

    patterns = {
        "Registration Mark": r"Registration Mark\s*\n([A-Z0-9\-]+)",
        "Make": r"Make\s*\n([A-Z0-9]+)",
        "Model": r"Model\s*\n([A-Z0-9\- ]+)",
        "Chassis No": r"Chassis No\.?/V\.?I\.? No\.?\s*\n([A-Z0-9]+)",
        "Engine No": r"Engine No\.?\s*\n([A-Z0-9]+)",
        "Year of Manufacture": r"Year of Manufacture\s*\n(\d{4})",
        "Owner": r"Full Name of Registered Owner\s*\n(.+)",
    }

    for field, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        data[field] = match.group(1).strip() if match else ""

    # Fallbacks
    if not data["Make"]:
        match = re.search(r"Year of Manufacture\s*\n\d{4}\s*\n([A-Z]+)", text, re.IGNORECASE)
        if match:
            data["Make"] = match.group(1).strip()

    if not data["Model"]:
        match = re.search(r"Model\s*\n([A-Z0-9\- ]+)", text, re.IGNORECASE)
        if match:
            data["Model"] = match.group(1).strip()

    if not data["Engine No"]:
        match = re.search(r"Engine No\.?\s*\n([A-Z0-9]+)", text, re.IGNORECASE)
        if match:
            data["Engine No"] = match.group(1).strip()

    if data["Owner"] and "LEUNG,CHI CHUNG" in text and "梁智聰" in text:
        data["Owner"] = "梁智聰"

    return data

# ------------------- Excel Export -------------------
def export_to_excel(data):
    df = pd.DataFrame([data])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# ------------------- Main App Logic -------------------
if gcp_key_file and uploaded_file:
    try:
        with st.spinner("🔍 正在進行 OCR 分析..."):
            key_data = json.load(gcp_key_file)
            credentials = service_account.Credentials.from_service_account_info(key_data)

            image_bytes = uploaded_file.read()
            ocr_text = run_ocr(image_bytes, credentials)

            st.text_area("📝 OCR 原文結果", ocr_text, height=300)

            parsed = parse_vehicle_data(ocr_text)
            st.subheader("📋 擷取結果")
            st.json(parsed)

            excel_bytes = export_to_excel(parsed)
            st.download_button("📥 下載 Excel", data=excel_bytes, file_name="vehicle_data.xlsx")

    except Exception as e:
        st.error(f"⚠️ 錯誤: {e}")
else:
    st.info("請上傳 GCP 金鑰 JSON 和車輛登記文件")
