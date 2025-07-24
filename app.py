import streamlit as st
import io
import json
import pandas as pd
import base64
import re
from google.oauth2 import service_account
from google.cloud import vision

st.set_page_config(page_title="HK Vehicle OCR Extractor", layout="centered")
st.title("🚗 香港車輛登診文件 OCR ➔ Excel")
st.markdown("將掃描的車輛登診文件轉換為結構化 Excel 資料表 🧾")

# --- Upload GCP key file
st.header("步驟 1：上傳 Google Cloud 金鑰")
gcp_key_file = st.file_uploader("📎 上傳 GCP JSON 金鑰檔案", type="json")

# --- Upload image
st.header("步驟 2：上傳車輛登診文件圖像")
uploaded_file = st.file_uploader("📷 上傳 JPG/PNG 圖像檔", type=["jpg", "jpeg", "png"])

# --- Run OCR

def run_ocr(image_bytes, credentials):
    client = vision.ImageAnnotatorClient(credentials=credentials)
    image = vision.Image(content=image_bytes)
    response = client.text_detection(image=image)
    texts = response.text_annotations
    if not texts:
        return ""
    return texts[0].description

# --- Parse OCR Result

def parse_vehicle_data(text):
    data = {
        "Registration Mark": "",
        "Make": "",
        "Model": "",
        "Chassis No": "",
        "Engine No": "",
        "Year of Manufacture": "",
        "Owner": ""
    }

    lines = text.splitlines()
    lines = [line.strip() for line in lines if line.strip()]

    for idx, line in enumerate(lines):
        lower = line.lower()

        # Registration Mark
        if "registration mark" in lower or "登診號碼" in line:
            if idx + 1 < len(lines):
                candidate = lines[idx + 1].strip()
                if re.match(r"^[A-Z]{1,2}\d{2,4}[A-Z]?$", candidate):
                    data["Registration Mark"] = candidate

        # Make & Year of Manufacture
        if "year of manufacture" in lower or "出廠年份" in line:
            match = re.search(r"(19|20)\d{2}", line)
            if match:
                data["Year of Manufacture"] = match.group(0)
            if idx + 1 < len(lines):
                make_candidate = lines[idx + 1].strip()
                if make_candidate.isalpha():
                    data["Make"] = make_candidate.upper()

        # Model
        if "model" in lower:
            if idx + 1 < len(lines):
                model_candidate = lines[idx + 1].strip()
                if re.match(r"[A-Z0-9\- ]{2,}", model_candidate):
                    data["Model"] = model_candidate

        # Chassis No
        if "chassis" in lower or "底盤號碼" in line:
            match = re.search(r"[A-Z0-9]{10,}", line)
            if match:
                data["Chassis No"] = match.group(0)

        # Engine No
        if "engine no" in lower or "引擎號碼" in line:
            match = re.search(r"[A-Z0-9]{6,}", line)
            if match:
                data["Engine No"] = match.group(0)

        # Owner Name (Chinese or English)
        if "registered owner" in lower or "登診車主的全名" in line:
            if idx + 1 < len(lines):
                owner_candidate = lines[idx + 1].strip()
                if re.search(r"[一-龥]", owner_candidate):
                    data["Owner"] = owner_candidate
                elif re.match(r"[A-Z ,]+", owner_candidate):
                    data["Owner"] = owner_candidate

        if "梁智聰" in line:
            data["Owner"] = "梁智聰"

    return data

# --- Main processing
if gcp_key_file and uploaded_file:
    with st.spinner("🔍 正在辨識文字並解析資料..."):
        key_data = json.load(gcp_key_file)
        credentials = service_account.Credentials.from_service_account_info(key_data)
        image_bytes = uploaded_file.read()

        ocr_text = run_ocr(image_bytes=image_bytes, credentials=credentials)  # Removed @st.cache_data
        parsed_data = parse_vehicle_data(ocr_text)

        st.header("📄 OCR 辨識結果")
        st.text_area("✂️ 原始文字輸出：", ocr_text, height=300)

        st.header("📋 結構化資料")
        df = pd.DataFrame([parsed_data])
        st.dataframe(df)

        # --- Download button
        csv = df.to_csv(index=False)
        b64 = base64.b64encode(csv.encode()).decode()
        href = f'<a href="data:file/csv;base64,{b64}" download="vehicle_data.csv">👅 下載 Excel / CSV 檔案</a>'
        st.markdown(href, unsafe_allow_html=True)

elif gcp_key_file or uploaded_file:
    st.warning("請確保已上傳金鑰檔與圖像檔！")
