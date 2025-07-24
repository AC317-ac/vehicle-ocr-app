import streamlit as st
import requests
import pandas as pd
import tempfile

OCR_API_KEY = "YOUR_OCR_SPACE_API_KEY"

def ocr_space_file_upload(file):
    url = 'https://api.ocr.space/parse/image'
    response = requests.post(
        url,
        files={'file': file},
        data={'apikey': OCR_API_KEY, 'language': 'eng'},
    )
    result = response.json()
    if result['IsErroredOnProcessing']:
        return None
    return result['ParsedResults'][0]['ParsedText']

def parse_vehicle_data(text):
    import re
    fields = {
        'Registration Mark': r'Registration Mark\s+([A-Z]+\d+)',
        'Make': r'Make\s+([A-Z ]+)',
        'Model': r'Model\s+([A-Z0-9 \(\)\-]+)',
        'Chassis No': r'Chassis No\.?\s+([A-Z0-9]+)',
        'Engine No': r'Engine No\.?\s+([A-Z0-9]+)',
        'Year of Manufacture': r'Year of Manufacture\s+(\d{4})',
        'Owner': r'Full Name of Registered Owner\s+([A-Z ]+)',
    }
    data = {}
    for key, pattern in fields.items():
        match = re.search(pattern, text)
        data[key] = match.group(1).strip() if match else ''
    return data

def export_to_excel(data):
    df = pd.DataFrame([data])
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    df.to_excel(temp.name, index=False)
    return temp.name

st.title("📄 香港車輛登記文件 ➜ Excel")
uploaded_file = st.file_uploader("上傳 JPG / PNG / PDF", type=["jpg", "jpeg", "png", "pdf"])

if uploaded_file:
    with st.spinner("🧠 使用 OCR.space 分析中..."):
        ocr_text = ocr_space_file_upload(uploaded_file)
        if ocr_text:
            st.text_area("📝 OCR 結果", ocr_text, height=300)
            parsed = parse_vehicle_data(ocr_text)
            st.json(parsed)
            xlsx_file = export_to_excel(parsed)
            with open(xlsx_file, "rb") as f:
                st.download_button("📥 下載 Excel", f, file_name="vehicle_data.xlsx")
        else:
            st.error("OCR 處理失敗，請確認圖像清晰")
