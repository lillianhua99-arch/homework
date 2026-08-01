import streamlit as st
import pandas as pd
import sqlite3
import pytesseract
from PIL import Image
import cv2
import numpy as np
import re
from datetime import datetime

# ==========================================
# Windows 使用者若未設定 PATH，請將下行註解打開發並填入實際安裝路徑：
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# ==========================================

# 設定頁面標題與佈局
st.set_page_config(page_title="發票拍照辨識購物紀錄", page_icon="🧾", layout="centered")

DB_NAME = "shopping_records.db"

# --- SQLite 資料庫工具函式 ---
def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time TEXT NOT NULL,
            buyer TEXT NOT NULL,
            category TEXT NOT NULL,
            item_name TEXT NOT NULL,
            price REAL NOT NULL,
            quantity INTEGER NOT NULL,
            subtotal REAL NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def load_data():
    conn = get_connection()
    df = pd.read_sql_query("SELECT id, time AS 時間, buyer AS 購買人, category AS 購買種類, item_name AS 商品名稱, price AS 單價, quantity AS 數量, subtotal AS 小計 FROM records ORDER BY id DESC", conn)
    conn.close()
    return df

def insert_record(time, buyer, category, item_name, price, quantity, subtotal):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO records (time, buyer, category, item_name, price, quantity, subtotal)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (time, buyer, category, item_name, price, quantity, subtotal))
    conn.commit()
    conn.close()

def delete_record(record_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM records WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()

# --- 發票影像處理與 OCR 辨識邏輯 ---
def preprocess_image(image):
    """影像灰階化與二值化，提高 OCR 辨識率"""
    img_np = np.array(image.convert("RGB"))
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    # 對比度增強與二值化
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return Image.fromarray(thresh)

def parse_invoice_text(text):
    """利用正則表達式自動解析發票文字內容"""
    # 1. 辨識統一發票號碼 (兩個大寫英文 + 8位數字)
    invoice_num_match = re.search(r'[A-Z]{2}[-\s]?\d{8}', text)
    invoice_num = invoice_num_match.group(0).replace(" ", "") if invoice_num_match else "未辨識出號碼"

    # 2. 尋找金額 (尋找包含數字且非發票號碼的樣式，找最大金額作為單價/總價猜測)
    amounts = re.findall(r'\b\d+(?:\.\d{1,2})?\b', text)
    valid_amounts = [float(a) for a in amounts if len(a) <= 6] # 排除發票號碼等長數字
    
    extracted_price = max(valid_amounts) if valid_amounts else 0.0

    # 3. 尋找數量 (預設 1)
    extracted_qty = 1
    
    return invoice_num, extracted_price, extracted_qty

# 初始化資料庫
init_db()

# --- 介面佈局 ---
st.title("🧾 購物紀錄小幫手 (拍照辨識版)")
st.caption("支援本地 Tesseract OCR 發票辨識、拍照輸入與 SQLite 儲存")

BUYERS = ["小明", "小華", "媽媽", "爸爸", "公司帳"]
CATEGORIES = ["餐飲飲食", "日常用品", "生鮮食材", "電子數碼", "服飾鞋包", "娛樂休閒", "其他"]

tab1, tab2 = st.tabs(["📸 拍照/手動新增紀錄", "📋 歷史明細與維護"])

# ================= 頁籤 1: 拍照與新增紀錄 =================
with tab1:
    st.subheader("1. 📸 拍照辨識統一發票")
    camera_photo = st.camera_input("將發票對準鏡頭拍照：")

    # 預設辨識結果變數
    detected_num = ""
    detected_price = 0.0
    detected_qty = 1

    if camera_photo is not None:
        image = Image.open(camera_photo)
        
        with st.spinner("正在執行本地 OCR 辨識中..."):
            # 進行影像預處理
            processed_img = preprocess_image(image)
            
            # 使用 Tesseract 進行中英文辨識
            try:
                raw_text = pytesseract.image_to_string(processed_img, lang="chi_tra+eng")
                detected_num, detected_price, detected_qty = parse_invoice_text(raw_text)
                st.success("✅ 發票辨識完成！請確認或修改下方帶入的欄位。")
                
                with st.expander("🔍 檢視 OCR 提取的原始文字"):
                    st.text(raw_text if raw_text.strip() else "未檢測到文字，請調整光線或距離重試。")
            except Exception as e:
                st.error(f"⚠️ OCR 辨識失敗，請確認是否已安裝 Tesseract 繁體中文包 (`chi_tra`)。\n錯誤訊息：{e}")

    st.divider()
    st.subheader("2. 📝 確認與填寫資料")

    with st.form(key="add_record_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            buyer = st.selectbox("購買人", options=BUYERS)
            item_name = st.text_input("商品名稱 / 發票號碼", value=detected_num if detected_num else "日常用品")
            price = st.number_input("單價 (元)", min_value=0.0, value=float(detected_price), step=1.0, format="%.2f")
            
        with col2:
            category = st.selectbox("購買種類", options=CATEGORIES)
            quantity = st.number_input("購買數量", min_value=1, value=int(detected_qty), step=1)
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.text_input("紀錄時間 (自動填寫)", value=current_time, disabled=True)

        submit_button = st.form_submit_button(label="💾 儲存至紀錄庫", use_container_width=True)

        if submit_button:
            if price <= 0:
                st.warning("⚠️ 請輸入大於 0 的金額！")
            else:
                subtotal = price * quantity
                record_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                insert_record(record_time, buyer, category, item_name, price, quantity, subtotal)
                st.success(f"🎉 已成功儲存：[{buyer}] {item_name} (總價: ${subtotal:,.2f})")
                st.rerun()

# ================= 頁籤 2: 歷史紀錄與管理 =================
with tab2:
    st.subheader("📋 歷史購買紀錄")
    df_records = load_data()

    if not df_records.empty:
        total_amount = df_records["小計"].sum()
        total_items = df_records["數量"].sum()

        col_stat1, col_stat2, col_stat3 = st.columns(3)
        col_stat1.metric(label="累計總金額", value=f"${total_amount:,.2f}")
        col_stat2.metric(label="購買總件數", value=f"{int(total_items)} 件")
        col_stat3.metric(label="總紀錄筆數", value=f"{len(df_records)} 筆")

        st.write("")

        st.dataframe(
            df_records,
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": st.column_config.NumberColumn("ID", width="small"),
                "單價": st.column_config.NumberColumn(format="$%.2f"),
                "小計": st.column_config.NumberColumn(format="$%.2f"),
            }
        )

        # 刪除功能
        with st.expander("🗑️ 刪除指定紀錄"):
            options_to_delete = {
                f"ID {row['id']}: [{row['時間']}] {row['購買人']} - {row['商品名稱']} (${row['小計']})": row['id']
                for _, row in df_records.iterrows()
            }
            selected_option = st.selectbox("選擇欲刪除的紀錄：", options=list(options_to_delete.keys()))
            
            if st.button("確認刪除該筆資料", type="primary"):
                delete_record(options_to_delete[selected_option])
                st.success("✅ 紀錄已成功刪除！")
                st.rerun()
    else:
        st.info("💡 目前資料庫中無任何購物紀錄。")
