import streamlit as st
import pandas as pd
from datetime import datetime

# 設定頁面標題與佈局
st.set_page_config(page_title="購物紀錄小幫手", page_icon="🛒", layout="centered")

st.title("🛒 購物紀錄小幫手")
st.caption("輸入金額與數量，系統自動記錄日期與時間並計算總價")

# 初始化 session_state 用於儲存購物紀錄
if "shopping_list" not in st.session_state:
    st.session_state.shopping_list = []

# --- 新增紀錄區塊 ---
st.subheader("➕ 新增購買紀錄")

with st.form(key="add_item_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    
    with col1:
        item_name = st.text_input("商品名稱", value="日常用品")
        price = st.number_input("單價 (元)", min_value=0.0, step=1.0, format="%.2f")
        
    with col2:
        quantity = st.number_input("購買數量", min_value=1, value=1, step=1)
        # 自動抓取當前日期與時間
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.text_input("紀錄時間 (自動填寫)", value=current_time, disabled=True)

    submit_button = st.form_submit_button(label="新增至購物紀錄", use_container_width=True)

    if submit_button:
        if price <= 0:
            st.warning("⚠️ 請輸入大於 0 的金額！")
        else:
            subtotal = price * quantity
            # 建立單筆紀錄資料
            record = {
                "購買時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "商品名稱": item_name,
                "單價": price,
                "數量": quantity,
                "小計": subtotal
            }
            st.session_state.shopping_list.append(record)
            st.success(f"✅ 已成功加入：{item_name} (小計: ${subtotal:,.2f})")

st.divider()

# --- 紀錄展示與統計區塊 ---
st.subheader("📋 購買紀錄明細")

if st.session_state.shopping_list:
    # 轉為 DataFrame 方便顯示與處理
    df = pd.DataFrame(st.session_state.shopping_list)
    
    # 計算總價與總數量
    total_amount = df["小計"].sum()
    total_items = df["數量"].sum()

    # 數據指標卡片
    col_stat1, col_stat2, col_stat3 = st.columns(3)
    col_stat1.metric(label="累計消費總額", value=f"${total_amount:,.2f}")
    col_stat2.metric(label="購買總件數", value=f"{total_items} 件")
    col_stat3.metric(label="紀錄筆數", value=f"{len(df)} 筆")

    st.write("")
    
    # 顯示歷史紀錄表格 (自動排版)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "單價": st.column_config.NumberColumn(format="$%.2f"),
            "小計": st.column_config.NumberColumn(format="$%.2f"),
        }
    )

    # 底部操作按鈕：匯出 CSV & 清除紀錄
    col_btn1, col_btn2 = st.columns([1, 1])
    
    with col_btn1:
        # 下載 CSV 功能
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 匯出 CSV 檔案",
            data=csv,
            file_name=f"shopping_records_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
        
    with col_btn2:
        if st.button("🗑️ 清空所有紀錄", use_container_width=True):
            st.session_state.shopping_list = []
            st.rerun()

else:
    st.info("💡 目前尚無購買紀錄，請在上方輸入金額並新增。")
