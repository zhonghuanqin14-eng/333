import streamlit as st
import pandas as pd

# 页面配置
st.set_page_config(
    page_title="渠道费用测算",
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
    .rate-card {
        background-color: #f8f9fa;
        padding: 0.8rem;
        border-radius: 8px;
        height: 100%;
        font-size: 0.8rem;
        border-left: 3px solid #1f77b4;
    }
    .rate-card p {
        margin: 4px 0;
    }
    .rate-card-title {
        font-weight: bold;
        font-size: 1rem;
        margin-bottom: 8px;
        color: #1f77b4;
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
    .warehouse-row {
        margin-bottom: 1rem;
    }
    .warehouse-label {
        font-weight: 500;
        margin-bottom: 0.3rem;
        color: #333;
    }
    /* 输入框宽度统一 */
    .stNumberInput > div {
        width: 100px !important;
    }
    .stNumberInput {
        display: inline-block;
    }
    /* 仓库行内居中对齐 */
    .warehouse-col {
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# ==================== 固定费率配置 ====================

# 汇率
USD_TO_CNY = 7

# AMP
AMP_CONFIG = {
    "报关费": 260,
    "固定费": 718.8,
    "cbm单价": 1169.69,
    "仓库": "POC系列"
}

# AGL - 5个固定仓库
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

# send 五仓 - 5个固定仓库
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
            warehouse_details.append({
                "仓库": wh["name"],
                "CBM": cbm,
                "重量(kg)": weight,
                "密度": 0,
                "计费方式": "-",
                "运费": 0
            })
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
                "计费量": f"{cbm:.2f} CBM",
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
                "计费量": f"{chargeable_weight:.0f} kg",
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
            "计费量": f"{cbm:.2f} CBM",
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
            "计费量": f"{chargeable_weight:.0f} kg",
            "单价": wh["kg单价"],
            "运费": round(freight, 2)
        }
    
    fixed_fee = SEND1_CONFIG["报关费"]
    total_freight = fixed_fee + freight + inbound_fee_cny
    return total_freight, detail, fixed_fee, inbound_fee_cny

# ==================== 顶部费率卡片 ====================

st.markdown('<div class="main-header">渠道费用测算</div>', unsafe_allow_html=True)

col_rate1, col_rate2, col_rate3 = st.columns(3)

with col_rate1:
    st.markdown(f"""
    <div class="rate-card">
        <div class="rate-card-title">AMP 单点</div>
        <p>报关费: ¥{AMP_CONFIG['报关费']:.0f}</p>
        <p>固定费: ¥{AMP_CONFIG['固定费']:.1f}</p>
        <p>CBM单价: ¥{AMP_CONFIG['cbm单价']:.2f}</p>
        <p>仓库: {AMP_CONFIG['仓库']}</p>
    </div>
    """, unsafe_allow_html=True)

with col_rate2:
    agl_text = f"""
    <div class="rate-card">
        <div class="rate-card-title">AGL 五仓</div>
        <p>报关费: ¥{AGL_CONFIG['报关费']:.0f} × 5 = ¥{AGL_CONFIG['报关费']*5:.0f}</p>
        <p>固定费: ¥{AGL_CONFIG['固定费']:.1f} × 5 = ¥{AGL_CONFIG['固定费']*5:.1f}</p>
        <p>CBM单价:</p>
    """
    for wh in AGL_WAREHOUSES:
        agl_text += f"<p style='margin-left:1rem;'>• {wh['name']}: ¥{wh['cbm单价']:.1f}</p>"
    agl_text += "</div>"
    st.markdown(agl_text, unsafe_allow_html=True)

with col_rate3:
    send_text = f"""
    <div class="rate-card">
        <div class="rate-card-title">send 服务</div>
        <p>报关费: ¥{SEND5_CONFIG['报关费']:.0f} × 仓库数</p>
        <p>固定费: ¥0</p>
        <p>计费规则: 密度 > {VOLUME_WEIGHT_RATIO} → CBM，否则 → kg</p>
        <p>体积重系数: 1 CBM = {VOLUME_WEIGHT_RATIO} kg</p>
        <p class="fee-hint">单点额外 + 入库配置费(USD×7)</p>
    </div>
    """
    st.markdown(send_text, unsafe_allow_html=True)

st.markdown("---")

# ==================== AMP 输入 ====================

st.markdown('<div class="sub-header">AMP 输入</div>', unsafe_allow_html=True)

col_left, col_center, col_right = st.columns([1, 1, 1])
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

st.markdown('<div class="sub-header">AGL 输入</div>', unsafe_allow_html=True)
st.caption("输入每个仓库的CBM")

# 仓库名横排
cols_name = st.columns(len(AGL_WAREHOUSES))
for i, wh in enumerate(AGL_WAREHOUSES):
    with cols_name[i]:
        st.markdown(f"<div style='text-align:center; font-weight:bold;'>{wh['name']}</div>", unsafe_allow_html=True)

# 输入框竖在下面
cols_input = st.columns(len(AGL_WAREHOUSES))
agl_cbm_list = []
for i, wh in enumerate(AGL_WAREHOUSES):
    with cols_input[i]:
        cbm = st.number_input(
            "", 
            min_value=0.0, 
            step=0.5, 
            format="%.2f", 
            key=f"agl_{wh['name']}",
            label_visibility="collapsed"
        )
        agl_cbm_list.append(cbm)

st.markdown("---")

# ==================== send 五仓输入 ====================

st.markdown('<div class="sub-header">send 五仓输入</div>', unsafe_allow_html=True)
st.caption("输入每个仓库的CBM和重量，系统自动判断走CBM还是kg")

# 仓库名横排（两行：第一行仓库名，第二行标注CBM/重量）
cols_name = st.columns(len(SEND5_WAREHOUSES))
for i, wh in enumerate(SEND5_WAREHOUSES):
    with cols_name[i]:
        st.markdown(f"<div style='text-align:center; font-weight:bold;'>{wh['name']}</div>", unsafe_allow_html=True)

# CBM输入行
cols_cbm = st.columns(len(SEND5_WAREHOUSES))
send5_cbm_list = []
for i, wh in enumerate(SEND5_WAREHOUSES):
    with cols_cbm[i]:
        st.markdown("<div style='text-align:center; font-size:0.7rem; color:#666;'>CBM</div>", unsafe_allow_html=True)
        cbm = st.number_input(
            "", 
            min_value=0.0, 
            step=0.5, 
            format="%.2f", 
            key=f"send5_{wh['name']}_cbm",
            label_visibility="collapsed"
        )
        send5_cbm_list.append(cbm)

# 重量输入行
cols_weight = st.columns(len(SEND5_WAREHOUSES))
send5_weight_list = []
for i, wh in enumerate(SEND5_WAREHOUSES):
    with cols_weight[i]:
        st.markdown("<div style='text-align:center; font-size:0.7rem; color:#666;'>重量(kg)</div>", unsafe_allow_html=True)
        weight = st.number_input(
            "", 
            min_value=0.0, 
            step=10.0, 
            format="%.0f", 
            key=f"send5_{wh['name']}_weight",
            label_visibility="collapsed"
        )
        send5_weight_list.append(weight)

st.markdown("---")

# ==================== send 单点输入 ====================

st.markdown('<div class="sub-header">send 单点输入</div>', unsafe_allow_html=True)
st.caption("输入仓库数据及入库配置费（美元）")

# 仓库名
st.markdown("<div style='text-align:center; font-weight:bold; margin-bottom:0.5rem;'>GEU2</div>", unsafe_allow_html=True)

# CBM和重量两列
col_cbm, col_weight = st.columns(2)
with col_cbm:
    st.markdown("<div style='text-align:center; font-size:0.7rem; color:#666;'>CBM</div>", unsafe_allow_html=True)
    send1_cbm = st.number_input(
        "", 
        min_value=0.0, 
        step=0.5, 
        format="%.2f", 
        key="send1_cbm",
        label_visibility="collapsed"
    )
with col_weight:
    st.markdown("<div style='text-align:center; font-size:0.7rem; color:#666;'>重量(kg)</div>", unsafe_allow_html=True)
    send1_weight = st.number_input(
        "", 
        min_value=0.0, 
        step=10.0, 
        format="%.0f", 
        key="send1_weight",
        label_visibility="collapsed"
    )

# 入库配置费
st.markdown("<div style='margin-top:1rem;'><b>入库配置费</b> (USD × 7 = CNY)</div>", unsafe_allow_html=True)
col_left, col_center, col_right = st.columns([1, 1, 1])
with col_center:
    send1_inbound_usd = st.number_input(
        "美元金额",
        min_value=0.0,
        step=50.0,
        format="%.0f",
        key="send1_inbound",
        label_visibility="collapsed"
    )

st.markdown("---")

# ==================== 比价按钮 ====================

center_col, _, _ = st.columns([1, 2, 1])
with center_col:
    calculate_btn = st.button(
        "开始比价", 
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
    
    st.markdown('<div class="sub-header">比价结果</div>', unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="best-channel">
        推荐渠道：{best[0]} | 总运费：¥{best[1]:,.2f}
    </div>
    """, unsafe_allow_html=True)
    
    # 对比表格
    compare_data = []
    for name, freight, _, _, _ in results:
        compare_data.append({
            "渠道": name,
            "总运费": f"¥{freight:,.2f}",
            "比最优贵": f"¥{freight - best[1]:,.2f}" if freight > best[1] else "最优"
        })
    st.dataframe(pd.DataFrame(compare_data), use_container_width=True, hide_index=True)
    
    # send五仓明细
    for name, freight, details, fixed_fee, _ in results:
        if name == "send五仓" and details:
            st.markdown(f"**{name} 费用明细**")
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
            st.markdown(f"**{name} 费用明细**")
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
    st.info("请先输入发货数据，然后点击「开始比价」")

st.markdown("---")
st.caption(f"说明: 体积重系数 1 CBM = {VOLUME_WEIGHT_RATIO} kg；send单点入库配置费按汇率 1 USD = {USD_TO_CNY} CNY 换算")
