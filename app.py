import streamlit as st
import pandas as pd

# 页面配置
st.set_page_config(
    page_title="亚马逊物流比价系统",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 自定义CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        font-weight: bold;
        color: #2c3e50;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
        padding-bottom: 0.3rem;
        border-bottom: 2px solid #1f77b4;
    }
    .best-channel {
        background-color: #27ae60;
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        font-size: 1.2rem;
        font-weight: bold;
    }
    .warehouse-table {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin-top: 0.5rem;
    }
    .metric-card {
        background-color: white;
        padding: 0.8rem;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        text-align: center;
    }
    /* 输入框样式 */
    .stNumberInput > div {
        width: 100%;
    }
    .input-label {
        font-size: 0.75rem;
        color: #666;
        text-align: center;
        margin-bottom: 0.2rem;
    }
    .warehouse-title {
        font-weight: bold;
        text-align: center;
        margin-bottom: 0.5rem;
        font-size: 0.9rem;
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
                "CBM": cbm,
                "重量(kg)": weight,
                "密度": round(density, 1),
                "计费方式": "CBM",
                "单价": wh["cbm单价"],
                "运费": round(freight, 2)
            })
        else:
            chargeable_weight = max(weight, volume_weight)
            freight = chargeable_weight * wh["kg单价"]
            warehouse_details.append({
                "仓库": wh["name"],
                "CBM": cbm,
                "重量(kg)": weight,
                "体积重(kg)": round(volume_weight, 1),
                "计费重量(kg)": round(chargeable_weight, 1),
                "密度": round(density, 1),
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
            "CBM": cbm,
            "重量(kg)": weight,
            "密度": round(density, 1),
            "计费方式": "CBM",
            "单价": wh["cbm单价"],
            "运费": round(freight, 2)
        }
    else:
        chargeable_weight = max(weight, volume_weight)
        freight = chargeable_weight * wh["kg单价"]
        detail = {
            "仓库": wh["name"],
            "CBM": cbm,
            "重量(kg)": weight,
            "体积重(kg)": round(volume_weight, 1),
            "计费重量(kg)": round(chargeable_weight, 1),
            "密度": round(density, 1),
            "计费方式": "kg",
            "单价": wh["kg单价"],
            "运费": round(freight, 2)
        }
    
    fixed_fee = SEND1_CONFIG["报关费"]
    total_freight = fixed_fee + freight + inbound_fee_cny
    return total_freight, detail, fixed_fee, inbound_fee_cny

# ==================== 顶部费率卡片（折叠） ====================

st.markdown('<div class="main-header">亚马逊物流比价系统</div>', unsafe_allow_html=True)

# 三列折叠框
col_rate1, col_rate2, col_rate3 = st.columns(3)

with col_rate1:
    with st.expander("📊 AMP 计费方式", expanded=False):
        st.markdown(f"""
        - 报关费: ¥{AMP_CONFIG['报关费']:.0f}
        - 固定费: ¥{AMP_CONFIG['固定费']:.1f}
        - CBM单价: ¥{AMP_CONFIG['cbm单价']:.2f}
        - 仓库: {AMP_CONFIG['仓库']}
        """)

with col_rate2:
    with st.expander("📊 AGL 计费方式", expanded=False):
        st.markdown(f"""
        - 报关费: ¥{AGL_CONFIG['报关费']:.0f} × 5 = ¥{AGL_CONFIG['报关费']*5:.0f}
        - 固定费: ¥{AGL_CONFIG['固定费']:.1f} × 5 = ¥{AGL_CONFIG['固定费']*5:.1f}
        - CBM单价:
        """)
        for wh in AGL_WAREHOUSES:
            st.markdown(f"  • {wh['name']}: ¥{wh['cbm单价']:.1f}")

with col_rate3:
    with st.expander("📊 send 计费方式", expanded=False):
        st.markdown(f"""
        - 报关费: ¥{SEND5_CONFIG['报关费']:.0f} × 仓库数
        - 固定费: ¥0
        - 体积重系数: 1 CBM = {VOLUME_WEIGHT_RATIO} kg
        - 计费规则: 密度 > {VOLUME_WEIGHT_RATIO} → CBM，否则 → kg
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
        step=0.5,
        format="%.2f",
        key="amp_input"
    )

st.markdown("---")

# ==================== AGL 输入 ====================

st.markdown('<div class="sub-header">🏭 AGL 五仓</div>', unsafe_allow_html=True)

# 使用网格布局：5列，每列仓库名在上，输入框在下
agl_cols = st.columns(len(AGL_WAREHOUSES))
agl_cbm_list = []
for i, wh in enumerate(AGL_WAREHOUSES):
    with agl_cols[i]:
        st.markdown(f"<div class='warehouse-title'>{wh['name']}</div>", unsafe_allow_html=True)
        cbm = st.number_input(
            "CBM",
            min_value=0.0,
            step=0.5,
            format="%.2f",
            key=f"agl_{wh['name']}",
            label_visibility="collapsed"
        )
        agl_cbm_list.append(cbm)

st.markdown("---")

# ==================== send 五仓输入 ====================

st.markdown('<div class="sub-header">🚚 send 五仓</div>', unsafe_allow_html=True)

# 5列：仓库名、CBM、重量
send5_cols = st.columns(len(SEND5_WAREHOUSES))
send5_cbm_list = []
send5_weight_list = []
for i, wh in enumerate(SEND5_WAREHOUSES):
    with send5_cols[i]:
        st.markdown(f"<div class='warehouse-title'>{wh['name']}</div>", unsafe_allow_html=True)
        
        st.markdown("<div class='input-label'>CBM</div>", unsafe_allow_html=True)
        cbm = st.number_input(
            "cbm",
            min_value=0.0,
            step=0.5,
            format="%.2f",
            key=f"send5_{wh['name']}_cbm",
            label_visibility="collapsed"
        )
        send5_cbm_list.append(cbm)
        
        st.markdown("<div class='input-label'>重量(kg)</div>", unsafe_allow_html=True)
        weight = st.number_input(
            "weight",
            min_value=0.0,
            step=10.0,
            format="%.0f",
            key=f"send5_{wh['name']}_weight",
            label_visibility="collapsed"
        )
        send5_weight_list.append(weight)

st.markdown("---")

# ==================== send 单点输入 ====================

st.markdown('<div class="sub-header">📍 send 单点</div>', unsafe_allow_html=True)

# 三列：CBM、重量、入库配置费
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"<div class='warehouse-title'>GEU2</div>", unsafe_allow_html=True)
    st.markdown("<div class='input-label'>CBM</div>", unsafe_allow_html=True)
    send1_cbm = st.number_input(
        "cbm",
        min_value=0.0,
        step=0.5,
        format="%.2f",
        key="send1_cbm",
        label_visibility="collapsed"
    )

with col2:
    st.markdown(f"<div class='warehouse-title'> </div>", unsafe_allow_html=True)
    st.markdown("<div class='input-label'>重量(kg)</div>", unsafe_allow_html=True)
    send1_weight = st.number_input(
        "weight",
        min_value=0.0,
        step=10.0,
        format="%.0f",
        key="send1_weight",
        label_visibility="collapsed"
    )

with col3:
    st.markdown(f"<div class='warehouse-title'> </div>", unsafe_allow_html=True)
    st.markdown("<div class='input-label'>入库配置费(USD)</div>", unsafe_allow_html=True)
    send1_inbound_usd = st.number_input(
        "usd",
        min_value=0.0,
        step=50.0,
        format="%.0f",
        key="send1_inbound",
        label_visibility="collapsed"
    )
    st.caption(f"≈ ¥{send1_inbound_usd * USD_TO_CNY:.0f}")

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
    
    # send五仓明细
    for name, freight, details, fixed_fee, _ in results:
        if name == "send五仓" and details:
            st.markdown(f"**📋 {name} 费用明细**")
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("固定报关费", f"¥{fixed_fee:.2f}")
            with col_b:
                st.metric("总运费", f"¥{freight:.2f}")
            df_details = pd.DataFrame(details)
            st.dataframe(df_details, use_container_width=True, hide_index=True)
    
    # send单点明细
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
            df_detail = pd.DataFrame([detail])
            st.dataframe(df_detail, use_container_width=True, hide_index=True)

elif not calculate_btn:
    st.info("👆 请先输入发货数据，然后点击「开始比价」")

st.markdown("---")
st.caption(f"📌 体积重系数: 1 CBM = {VOLUME_WEIGHT_RATIO} kg | 汇率: 1 USD = {USD_TO_CNY} CNY")
