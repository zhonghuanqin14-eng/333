import streamlit as st
import pandas as pd

# 页面配置
st.set_page_config(
    page_title="亚马逊物流比价系统",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 自定义CSS - 高级现代化风格
st.markdown("""
<style>
    /* 全局背景 */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%);
    }
    
    /* 主容器 */
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        background: white;
        border-radius: 24px;
        margin-top: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 10px 40px rgba(0,0,0,0.08);
    }
    
    /* 主标题 */
    .main-header {
        font-size: 2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #1a5d8f 0%, #2c8fbb 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    
    /* 子标题 */
    .sub-header {
        font-size: 1.2rem;
        font-weight: 600;
        color: #1a5d8f;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
        padding-bottom: 0.4rem;
        border-bottom: 2px solid #e0e8f0;
    }
    
    /* 折叠框样式 */
    .streamlit-expanderHeader {
        background: linear-gradient(135deg, #f8fafc 0%, #f0f4f8 100%);
        border-radius: 12px;
        font-weight: 600;
        border: 1px solid #e0e8f0;
    }
    .streamlit-expanderContent {
        background-color: #fefefe;
        border-radius: 0 0 12px 12px;
        border: 1px solid #e0e8f0;
        border-top: none;
    }
    
    /* 推荐卡片 */
    .best-channel {
        background: linear-gradient(135deg, #27ae60 0%, #1e8e50 100%);
        color: white;
        padding: 1.2rem;
        border-radius: 20px;
        text-align: center;
        font-size: 1.3rem;
        font-weight: 700;
        margin: 1rem 0;
        box-shadow: 0 8px 20px rgba(39,174,96,0.35);
    }
    
    /* 仓库标题 */
    .warehouse-title {
        font-weight: 700;
        text-align: center;
        margin-bottom: 0.6rem;
        font-size: 0.95rem;
        color: #2c3e50;
        background: linear-gradient(135deg, #eef2f9 0%, #e6ecf5 100%);
        padding: 0.5rem;
        border-radius: 12px;
    }
    
    /* 输入框标签 */
    .input-label {
        font-size: 0.7rem;
        font-weight: 500;
        color: #5a6e8a;
        text-align: center;
        margin-bottom: 0.3rem;
        letter-spacing: 0.5px;
    }
    
    /* 指标卡片 */
    .metric-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        padding: 1rem;
        border-radius: 16px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        text-align: center;
        border: 1px solid #e8edf2;
    }
    
    /* 按钮样式 */
    .stButton > button {
        background: linear-gradient(135deg, #1a5d8f 0%, #0e3d5f 100%);
        color: white;
        border-radius: 40px;
        padding: 0.6rem 2rem;
        font-weight: 600;
        border: none;
        transition: all 0.3s ease;
        width: 100%;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(26,93,143,0.35);
        background: linear-gradient(135deg, #1e6ea8 0%, #124a70 100%);
    }
    
    /* 数字输入框美化 */
    .stNumberInput input {
        border-radius: 12px;
        border: 1px solid #d0dae6;
        transition: all 0.2s;
        background-color: white;
        padding: 0.5rem 0.75rem;
    }
    .stNumberInput input:focus {
        border-color: #1a5d8f;
        box-shadow: 0 0 0 3px rgba(26,93,143,0.15);
        outline: none;
    }
    
    /* 数据表格 */
    .stDataFrame {
        border-radius: 16px;
        overflow: hidden;
        border: 1px solid #e8edf2;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    
    /* 页脚 */
    .footer {
        text-align: center;
        font-size: 0.7rem;
        color: #95a5a6;
        margin-top: 2rem;
        padding-top: 1rem;
        border-top: 1px solid #e8edf2;
    }
    
    /* 分割线 */
    hr {
        margin: 1.2rem 0;
        border-color: #e0e8f0;
    }
    
    /* 指标数值 */
    div[data-testid="stMetricValue"] {
        font-size: 1.8rem;
        font-weight: 700;
        background: linear-gradient(135deg, #1a5d8f 0%, #2c8fbb 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    /* 成功信息框 */
    .stAlert {
        border-radius: 16px;
        border-left-width: 4px;
    }
</style>
""", unsafe_allow_html=True)

# ==================== 固定费率配置 ====================

USD_TO_CNY = 7

# AMP
AMP_CONFIG = {
    "报关费": 260,
    "固定费": 718.8,
    "cbm单价": 1169.69,
    "仓库": "POC系列"
}

# AGL
AGL_WAREHOUSES = [
    {"name": "ONT8", "cbm单价": 597},
    {"name": "LAX9", "cbm单价": 597},
    {"name": "TEB9", "cbm单价": 557.6},
    {"name": "CLT2", "cbm单价": 557.6},
    {"name": "SWF2", "cbm单价": 557.6}
]

AGL_CONFIG = {
    "报关费": 260,
    "固定费": 434.8,
    "warehouses": AGL_WAREHOUSES
}

# send 五仓
SEND5_WAREHOUSES = [
    {"name": "SBD1", "kg单价": 4.2, "cbm单价": 633},
    {"name": "TEB9", "kg单价": 4.8, "cbm单价": 702},
    {"name": "LAX9", "kg单价": 4.2, "cbm单价": 633},
    {"name": "CLT2", "kg单价": 5.2, "cbm单价": 809},
    {"name": "LAS1", "kg单价": 4.7, "cbm单价": 706}
]

SEND5_CONFIG = {
    "报关费": 85,
    "固定费": 0,
    "warehouses": SEND5_WAREHOUSES
}

# send 单点
SEND1_CONFIG = {
    "报关费": 85,
    "固定费": 0,
    "warehouse": {"name": "GEU2", "kg单价": 4.7, "cbm单价": 706}
}

VOLUME_WEIGHT_RATIO = 183

# ==================== 计算函数 ====================

def calculate_amp(cbm):
    return AMP_CONFIG["报关费"] + AMP_CONFIG["固定费"] + cbm * AMP_CONFIG["cbm单价"]

def calculate_agl(cbm_list):
    freight_cbm = 0
    for i, wh in enumerate(AGL_WAREHOUSES):
        freight_cbm += cbm_list[i] * wh["cbm单价"]
    return (AGL_CONFIG["报关费"] * 5) + (AGL_CONFIG["固定费"] * 5) + freight_cbm

def calculate_send_5(cbm_list, weight_list):
    total_freight = 0
    warehouse_details = []
    
    for i, wh in enumerate(SEND5_WAREHOUSES):
        cbm = cbm_list[i]
        weight = weight_list[i]
        
        if cbm == 0 or weight == 0:
            continue
        
        density = weight / cbm
        volume_weight = cbm * VOLUME_WEIGHT_RATIO
        
        if density > VOLUME_WEIGHT_RATIO:
            freight = cbm * wh["cbm单价"]
            warehouse_details.append({
                "仓库": wh["name"],
                "重量(kg)": round(weight, 1),
                "体积重(kg)": round(volume_weight, 1),
                "计费方式": "CBM",
                "单价": wh["cbm单价"],
                "运费": round(freight, 2)
            })
        else:
            chargeable_weight = max(weight, volume_weight)
            freight = chargeable_weight * wh["kg单价"]
            warehouse_details.append({
                "仓库": wh["name"],
                "重量(kg)": round(weight, 1),
                "体积重(kg)": round(volume_weight, 1),
                "计费方式": "kg",
                "单价": wh["kg单价"],
                "运费": round(freight, 2)
            })
        
        total_freight += freight
    
    fixed_fee = SEND5_CONFIG["报关费"] * 5
    total_freight += fixed_fee
    return total_freight, warehouse_details, fixed_fee

def calculate_send_1(cbm, weight, inbound_fee_usd):
    inbound_fee_cny = inbound_fee_usd * USD_TO_CNY
    wh = SEND1_CONFIG["warehouse"]
    density = weight / cbm if cbm > 0 else 0
    volume_weight = cbm * VOLUME_WEIGHT_RATIO
    
    if density > VOLUME_WEIGHT_RATIO:
        freight = cbm * wh["cbm单价"]
        detail = {
            "仓库": wh["name"],
            "重量(kg)": round(weight, 1),
            "体积重(kg)": round(volume_weight, 1),
            "计费方式": "CBM",
            "运费": round(freight, 2)
        }
    else:
        chargeable_weight = max(weight, volume_weight)
        freight = chargeable_weight * wh["kg单价"]
        detail = {
            "仓库": wh["name"],
            "重量(kg)": round(weight, 1),
            "体积重(kg)": round(volume_weight, 1),
            "计费方式": "kg",
            "运费": round(freight, 2)
        }
    
    fixed_fee = SEND1_CONFIG["报关费"]
    total_freight = fixed_fee + freight + inbound_fee_cny
    return total_freight, detail, fixed_fee, inbound_fee_cny

# ==================== 主界面 ====================

st.markdown('<div class="main-header">📦 亚马逊物流比价系统</div>', unsafe_allow_html=True)

# 顶部费率卡片（折叠）
col_rate1, col_rate2, col_rate3 = st.columns(3)

with col_rate1:
    with st.expander("📊 AMP 计费方式", expanded=False):
        st.markdown(f"""
        - **报关费**: ¥{AMP_CONFIG['报关费']:.0f}
        - **固定费**: ¥{AMP_CONFIG['固定费']:.1f}
        - **CBM单价**: ¥{AMP_CONFIG['cbm单价']:.2f}
        - **仓库**: {AMP_CONFIG['仓库']}
        """)

with col_rate2:
    with st.expander("📊 AGL 计费方式", expanded=False):
        st.markdown(f"""
        - **报关费**: ¥{AGL_CONFIG['报关费']:.0f} × 5 = ¥{AGL_CONFIG['报关费']*5:.0f}
        - **固定费**: ¥{AGL_CONFIG['固定费']:.1f} × 5 = ¥{AGL_CONFIG['固定费']*5:.1f}
        - **CBM单价**:
        """)
        for wh in AGL_WAREHOUSES:
            st.markdown(f"  • {wh['name']}: ¥{wh['cbm单价']:.1f}/CBM")

with col_rate3:
    with st.expander("📊 send 计费方式", expanded=False):
        st.markdown(f"""
        - **报关费**: ¥{SEND5_CONFIG['报关费']:.0f} × 仓库数
        - **固定费**: ¥0
        - **体积重系数**: 1 CBM = {VOLUME_WEIGHT_RATIO} kg
        - **计费规则**: 密度 > {VOLUME_WEIGHT_RATIO} → CBM，否则 → kg
        """)
        st.markdown("**五仓单价:**")
        for wh in SEND5_WAREHOUSES:
            st.markdown(f"  • {wh['name']}: kg:¥{wh['kg单价']:.1f} | CBM:¥{wh['cbm单价']:.0f}")
        st.markdown("**单点单价 (GEU2):**")
        st.markdown(f"  • kg:¥{SEND1_CONFIG['warehouse']['kg单价']:.1f} | CBM:¥{SEND1_CONFIG['warehouse']['cbm单价']:.0f}")
        st.markdown(f"  • 额外 + 入库配置费 (USD × {USD_TO_CNY})")

st.markdown("---")

# ==================== AMP 输入 ====================

st.markdown('<div class="sub-header">📦 AMP 单点</div>', unsafe_allow_html=True)

col_left, col_center, col_right = st.columns([1, 2, 1])
with col_center:
    amp_cbm = st.number_input(
        "总CBM",
        min_value=0.0,
        step=None,
        format="%.3f",
        key="amp_input",
        value=0.0
    )

st.markdown("---")

# ==================== AGL 输入 ====================

st.markdown('<div class="sub-header">🏭 AGL 五仓</div>', unsafe_allow_html=True)

agl_cols = st.columns(len(AGL_WAREHOUSES))
agl_cbm_list = []
for i, wh in enumerate(AGL_WAREHOUSES):
    with agl_cols[i]:
        st.markdown(f"<div class='warehouse-title'>{wh['name']}</div>", unsafe_allow_html=True)
        cbm = st.number_input(
            "CBM",
            min_value=0.0,
            step=None,
            format="%.3f",
            key=f"agl_{wh['name']}",
            label_visibility="collapsed",
            value=0.0
        )
        agl_cbm_list.append(cbm)

st.markdown("---")

# ==================== send 五仓输入 ====================

st.markdown('<div class="sub-header">🚚 send 五仓</div>', unsafe_allow_html=True)

send5_cols = st.columns(len(SEND5_WAREHOUSES))
send5_cbm_list = []
send5_weight_list = []
for i, wh in enumerate(SEND5_WAREHOUSES):
    with send5_cols[i]:
        st.markdown(f"<div class='warehouse-title'>{wh['name']}</div>", unsafe_allow_html=True)
        
        st.markdown("<div class='input-label'>CBM (m³)</div>", unsafe_allow_html=True)
        cbm = st.number_input(
            "cbm",
            min_value=0.0,
            step=None,
            format="%.3f",
            key=f"send5_{wh['name']}_cbm",
            label_visibility="collapsed",
            value=0.0
        )
        send5_cbm_list.append(cbm)
        
        st.markdown("<div class='input-label'>重量 (kg)</div>", unsafe_allow_html=True)
        weight = st.number_input(
            "weight",
            min_value=0.0,
            step=None,
            format="%.3f",
            key=f"send5_{wh['name']}_weight",
            label_visibility="collapsed",
            value=0.0
        )
        send5_weight_list.append(weight)

st.markdown("---")

# ==================== send 单点输入 ====================

st.markdown('<div class="sub-header">📍 send 单点</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"<div class='warehouse-title'>GEU2</div>", unsafe_allow_html=True)
    st.markdown("<div class='input-label'>CBM (m³)</div>", unsafe_allow_html=True)
    send1_cbm = st.number_input(
        "cbm",
        min_value=0.0,
        step=None,
        format="%.3f",
        key="send1_cbm",
        label_visibility="collapsed",
        value=0.0
    )

with col2:
    st.markdown(f"<div class='warehouse-title'> </div>", unsafe_allow_html=True)
    st.markdown("<div class='input-label'>重量 (kg)</div>", unsafe_allow_html=True)
    send1_weight = st.number_input(
        "weight",
        min_value=0.0,
        step=None,
        format="%.3f",
        key="send1_weight",
        label_visibility="collapsed",
        value=0.0
    )

with col3:
    st.markdown(f"<div class='warehouse-title'> </div>", unsafe_allow_html=True)
    st.markdown("<div class='input-label'>入库配置费 (USD)</div>", unsafe_allow_html=True)
    send1_inbound_usd = st.number_input(
        "usd",
        min_value=0.0,
        step=None,
        format="%.3f",
        key="send1_inbound",
        label_visibility="collapsed",
        value=0.0
    )
    st.caption(f"≈ ¥{send1_inbound_usd * USD_TO_CNY:.2f}")

st.markdown("---")

# ==================== 比价按钮 ====================

center_col, _, _ = st.columns([1, 2, 1])
with center_col:
    calculate_btn = st.button(
        "🚀 开始比价", 
        type="primary", 
        use_container_width=True
    )

# ==================== 结果展示 ====================

if calculate_btn:
    results = []
    
    # AMP
    if amp_cbm > 0:
        amp_freight = calculate_amp(amp_cbm)
        results.append(("AMP", amp_freight, None, None, None))
    
    # AGL
    if any(c > 0 for c in agl_cbm_list):
        agl_freight = calculate_agl(agl_cbm_list)
        results.append(("AGL", agl_freight, None, None, None))
    
    # send 五仓
    if any(c > 0 for c in send5_cbm_list) or any(w > 0 for w in send5_weight_list):
        send5_freight, send5_details, send5_fixed = calculate_send_5(send5_cbm_list, send5_weight_list)
        if send5_freight > 0:
            results.append(("send五仓", send5_freight, send5_details, send5_fixed, None))
    
    # send 单点
    if send1_cbm > 0 or send1_weight > 0:
        send1_freight, send1_detail, send1_fixed, send1_inbound = calculate_send_1(send1_cbm, send1_weight, send1_inbound_usd)
        if send1_freight > 0:
            results.append(("send单点", send1_freight, None, send1_fixed, (send1_detail, send1_inbound)))
    
    if not results:
        st.warning("请至少输入一个渠道的发货数据")
        st.stop()
    
    best = min(results, key=lambda x: x[1])
    
    st.markdown('<div class="sub-header">📊 比价结果</div>', unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="best-channel">
        🏆 推荐渠道：{best[0]} | 总运费：¥{best[1]:,.2f}
    </div>
    """, unsafe_allow_html=True)
    
    # 对比表格
    compare_data = []
    for name, freight, _, _, _ in results:
        compare_data.append({
            "渠道": name,
            "总运费": f"¥{freight:,.2f}",
            "比最优贵": f"¥{freight - best[1]:,.2f}" if freight > best[1] else "👑 最优"
        })
    st.dataframe(pd.DataFrame(compare_data), use_container_width=True, hide_index=True)
    
    # send五仓明细（简化版）
    for name, freight, details, fixed_fee, _ in results:
        if name == "send五仓" and details:
            st.markdown(f"**📋 {name} 费用明细**")
            
            # 显示固定报关费
            st.metric("固定报关费", f"¥{fixed_fee:.2f}")
            
            # 简化表格：只显示仓库、重量、体积重、计费方式、运费
            df_simple = pd.DataFrame([{
                "仓库": d["仓库"],
                "重量(kg)": d["重量(kg)"],
                "体积重(kg)": d["体积重(kg)"],
                "计费方式": d["计费方式"],
                "运费(元)": d["运费"]
            } for d in details])
            
            st.dataframe(df_simple, use_container_width=True, hide_index=True)
            
            # 总运费
            st.metric("总运费", f"¥{freight:.2f}")
    
    # send单点明细（简化版）
    for name, freight, _, fixed_fee, extra in results:
        if name == "send单点" and extra:
            detail, inbound_fee = extra
            st.markdown(f"**📋 {name} 费用明细**")
            
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("固定报关费", f"¥{fixed_fee:.2f}")
            with col_b:
                st.metric("入库配置费", f"¥{inbound_fee:.2f}")
            with col_c:
                st.metric("总运费", f"¥{freight:.2f}")
            
            # 简化表格
            df_detail = pd.DataFrame([{
                "仓库": detail["仓库"],
                "重量(kg)": detail["重量(kg)"],
                "体积重(kg)": detail["体积重(kg)"],
                "计费方式": detail["计费方式"],
                "运费(元)": detail["运费"]
            }])
            st.dataframe(df_detail, use_container_width=True, hide_index=True)

elif not calculate_btn:
    st.info("👆 请先输入发货数据，然后点击「开始比价」")

st.markdown("---")
st.markdown(f"""
<div class="footer">
    📌 体积重系数: 1 CBM = {VOLUME_WEIGHT_RATIO} kg | 汇率: 1 USD = {USD_TO_CNY} CNY
</div>
""", unsafe_allow_html=True)
