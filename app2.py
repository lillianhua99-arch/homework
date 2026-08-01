import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# 設定頁面標題與佈局
st.set_page_config(page_title="SQLite 購物紀錄小幫手", page_icon="🛒", layout="centered")

DB_NAME = "shopping_records.db"

# --- SQLite 資料庫工具函式 ---
def get_connection():
    """建立 SQLite 資料庫連線"""
    conn = sqlite3.connect(DB_NAME)
    return conn

def init_db():
    """初始化資料庫與資料表"""
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
    """從資料庫載入所有購物紀錄"""
    conn = get_connection()
    df = pd.read_sql_query("SELECT id, time AS 時間, buyer AS 購買人, category AS 購買種類, item_name AS 商品名稱, price AS 單價, quantity AS 數量, subtotal AS 小計 FROM records ORDER BY id DESC", conn)
    conn.close()
    return df

def insert_record(time, buyer, category, item_name, price, quantity, subtotal):
    """新增單筆紀錄"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO records (time, buyer, category, item_name, price, quantity, subtotal)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (time, buyer, category, item_name, price, quantity, subtotal))
    conn.commit()
    conn.close()

def delete_record(record_id):
    """依 ID 刪除單筆紀錄"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM records WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()

def import_records_from_df(df_import):
    """將匯入的 DataFrame 寫入資料庫"""
    conn = get_connection()
    cursor = conn.cursor()
    for _, row in df_import.iterrows():
        cursor.execute("""
            INSERT INTO records (time, buyer, category, item_name, price, quantity, subtotal)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            str(row["時間"]),
            str(row["購買人"]),
            str(row["購買種類"]),
            str(row["商品名稱"]),
            float(row["單價"]),
            int(row["數量"]),
            float(row["小計"])
        ))
    conn.commit()
    conn.close()

# 初始化資料庫
init_db()

# --- UI 介面設定 ---
st.title("🛒 購物紀錄小幫手 (SQLite 版)")
st.caption("支援 SQLite 本地儲存、自動計算金額、單筆刪除與 CSV 匯入/匯出")

# 選項預設值
BUYERS = ["小明", "小華", "媽媽", "爸爸", "公司帳"]
CATEGORIES = ["餐飲飲食", "日常用品", "生鮮食材", "電子數碼", "服飾鞋包", "娛樂休閒", "其他"]

# 頁籤分類：新增紀錄、備份與匯入
tab1, tab2 = st.tabs(["➕ 新增與查看紀錄", "📁 匯入 / 匯出備份"])

# ================= 頁籤 1: 新增與查看紀錄 =================
with tab1:
    st.subheader("新增購買紀錄")
    
    with st.form(key="add_record_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            buyer = st.selectbox("購買人", options=BUYERS)
            item_name = st.text_input("商品名稱", value="日常用品")
            price = st.number_input("單價 (元)", min_value=0.0, step=1.0, format="%.2f")
            
        with col2:
            category = st.selectbox("購買種類", options=CATEGORIES)
            quantity = st.number_input("購買數量", min_value=1, value=1, step=1)
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.text_input("紀錄時間 (自動填寫)", value=current_time, disabled=True)

        submit_button = st.form_submit_button(label="儲存至資料庫", use_container_width=True)

        if submit_button:
            if price <= 0:
                st.warning("⚠️ 請輸入大於 0 的金額！")
            else:
                subtotal = price * quantity
                record_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                insert_record(record_time, buyer, category, item_name, price, quantity, subtotal)
                st.success(f"✅ 已成功寫入資料庫：[{buyer}] 購買 {item_name} (小計: ${subtotal:,.2f})")
                st.rerun()

    st.divider()

    # --- 歷史紀錄與統計 ---
    st.subheader("📋 購買紀錄明細")
    df_records = load_data()

    if not df_records.empty:
        # 數據指標卡片
        total_amount = df_records["小計"].sum()
        total_items = df_records["數量"].sum()

        col_stat1, col_stat2, col_stat3 = st.columns(3)
        col_stat1.metric(label="累計總金額", value=f"${total_amount:,.2f}")
        col_stat2.metric(label="購買總件數", value=f"{int(total_items)} 件")
        col_stat3.metric(label="總紀錄筆數", value=f"{len(df_records)} 筆")

        st.write("")

        # 顯示歷史紀錄表格
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

        # --- 刪除紀錄 ---
        with st.expander("🗑️ 刪除指定紀錄"):
            options_to_delete = {
                f"ID {row['id']}: [{row['時間']}] {row['購買人']} - {row['商品名稱']} (${row['小計']})": row['id']
                for _, row in df_records.iterrows()
            }
            
            selected_option = st.selectbox("選擇欲刪除的紀錄：", options=list(options_to_delete.keys()))
            
            if st.button("確認刪除該筆資料", type="primary"):
                target_id = options_to_delete[selected_option]
                delete_record(target_id)
                st.success("✅ 紀錄已成功從 SQLite 資料庫中刪除！")
                st.rerun()

    else:
        st.info("💡 目前資料庫中無任何購物紀錄。")

# ================= 頁籤 2: 匯入 / 匯出備份 =================
with tab2:
    st.subheader("📤 匯出資料庫紀錄 (CSV)")
    df_records = load_data()
    
    if not df_records.empty:
        # 排除 ID 後匯出
        df_export = df_records.drop(columns=["id"])
        csv_data = df_export.to_csv(index=False).encode('utf-8-sig')
        
        st.download_button(
            label="📥 下載全量 CSV 備份檔",
            data=csv_data,
            file_name=f"shopping_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.caption("無資料可供匯出。")

    st.divider()

    st.subheader("📥 匯入歷史紀錄 (CSV)")
    st.caption("上傳的 CSV 檔案需包含以下 7 個欄位：`時間`, `購買人`, `購買種類`, `商品名稱`, `單價`, `數量`, `小計`")
    
    uploaded_file = st.file_uploader("選擇 CSV 檔案進行匯入", type=["csv"])
    
    if uploaded_file is not None:
        try:
            df_import = pd.read_csv(uploaded_file)
            required_columns = {"時間", "購買人", "購買種類", "商品名稱", "單價", "數量", "小計"}
            
            if required_columns.issubset(df_import.columns):
                st.write("預覽即將匯入的資料：")
                st.dataframe(df_import.head(5), use_container_width=True)
                
                if st.button("確認將以上資料匯入 SQLite 資料庫", type="primary"):
                    import_records_from_df(df_import)
                    st.success(f"🎉 成功匯入 {len(df_import)} 筆歷史紀錄！")
                    st.rerun()
            else:
                st.error(f"❌ 檔案欄位不符合格式需求，缺少以下欄位：{required_columns - set(df_import.columns)}")
        except Exception as e:
            st.error(f"⚠️ 解析 CSV 檔案失敗：{e}")
