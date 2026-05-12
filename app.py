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
        margin-top: 1rem;
        margin-bottom: 0.8rem;
        padding-bottom: 0.3rem;
        border-bottom: 2px solid #1f77b4;
    }
    .rate-card {
        background-color: #f8f9fa;
        padding: 0.5rem 0.8rem;
        border-radius: 6px;
        margin-top: 0.3rem;
        margin-bottom: 0.5rem;
        font-size: 0.8rem;
        border-left: 3px solid #1f77b4;
    }
    .rate-card p {
        margin: 2px 0;
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
    .fee-hint {
        font-size: 0.7rem;
        color: #888;
        margin-top: 0.2rem;
    }
    .stNumberInput > div {
        width: 100px !important;
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
    "报关费": 260,  # 每个仓
    "固定费": 434.8,  # 每个仓
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

# 通用配置
VOLUME_WEIGHT_RATIO = 183  # 1 CBM = 183 kg

# ==================== 计算函数 ====================

def calculate_amp(cbm):
    """计算AMP总运费"""
    return AMP_CONFIG["报关费"] + AMP_CONFIG["固定费"] + cbm * AMP_CONFIG["cbm单价"]

def calculate_agl(cbm_list):
    """计算AGL总运费，cbm_list按仓库顺序传入"""
    freight_cbm = 0
    for i, wh in enumerate(AGL_WAREHOUSES):
        freight_cbm += cbm_list[i] * wh["cbm单价"]
    
    total = (AGL_CONFIG["报关费"] * 5) + (AGL_CONFIG["固定费"] * 5) + freight_cbm
    return total

def calculate_send_5(cbm_list, weight_list):
    """计算send五仓总运费，按每个仓库密度独立判断计费方式"""
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
            # 重货：走CBM
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
            # 抛货：走kg
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
    """计算send单点总运费"""
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

# ==================== 主界面 ====================

st.markdown('<div class="main-header">亚马逊物流比价系统</div>', unsafe_allow_html=True)

# 汇率提示
st.info(f"💱 美元兑人民币汇率: 1 USD = {USD_TO_CNY} CNY")

st.markdown("---")

# ==================== AMP + AGL 费率卡片 ====================

st.markdown('<div class="sub-header">1. AMP 及 AGL 费率</div>', unsafe_allow_html=True)

col_amp, col_agl = st.columns(2)

with col_amp:
    st.markdown("**AMP 单点**")
    st.markdown(f"""
    <div class="rate-card">
        <p>报关费: ¥{AMP_CONFIG['报关费']:.0f}</p>
        <p>固定费: ¥{AMP_CONFIG['固定费']:.1f}</p>
        <p>CBM单价: ¥{AMP_CONFIG['cbm单价']:.2f}</p>
        <p class="fee-hint">仓库: {AMP_CONFIG['仓库']}</p>
    </div>
    """, unsafe_allow_html=True)

with col_agl:
    st.markdown("**AGL 五仓**")
    agl_fee_summary = f"""
    <div class="rate-card">
        <p>报关费: ¥{AGL_CONFIG['报关费']:.0f} × 5 = ¥{AGL_CONFIG['报关费']*5:.0f}</p>
        <p>固定费: ¥{AGL_CONFIG['固定费']:.1f} × 5 = ¥{AGL_CONFIG['固定费']*5:.1f}</p>
        <p>CBM单价: </p>
    """
    for wh in AGL_WAREHOUSES:
        agl_fee_summary += f"<p style='margin-left:1rem;'>• {wh['name']}: ¥{wh['cbm单价']:.1f}</p>"
    agl_fee_summary += "</div>"
    st.markdown(agl_fee_summary, unsafe_allow_html=True)

st.markdown("---")

# ==================== AMP 输入 ====================

st.markdown('<div class="sub-header">2. AMP 输入</div>', unsafe_allow_html=True)

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

st.markdown('<div class="sub-header">3. AGL 输入</div>', unsafe_allow_html=True)
st.caption("输入每个仓库的CBM")

# 表头
col_h1, col_h2 = st.columns([0.6, 0.6])
with col_h1:
    st.markdown("**仓库代码**")
with col_h2:
    st.markdown("**CBM**")

agl_cbm_list = []
for wh in AGL_WAREHOUSES:
    cols = st.columns([0.6, 0.6])
    with cols[0]:
        st.markdown(f"{wh['name']}")
    with cols[1]:
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

st.markdown('<div class="sub-header">4. send 五仓输入</div>', unsafe_allow_html=True)
st.caption("输入每个仓库的CBM和重量，系统自动判断走CBM还是kg")

# 表头
col_h1, col_h2, col_h3 = st.columns([0.6, 0.6, 0.6])
with col_h1:
    st.markdown("**仓库代码**")
with col_h2:
    st.markdown("**CBM**")
with col_h3:
    st.markdown("**重量(kg)**")

send5_cbm_list = []
send5_weight_list = []
for wh in SEND5_WAREHOUSES:
    cols = st.columns([0.6, 0.6, 0.6])
    with cols[0]:
        st.markdown(f"{wh['name']}")
    with cols[1]:
        cbm = st.number_input(
            "", 
            min_value=0.0, 
            step=0.5, 
            format="%.2f", 
            key=f"send5_{wh['name']}_cbm",
            label_visibility="collapsed"
        )
        send5_cbm_list.append(cbm)
    with cols[2]:
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

st.markdown('<div class="sub-header">5. send 单点输入</div>', unsafe_allow_html=True)
st.caption("输入仓库数据及入库配置费（美元）")

col_h1, col_h2, col_h3 = st.columns([0.6, 0.6, 0.6])
with col_h1:
    st.markdown("**仓库代码**")
with col_h2:
    st.markdown("**CBM**")
with col_h3:
    st.markdown("**重量(kg)**")

cols = st.columns([0.6, 0.6, 0.6])
with cols[0]:
    st.markdown("GEU2")
with cols[1]:
    send1_cbm = st.number_input(
        "", 
        min_value=0.0, 
        step=0.5, 
        format="%.2f", 
        key="send1_cbm",
        label_visibility="collapsed"
    )
with cols[2]:
    send1_weight = st.number_input(
        "", 
        min_value=0.0, 
        step=10.0, 
        format="%.0f", 
        key="send1_weight",
        label_visibility="collapsed"
    )

st.markdown("**入库配置费**")
col_left, col_center, col_right = st.columns([1, 1, 1])
with col_center:
    send1_inbound_usd = st.number_input(
        "入库配置费（美元）",
        min_value=0.0,
        step=50.0,
        format="%.0f",
        key="send1_inbound",
        label_visibility="collapsed"
    )
st.caption(f"将自动按汇率 {USD_TO_CNY} 换算为人民币")

st.markdown("---")

# ==================== send 计费规则说明 ====================

with st.expander("send 计费规则说明"):
    st.markdown(f"""
    - 报关费: ¥85 × 仓库数
    - 体积重系数: 1 CBM = {VOLUME_WEIGHT_RATIO} kg
    - 计费规则: 每个仓库独立判断
    - 密度 > {VOLUME_WEIGHT_RATIO} kg/m³ → 按CBM计费
    - 密度 ≤ {VOLUME_WEIGHT_RATIO} kg/m³ → 按kg计费，计费重量 = MAX(实际重量, 体积重)
    - 单点额外费用: 入库配置费 (美元) × {USD_TO_CNY}
    """)

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
    
    # 找出最优
    best = min(results, key=lambda x: x[1])
    
    st.markdown('<div class="sub-header">6. 比价结果</div>', unsafe_allow_html=True)
    
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
            
            col_a, col_b, col_c = st.columns(3)
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
st.caption("说明: AMP和AGL仓库固定；send按每个仓库密度自动判断走CBM还是kg；单点入库配置费按汇率7换算")
