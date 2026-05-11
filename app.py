import streamlit as st
import pandas as pd
from io import BytesIO

# 页面配置
st.set_page_config(
    page_title="渠道费用测算",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 自定义CSS - 美化界面
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1.5rem;
    }
    .sub-header {
        font-size: 1.3rem;
        font-weight: bold;
        color: #2c3e50;
        margin-top: 1rem;
        margin-bottom: 0.8rem;
        padding-bottom: 0.3rem;
        border-bottom: 2px solid #1f77b4;
    }
    .rate-card {
        background-color: #f8f9fa;
        padding: 0.6rem 0.8rem;
        border-radius: 8px;
        margin-top: 0.5rem;
        margin-bottom: 0.8rem;
        font-size: 0.85rem;
        border-left: 3px solid #1f77b4;
    }
    .rate-card p {
        margin: 0;
        line-height: 1.4;
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
    .metric-card {
        background-color: white;
        padding: 0.8rem;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .small-input .stNumberInput > div > div > input {
        padding: 0.3rem 0.5rem;
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
    
    # 智能识别列名
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

def calculate_niuku_by_warehouse(shipment_df, warehouse_data, rates):
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
        
        # 判断密度决定计费方式
        density = wh_weight / wh_cbm if wh_cbm > 0 else 0
        volume_weight = wh_cbm * NIUKU_CONFIG["体积重系数"]
        chargeable_weight = max(wh_weight, volume_weight)
        
        if density > NIUKU_CONFIG["体积重系数"]:
            # 重货：走CBM
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
            # 抛货：走kg
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
    """导出明细到Excel"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        if detail.get("warehouse_details"):
            df_warehouse = pd.DataFrame(detail["warehouse_details"])
            df_warehouse.to_excel(writer, sheet_name="仓库明细", index=False)
        
        summary = pd.DataFrame([
            ["固定报关费", detail.get("fixed_fee", 0)],
            ["CBM部分运费", detail.get("total_cbm_freight", 0)],
            ["kg部分运费", detail.get("total_kg_freight", 0)],
            ["总运费", detail.get("total_freight", 0)]
        ], columns=["项目", "金额(元)"])
        summary.to_excel(writer, sheet_name="费用汇总", index=False)
    
    output.seek(0)
    return output

# ==================== 主界面 ====================

st.markdown('<div class="main-header">📦 亚马逊物流比价系统</div>', unsafe_allow_html=True)

# 文件上传区域
col1, col2 = st.columns(2)

with col1:
    st.markdown('<div class="sub-header">📁 1. 上传发货计划</div>', unsafe_allow_html=True)
    shipment_file = st.file_uploader(
        "选择Excel文件",
        type=['xlsx', 'xls'],
        help="需要包含：国家、品名、CBM（m³）、总毛重（kg）"
    )
    if shipment_file:
        st.success("✅ 文件已上传")

with col2:
    st.markdown('<div class="sub-header">💰 2. 上传纽酷报价</div>', unsafe_allow_html=True)
    niuku_file = st.file_uploader(
        "选择Excel文件（每周更新）",
        type=['xlsx', 'xls'],
        help="需要包含：仓库代码、慢线含税/kg、慢线自税/cbm"
    )
    if niuku_file:
        st.success("✅ 文件已上传")

st.markdown("---")

# ==================== 渠道输入 ====================

st.markdown('<div class="sub-header">🏭 3. 输入发货数据</div>', unsafe_allow_html=True)

# 三列布局
col_amp, col_agl, col_niuku = st.columns(3)

# ========== AMP ==========
with col_amp:
    st.markdown("#### 🇦 AMP 单点")
    with st.container():
        st.markdown(f"""
        <div class="rate-card">
            <p>📋 报关费：¥{AMP_CONFIG['报关费']:.0f}</p>
            <p>📋 固定费：¥{AMP_CONFIG['固定费']:.1f}</p>
            <p>📦 CBM单价：¥{AMP_CONFIG['cbm单价']:.2f}</p>
            <p style="color:#666; font-size:0.75rem;">🏭 固定仓库：POC系列</p>
        </div>
        """, unsafe_allow_html=True)
    
    amp_cbm = st.number_input(
        "总CBM（方数）",
        min_value=0.0,
        step=0.5,
        format="%.2f",
        help="请输入这批货的总立方数",
        key="amp_input"
    )

# ========== AGL ==========
with col_agl:
    st.markdown("#### 🇧 AGL 五仓")
    with st.container():
        st.markdown(f"""
        <div class="rate-card">
            <p>📋 报关费：¥{AGL_CONFIG['报关费']:.0f} × 5 = ¥{AGL_CONFIG['报关费']*5:.0f}</p>
            <p>📋 固定费：¥{AGL_CONFIG['固定费']:.1f} × 5 = ¥{AGL_CONFIG['固定费']*5:.1f}</p>
            <p>🗺️ 美西仓库：¥{AGL_CONFIG['美西单价']:.2f}/CBM</p>
            <p>🗺️ 美东/中：¥{AGL_CONFIG['美东中单价']:.2f}/CBM</p>
            <p style="color:#666; font-size:0.75rem;">🏭 固定：2个美西 + 3个美东/中</p>
        </div>
        """, unsafe_allow_html=True)
    
    col_west, col_east = st.columns(2)
    with col_west:
        agl_west = st.number_input("美西CBM", min_value=0.0, step=0.5, key="agl_west", format="%.2f")
    with col_east:
        agl_east = st.number_input("美东/中CBM", min_value=0.0, step=0.5, key="agl_east", format="%.2f")

# ========== 纽酷 ==========
with col_niuku:
    st.markdown("#### 🇨 纽酷")
    with st.container():
        st.markdown(f"""
        <div class="rate-card">
            <p>📋 报关费：¥{NIUKU_CONFIG['报关费']:.0f} × 仓库数</p>
            <p>⚖️ 体积重系数：1 CBM = {NIUKU_CONFIG['体积重系数']} kg</p>
            <p>🔄 计费规则：密度 > {NIUKU_CONFIG['体积重系数']} → CBM，否则 → kg</p>
            <p style="color:#666; font-size:0.75rem;">💰 单价从报价表自动匹配</p>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# ==================== 纽酷输入区域 ====================

st.markdown('<div class="sub-header">🇨 3.1 纽酷仓库明细</div>', unsafe_allow_html=True)
st.caption("根据亚马逊实际分配的仓库，输入每个仓库的代码、CBM和总重量")

# 纽酷类型选择
niuku_type = st.radio(
    "选择配送方式",
    ["五仓（5个仓库）", "单点（1个仓库）"],
    horizontal=True,
    key="niuku_type"
)

niuku_warehouse_data = []

if niuku_type == "五仓（5个仓库）":
    # 表头 - 使用更紧凑的比例
    st.markdown("---")
    h1, h2, h3 = st.columns([1.2, 0.8, 0.8])
    with h1: st.markdown("**仓库代码**")
    with h2: st.markdown("**CBM (m³)**")
    with h3: st.markdown("**重量 (kg)**")
    st.markdown("---")
    
    for i in range(5):
        cols = st.columns([1.2, 0.8, 0.8])
        with cols[0]:
            code = st.text_input(
                "", 
                placeholder=f"例: LGB8", 
                key=f"wh_code_{i}",
                label_visibility="collapsed"
            )
        with cols[1]:
            cbm = st.number_input(
                "", 
                min_value=0.0, 
                step=0.5, 
                format="%.2f", 
                key=f"wh_cbm_{i}",
                label_visibility="collapsed"
            )
        with cols[2]:
            weight = st.number_input(
                "", 
                min_value=0.0, 
                step=10.0, 
                format="%.0f",
                key=f"wh_weight_{i}",
                label_visibility="collapsed"
            )
        
        if code and code.strip():
            niuku_warehouse_data.append({
                "code": code.strip().upper(),
                "cbm": cbm,
                "weight": weight
            })

else:  # 单点
    st.markdown("---")
    h1, h2, h3 = st.columns([1.2, 0.8, 0.8])
    with h1: st.markdown("**仓库代码**")
    with h2: st.markdown("**CBM (m³)**")
    with h3: st.markdown("**重量 (kg)**")
    st.markdown("---")
    
    cols = st.columns([1.2, 0.8, 0.8])
    with cols[0]:
        code = st.text_input("", placeholder="例: LGB8", key="single_code", label_visibility="collapsed")
    with cols[1]:
        single_cbm = st.number_input("", min_value=0.0, step=0.5, format="%.2f", key="single_cbm", label_visibility="collapsed")
    with cols[2]:
        single_weight = st.number_input("", min_value=0.0, step=10.0, format="%.0f", key="single_weight", label_visibility="collapsed")
    
    if code:
        niuku_warehouse_data.append({
            "code": code.strip().upper(),
            "cbm": single_cbm,
            "weight": single_weight
        })

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
    # 验证输入
    errors = []
    if not shipment_file:
        errors.append("请上传发货计划Excel")
    if not niuku_file:
        errors.append("请上传纽酷报价Excel")
    
    # 检查至少有一个渠道有数据
    has_data = False
    if amp_cbm > 0:
        has_data = True
    if agl_west > 0 or agl_east > 0:
        has_data = True
    if niuku_warehouse_data:
        has_data = True
    
    if not has_data:
        errors.append("请至少输入一个渠道的发货数据")
    
    if errors:
        for err in errors:
            st.error(f"❌ {err}")
        st.stop()
    
    with st.spinner("正在计算运费，请稍候..."):
        # 读取文件
        try:
            shipment_df_raw = pd.read_excel(shipment_file)
            niuku_df_raw = pd.read_excel(niuku_file)
        except Exception as e:
            st.error(f"文件读取失败: {e}")
            st.stop()
        
        # 处理数据
        shipment_df = read_shipment_plan(shipment_df_raw)
        if shipment_df.empty:
            st.warning("⚠️ 发货计划中没有找到美国产品，请检查'国家'列")
            st.stop()
        
        niuku_rates = load_niuku_rates(niuku_df_raw)
        if not niuku_rates:
            st.warning("⚠️ 纽酷报价表为空，请检查Excel格式")
            st.stop()
        
        # 计算各渠道运费
        results = []
        
        # AMP
        if amp_cbm > 0:
            amp_freight = calculate_amp(amp_cbm)
            results.append(("AMP", amp_freight, None))
        
        # AGL
        if agl_west > 0 or agl_east > 0:
            agl_freight = calculate_agl(agl_west, agl_east)
            results.append(("AGL", agl_freight, None))
        
        # 纽酷
        if niuku_warehouse_data:
            # 验证纽酷数据完整性
            valid_warehouses = [w for w in niuku_warehouse_data if w["code"] and w["cbm"] > 0 and w["weight"] > 0]
            if valid_warehouses:
                niuku_freight, niuku_detail = calculate_niuku_by_warehouse(
                    shipment_df, valid_warehouses, niuku_rates
                )
                if niuku_detail and "error" not in niuku_detail:
                    channel_name = niuku_type
                    results.append((channel_name, niuku_freight, niuku_detail))
                elif niuku_detail and "error" in niuku_detail:
                    st.warning(f"纽酷: {niuku_detail['error']}")
        
        if not results:
            st.error("计算失败，请检查输入数据")
            st.stop()
        
        # 找出最优
        best = min(results, key=lambda x: x[1])
        
        # 结果显示
        st.markdown('<div class="sub-header">📊 4. 比价结果</div>', unsafe_allow_html=True)
        
        # 最优渠道卡片
        st.markdown(f"""
        <div class="best-channel">
            🏆 推荐渠道：{best[0]}<br>
            总运费：¥{best[1]:,.2f}
        </div>
        """, unsafe_allow_html=True)
        
        # 各渠道对比表格
        st.markdown("### 渠道对比")
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
                st.markdown(f"### 📦 {name} 费用明细")
                
                # 费用卡片
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("固定报关费", f"¥{detail['fixed_fee']:,.2f}")
                with col_b:
                    st.metric("CBM部分运费", f"¥{detail['total_cbm_freight']:,.2f}")
                with col_c:
                    st.metric("kg部分运费", f"¥{detail['total_kg_freight']:,.2f}")
                
                # 仓库明细表
                with st.expander("🏢 仓库明细", expanded=True):
                    df_warehouse = pd.DataFrame(detail['warehouse_details'])
                    st.dataframe(df_warehouse, use_container_width=True, hide_index=True)
                    
                    # 下载按钮
                    excel_file = export_detail_excel(detail, name)
                    st.download_button(
                        label=f"📥 下载 {name} 明细Excel",
                        data=excel_file,
                        file_name=f"{name}_运费明细.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
        
        # 发货数据概览
        with st.expander("📈 发货数据概览"):
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
            
            st.caption(f"📌 密度 > {NIUKU_CONFIG['体积重系数']} kg/m³ 为重货，走CBM计费；反之走kg计费")

elif not calculate_btn:
    st.info("👆 请先上传文件并输入发货数据，然后点击「开始比价」")

st.markdown("---")
st.caption("📌 说明：AMP和AGL仓库固定；纽酷需输入实际分配的仓库代码、CBM和重量，系统自动判断重货走CBM、抛货走kg")
