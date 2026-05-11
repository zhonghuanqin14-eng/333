import streamlit as st
import pandas as pd
from io import BytesIO

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
</style>
""", unsafe_allow_html=True)

# ==================== 固定费率配置 ====================

AMP_CONFIG = {
    "名称": "AMP单点",
    "报关费": 260,
    "固定费": 718.8,
    "cbm单价": 1169.69,
    "说明": "固定仓库：POC系列"
}

AGL_CONFIG = {
    "名称": "AGL五仓",
    "报关费": 260,
    "固定费": 434.8,
    "美西单价": 597,
    "美东中单价": 557.6,
    "说明": "固定：2个美西 + 3个美东/中"
}

NIUKU_CONFIG = {
    "报关费": 85,
    "体积重系数": 183,
    "说明": "按密度自动分配 kg/CBM"
}

# ==================== 数据处理函数 ====================

def read_shipment_plan(df):
    """读取发货计划，筛选美国"""
    df_us = df[df['国家'] == '美国'].copy()
    if df_us.empty:
        return pd.DataFrame()
    
    cbm_col = None
    weight_col = None
    name_col = None
    
    for col in df_us.columns:
        col_lower = str(col).lower()
        if 'cbm' in col_lower or '体积' in col_lower:
            cbm_col = col
        elif '毛重' in col_lower or 'weight' in col_lower:
            weight_col = col
        elif '品名' in col_lower or '名称' in col_lower or 'product' in col_lower:
            name_col = col
    
    if not all([cbm_col, weight_col, name_col]):
        st.error(f"无法识别列名，请确保包含：品名、CBM、总毛重")
        st.write("当前列名：", list(df_us.columns))
        return pd.DataFrame()
    
    df_us = df_us[[name_col, cbm_col, weight_col]].copy()
    df_us.columns = ['product_name', 'cbm', 'weight_kg']
    df_us = df_us.dropna(subset=['cbm', 'weight_kg'])
    
    return df_us

def load_niuku_rates(df):
    """读取纽酷报价，返回仓库价格字典"""
    rates = {}
    for _, row in df.iterrows():
        warehouse = str(row.iloc[0]).strip().upper()
        if pd.notna(warehouse) and warehouse != 'NAN' and warehouse != '':
            kg_rate = row.iloc[5] if len(row) > 5 and pd.notna(row.iloc[5]) else None
            cbm_rate = row.iloc[8] if len(row) > 8 and pd.notna(row.iloc[8]) else None
            
            if kg_rate and cbm_rate:
                rates[warehouse] = {"kg": float(kg_rate), "cbm": float(cbm_rate)}
    
    return rates

def calculate_amp(cbm):
    return AMP_CONFIG["报关费"] + AMP_CONFIG["固定费"] + cbm * AMP_CONFIG["cbm单价"]

def calculate_agl(west_cbm, east_cbm):
    return (AGL_CONFIG["报关费"] * 5 + 
            AGL_CONFIG["固定费"] * 5 + 
            west_cbm * AGL_CONFIG["美西单价"] + 
            east_cbm * AGL_CONFIG["美东中单价"])

def calculate_niuku_by_warehouse(warehouse_data, rates):
    """
    纽酷运费计算（按仓库分别传入CBM和重量）
    warehouse_data: [{"code": "LGB8", "cbm": 10, "weight": 500}, ...]
    """
    if not warehouse_data:
        return None, {"error": "未提供仓库数据"}
    
    total_warehouse_count = len(warehouse_data)
    fixed_fee = NIUKU_CONFIG["报关费"] * total_warehouse_count
    
    total_cbm_freight = 0
    total_kg_freight = 0
    warehouse_details = []
    
    for wh in warehouse_data:
        code = wh["code"].upper()
        wh_cbm = wh.get("cbm", 0)
        wh_weight = wh.get("weight", 0)
        
        if code not in rates:
            return None, {"error": f"仓库 {code} 在报价表中不存在"}
        
        kg_rate = rates[code]["kg"]
        cbm_rate = rates[code]["cbm"]
        
        density = wh_weight / wh_cbm if wh_cbm > 0 else 0
        volume_weight = wh_cbm * NIUKU_CONFIG["体积重系数"]
        chargeable_weight = max(wh_weight, volume_weight)
        
        if density > NIUKU_CONFIG["体积重系数"]:
            freight = wh_cbm * cbm_rate
            total_cbm_freight += freight
            warehouse_details.append({
                "仓库": code,
                "CBM": wh_cbm,
                "重量(kg)": wh_weight,
                "密度": round(density, 1),
                "计费方式": "CBM",
                "计费量": wh_cbm,
                "单价": cbm_rate,
                "运费": round(freight, 2)
            })
        else:
            freight = chargeable_weight * kg_rate
            total_kg_freight += freight
            warehouse_details.append({
                "仓库": code,
                "CBM": wh_cbm,
                "重量(kg)": wh_weight,
                "体积重(kg)": round(volume_weight, 1),
                "计费重量(kg)": round(chargeable_weight, 1),
                "密度": round(density, 1),
                "计费方式": "kg",
                "计费量": chargeable_weight,
                "单价": kg_rate,
                "运费": round(freight, 2)
            })
    
    total_freight = fixed_fee + total_cbm_freight + total_kg_freight
    
    detail = {
        "warehouse_count": total_warehouse_count,
        "fixed_fee": fixed_fee,
        "total_cbm_freight": total_cbm_freight,
        "total_kg_freight": total_kg_freight,
        "total_freight": total_freight,
        "warehouse_details": warehouse_details
    }
    
    return total_freight, detail

# ==================== 导出Excel ====================

def export_detail_excel(detail, channel_name):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        if detail.get("warehouse_details"):
            df_warehouse = pd.DataFrame(detail["warehouse_details"])
            df_warehouse.to_excel(writer, sheet_name="仓库明细", index=False)
        
        summary = pd.DataFrame([
            ["固定报关费", detail.get("fixed_fee", 0)],
            ["CBM部分运费", detail.get("total_cbm_freight", 0)],
            ["kg部分运费", detail.get("total_kg_freight", 0)],
            ["入库配置费", detail.get("inbound_fee", 0)],
            ["总运费", detail.get("total_freight", 0)]
        ], columns=["项目", "金额(元)"])
        summary.to_excel(writer, sheet_name="费用汇总", index=False)
    
    output.seek(0)
    return output

# ==================== 主界面 ====================

st.markdown('<div class="main-header">亚马逊物流比价系统</div>', unsafe_allow_html=True)

# 文件上传区域
col1, col2 = st.columns(2)

with col1:
    st.markdown('<div class="sub-header">1. 上传发货计划</div>', unsafe_allow_html=True)
    shipment_file = st.file_uploader(
        "选择Excel文件",
        type=['xlsx', 'xls'],
        help="需要包含：国家、品名、CBM、总毛重"
    )
    if shipment_file:
        st.success("文件已上传")

with col2:
    st.markdown('<div class="sub-header">2. 上传纽酷报价</div>', unsafe_allow_html=True)
    niuku_file = st.file_uploader(
        "选择Excel文件（每周更新）",
        type=['xlsx', 'xls'],
        help="需要包含：仓库代码、慢线含税/kg、慢线自税/cbm"
    )
    if niuku_file:
        st.success("文件已上传")

st.markdown("---")

# ==================== AMP + AGL 费率卡片 ====================

st.markdown('<div class="sub-header">3. 渠道费率及输入</div>', unsafe_allow_html=True)

col_amp, col_agl = st.columns(2)

with col_amp:
    st.markdown("**AMP 单点**")
    st.markdown(f"""
    <div class="rate-card">
        <p>报关费: ¥{AMP_CONFIG['报关费']:.0f}</p>
        <p>固定费: ¥{AMP_CONFIG['固定费']:.1f}</p>
        <p>CBM单价: ¥{AMP_CONFIG['cbm单价']:.2f}</p>
        <p class="fee-hint">仓库: POC系列</p>
    </div>
    """, unsafe_allow_html=True)
    amp_cbm = st.number_input(
        "总CBM",
        min_value=0.0,
        step=0.5,
        format="%.2f",
        key="amp_input"
    )

with col_agl:
    st.markdown("**AGL 五仓**")
    st.markdown(f"""
    <div class="rate-card">
        <p>报关费: ¥{AGL_CONFIG['报关费']:.0f} × 5 = ¥{AGL_CONFIG['报关费']*5:.0f}</p>
        <p>固定费: ¥{AGL_CONFIG['固定费']:.1f} × 5 = ¥{AGL_CONFIG['固定费']*5:.1f}</p>
        <p>美西: ¥{AGL_CONFIG['美西单价']:.2f}/CBM | 美东/中: ¥{AGL_CONFIG['美东中单价']:.2f}/CBM</p>
        <p class="fee-hint">固定: 2个美西 + 3个美东/中</p>
    </div>
    """, unsafe_allow_html=True)
    
    col_west, col_east = st.columns(2)
    with col_west:
        agl_west = st.number_input("美西CBM", min_value=0.0, step=0.5, key="agl_west", format="%.2f")
    with col_east:
        agl_east = st.number_input("美东/中CBM", min_value=0.0, step=0.5, key="agl_east", format="%.2f")

st.markdown("---")

# ==================== 纽酷五仓输入 ====================

st.markdown('<div class="sub-header">4. 纽酷五仓</div>', unsafe_allow_html=True)
st.caption("输入亚马逊实际分配的5个仓库，每个仓库的CBM和重量")

# 表头
h1, h2, h3, h4 = st.columns([1.2, 0.6, 0.6, 0.8])
with h1: st.markdown("**仓库代码**")
with h2: st.markdown("**CBM**")
with h3: st.markdown("**重量(kg)**")
with h4: st.markdown("**备注**")

niuku5_data = []

for i in range(5):
    cols = st.columns([1.2, 0.6, 0.6, 0.8])
    with cols[0]:
        code = st.text_input("", placeholder=f"例: LGB8", key=f"n5_code_{i}", label_visibility="collapsed")
    with cols[1]:
        cbm = st.number_input("", min_value=0.0, step=0.5, format="%.2f", key=f"n5_cbm_{i}", label_visibility="collapsed")
    with cols[2]:
        weight = st.number_input("", min_value=0.0, step=10.0, format="%.0f", key=f"n5_weight_{i}", label_visibility="collapsed")
    with cols[3]:
        st.caption("")
    
    if code and code.strip():
        niuku5_data.append({
            "code": code.strip().upper(),
            "cbm": cbm,
            "weight": weight
        })

st.markdown("---")

# ==================== 纽酷单点输入 ====================

st.markdown('<div class="sub-header">5. 纽酷单点</div>', unsafe_allow_html=True)
st.caption("输入亚马逊实际分配的1个仓库，CBM、重量，以及入库配置费")

# 单点输入行
col1, col2, col3, col4 = st.columns([1.2, 0.6, 0.6, 0.8])
with col1:
    single_code = st.text_input("仓库代码", placeholder="例: LGB8", key="single_code", label_visibility="collapsed")
with col2:
    single_cbm = st.number_input("CBM", min_value=0.0, step=0.5, format="%.2f", key="single_cbm", label_visibility="collapsed")
with col3:
    single_weight = st.number_input("重量(kg)", min_value=0.0, step=10.0, format="%.0f", key="single_weight", label_visibility="collapsed")
with col4:
    single_inbound_fee = st.number_input("入库配置费", min_value=0.0, step=50.0, format="%.0f", key="single_inbound", label_visibility="collapsed", help="单点入库需要额外支付的配置费")

niuku1_data = []
if single_code and single_code.strip():
    niuku1_data.append({
        "code": single_code.strip().upper(),
        "cbm": single_cbm,
        "weight": single_weight,
        "inbound_fee": single_inbound_fee
    })

st.markdown("---")

# ==================== 纽酷费率说明 ====================

with st.expander("纽酷计费规则说明"):
    st.markdown(f"""
    - 报关费: ¥{NIUKU_CONFIG['报关费']:.0f} × 仓库数
    - 体积重系数: 1 CBM = {NIUKU_CONFIG['体积重系数']} kg
    - 计费规则: 密度 > {NIUKU_CONFIG['体积重系数']} kg/m³ → 按CBM计费；否则按kg计费
    - kg计费时: 计费重量 = MAX(实际重量, 体积重)
    - 单点额外费用: 入库配置费 (用户手动输入)
    - 单价: 从每周上传的报价表自动匹配
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
    errors = []
    if not shipment_file:
        errors.append("请上传发货计划Excel")
    if not niuku_file:
        errors.append("请上传纽酷报价Excel")
    
    has_data = False
    if amp_cbm > 0:
        has_data = True
    if agl_west > 0 or agl_east > 0:
        has_data = True
    if niuku5_data:
        has_data = True
    if niuku1_data:
        has_data = True
    
    if not has_data:
        errors.append("请至少输入一个渠道的发货数据")
    
    if errors:
        for err in errors:
            st.error(f"{err}")
        st.stop()
    
    with st.spinner("正在计算运费..."):
        try:
            shipment_df_raw = pd.read_excel(shipment_file)
            niuku_df_raw = pd.read_excel(niuku_file)
        except Exception as e:
            st.error(f"文件读取失败: {e}")
            st.stop()
        
        shipment_df = read_shipment_plan(shipment_df_raw)
        if shipment_df.empty:
            st.warning("发货计划中没有找到美国产品")
            st.stop()
        
        niuku_rates = load_niuku_rates(niuku_df_raw)
        if not niuku_rates:
            st.warning("纽酷报价表为空")
            st.stop()
        
        results = []
        
        # AMP
        if amp_cbm > 0:
            amp_freight = calculate_amp(amp_cbm)
            results.append(("AMP", amp_freight, None))
        
        # AGL
        if agl_west > 0 or agl_east > 0:
            agl_freight = calculate_agl(agl_west, agl_east)
            results.append(("AGL", agl_freight, None))
        
        # 纽酷五仓
        if niuku5_data:
            valid = [w for w in niuku5_data if w["code"] and w["cbm"] > 0 and w["weight"] > 0]
            if valid:
                freight, detail = calculate_niuku_by_warehouse(valid, niuku_rates)
                if detail and "error" not in detail:
                    results.append(("纽酷五仓", freight, detail))
        
        # 纽酷单点
        if niuku1_data:
            valid = [w for w in niuku1_data if w["code"] and w["cbm"] > 0 and w["weight"] > 0]
            if valid:
                freight, detail = calculate_niuku_by_warehouse(valid, niuku_rates)
                if detail and "error" not in detail:
                    inbound_fee = valid[0].get("inbound_fee", 0)
                    detail["inbound_fee"] = inbound_fee
                    total_with_inbound = freight + inbound_fee
                    detail["total_freight"] = total_with_inbound
                    results.append(("纽酷单点", total_with_inbound, detail))
        
        if not results:
            st.error("计算失败，请检查输入数据")
            st.stop()
        
        best = min(results, key=lambda x: x[1])
        
        st.markdown('<div class="sub-header">6. 比价结果</div>', unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="best-channel">
            推荐渠道：{best[0]} | 总运费：¥{best[1]:,.2f}
        </div>
        """, unsafe_allow_html=True)
        
        # 对比表格
        compare_data = []
        for name, freight, _ in results:
            compare_data.append({
                "渠道": name,
                "总运费": f"¥{freight:,.2f}",
                "比最优贵": f"¥{freight - best[1]:,.2f}" if freight > best[1] else "最优"
            })
        st.dataframe(pd.DataFrame(compare_data), use_container_width=True, hide_index=True)
        
        # 纽酷详细结果
        for name, freight, detail in results:
            if detail:
                st.markdown(f"**{name} 费用明细**")
                
                col_a, col_b, col_c, col_d = st.columns(4)
                with col_a:
                    st.metric("固定报关费", f"¥{detail.get('fixed_fee', 0):,.2f}")
                with col_b:
                    st.metric("CBM部分", f"¥{detail.get('total_cbm_freight', 0):,.2f}")
                with col_c:
                    st.metric("kg部分", f"¥{detail.get('total_kg_freight', 0):,.2f}")
                with col_d:
                    if name == "纽酷单点":
                        st.metric("入库配置费", f"¥{detail.get('inbound_fee', 0):,.2f}")
                    else:
                        st.metric("合计运费", f"¥{detail.get('total_freight', 0):,.2f}")
                
                if name == "纽酷单点":
                    st.caption(f"总运费 = 报关费 + CBM运费 + kg运费 + 入库配置费")
                
                with st.expander("仓库明细"):
                    df_warehouse = pd.DataFrame(detail['warehouse_details'])
                    st.dataframe(df_warehouse, use_container_width=True, hide_index=True)
                    
                    excel_file = export_detail_excel(detail, name)
                    st.download_button(
                        label=f"下载 {name} 明细",
                        data=excel_file,
                        file_name=f"{name}_运费明细.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
        
        # 发货数据概览
        with st.expander("发货数据概览"):
            total_cbm = shipment_df['cbm'].sum()
            total_weight = shipment_df['weight_kg'].sum()
            avg_density = total_weight / total_cbm if total_cbm > 0 else 0
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("总CBM", f"{total_cbm:.2f} m³")
            with col2:
                st.metric("总重量", f"{total_weight:.0f} kg")
            with col3:
                st.metric("平均密度", f"{avg_density:.1f} kg/m³")

elif not calculate_btn:
    st.info("请先上传文件并输入发货数据，然后点击「开始比价」")

st.markdown("---")
st.caption("说明: AMP和AGL仓库固定；纽酷需输入实际分配的仓库代码；单点需额外填写入库配置费")
