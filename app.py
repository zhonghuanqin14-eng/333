import streamlit as st
import pandas as pd
from io import BytesIO

# ... (页面配置和CSS样式保持不变) ...

# ==================== 优化后的纽酷输入区域 ====================

# ... (之前的 AMP 和 AGL 输入代码保持不变) ...

# ==================== 纽酷五仓输入（完美对齐版） ====================
st.markdown("#### 🇨 纽酷五仓（5个仓库）")
st.caption("请根据亚马逊实际分配的仓库，输入每个仓库的代码、CBM和总重量")

# 创建表头，确保对齐
header_cols = st.columns([1.5, 1, 1])
with header_cols[0]:
    st.markdown("**仓库代码**")
with header_cols[1]:
    st.markdown("**CBM (m³)**")
with header_cols[2]:
    st.markdown("**总重量 (kg)**")

niuku_warehouse_data = []
for i in range(5):
    # 每一行都使用相同的列宽比例，确保对齐
    cols = st.columns([1.5, 1, 1])
    with cols[0]:
        code = st.text_input(
            "仓库代码", 
            placeholder=f"例: LGB8", 
            key=f"wh_code_{i}",
            label_visibility="collapsed"
        )
    with cols[1]:
        cbm = st.number_input(
            "CBM", 
            min_value=0.0, 
            step=0.1, 
            format="%.2f", 
            key=f"wh_cbm_{i}",
            label_visibility="collapsed"
        )
    with cols[2]:
        weight = st.number_input(
            "重量(kg)", 
            min_value=0.0, 
            step=10.0, 
            key=f"wh_weight_{i}",
            label_visibility="collapsed"
        )
    
    if code:
        niuku_warehouse_data.append({
            "code": code.strip().upper(),
            "cbm": cbm,
            "weight": weight
        })

# ... (纽酷单点输入和其他代码保持不变) ...
