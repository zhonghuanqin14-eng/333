import streamlit as st
import pandas as pd

# 页面配置
st.set_page_config(
    page_title="渠道费用测算",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed"  # 默认收起侧边栏
)

# 自定义CSS - 美化界面
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2c3e50;
        margin-top: 1rem;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #1f77b4;
    }
    .result-box {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 10px;
        margin-top: 1rem;
        margin-bottom: 1rem;
    }
    .best-channel {
        background-color: #27ae60;
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        font-size: 1.3rem;
        font-weight: bold;
    }
    .metric-card {
        background-color: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    .warning-text {
        color: #e74c3c;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

# 固定费率配置
AMP_CONFIG = {
    "名称": "AMP单点",
    "报关费": 260,
    "固定收费": 718.8,
    "cbm单价": 1169.69,
    "说明": "固定仓库：POC系列"
}

AGL_CONFIG = {
    "名称": "AGL五仓",
    "报关费": 260,
    "固定收费": 434.8,
    "美西单价": 597,
    "美东中单价": 557.6,
    "说明": "固定仓库：2个美西 + 3个美东/中"
}

NIUKU_CONFIG = {
    "报关费": 85,
    "体积重系数": 183
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
            # 慢线：含税=kg单价（第6列），自税=cbm单价（第9列）
            kg_rate = row.iloc[5] if len(row) > 5 and pd.notna(row.iloc[5]) else None
            cbm_rate = row.iloc[8] if len(row) > 8 and pd.notna(row.iloc[8]) else None
            
            if kg_rate and cbm_rate:
                rates[warehouse] = {"kg": float(kg_rate), "cbm": float(cbm_rate)}
    
    return rates

def calculate_amp(cbm):
    """计算AMP运费"""
    return AMP_CONFIG["报关费"] + AMP_CONFIG["固定收费"] + cbm * AMP_CONFIG["cbm单价"]

def calculate_agl(west_cbm, east_cbm):
    """计算AGL运费"""
    return (AGL_CONFIG["报关费"] * 5 + 
            AGL_CONFIG["固定收费"] * 5 + 
            west_cbm * AGL_CONFIG["美西单价"] + 
            east_cbm * AGL_CONFIG["美东中单价"])

def calculate_niuku(shipment_df, warehouse_codes, rates):
    """计算纽酷运费（精细化分配）"""
    if not warehouse_codes:
        return None, {"error": "未提供仓库代码"}
    
    fixed_fee = NIUKU_CONFIG["报关费"] * len(warehouse_codes)
    
    # 获取第一个仓库的报价
    first_warehouse = warehouse_codes[0]
    if first_warehouse not in rates:
        return None, {"error": f"仓库 {first_warehouse} 在报价表中不存在"}
    
    kg_rate = rates[first_warehouse]["kg"]
    cbm_rate = rates[first_warehouse]["cbm"]
    
    cbm_total = 0
    kg_total = 0
    cbm_products = []
    kg_products = []
    
    for _, row in shipment_df.iterrows():
        cbm = row['cbm']
        weight = row['weight_kg']
        density = weight / cbm if cbm > 0 else 0
        
        if density > NIUKU_CONFIG["体积重系数"]:
            cbm_total += cbm
            cbm_products.append(row['product_name'])
        else:
            volume_weight = cbm * NIUKU_CONFIG["体积重系数"]
            chargeable_weight = max(weight, volume_weight)
            kg_total += chargeable_weight
            kg_products.append((row['product_name'], chargeable_weight))
    
    cbm_freight = cbm_total * cbm_rate
    kg_freight = kg_total * kg_rate
    total_freight = fixed_fee + cbm_freight + kg_freight
    
    detail = {
        "warehouses": warehouse_codes,
        "warehouse_count": len(warehouse_codes),
        "kg_rate": kg_rate,
        "cbm_rate": cbm_rate,
        "fixed_fee": fixed_fee,
        "cbm_total": cbm_total,
        "kg_total": kg_total,
        "cbm_freight": cbm_freight,
        "kg_freight": kg_freight,
        "total_freight": total_freight,
        "cbm_products": cbm_products,
        "kg_products": kg_products
    }
    
    return total_freight, detail

# ==================== 主界面 ====================

st.markdown('<div class="main-header">📦 亚马逊物流比价系统</div>', unsafe_allow_html=True)

# 使用列布局，让上传区域更宽敞
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

# 三个渠道使用三列
channel_col1, channel_col2, channel_col3 = st.columns(3)

with channel_col1:
    st.markdown("#### 🇦 AMP 单点")
    st.caption("固定仓库：POC系列")
    amp_cbm = st.number_input(
        "总CBM（方数）",
        min_value=0.0,
        step=0.5,
        format="%.2f",
        help="请输入这批货的总立方数",
        key="amp_input"
    )
    if amp_cbm > 0:
        col1_1, col1_2 = st.columns(2)
        with col1_1:
            st.metric("报关费", f"¥{AMP_CONFIG['报关费']:.0f}")
        with col1_2:
            st.metric("操作费", f"¥{AMP_CONFIG['固定收费']:.0f}")
        st.metric("CBM单价", f"¥{AMP_CONFIG['cbm单价']:.2f}", help="POC系列仓库单价")

with channel_col2:
    st.markdown("#### 🇧 AGL 五仓")
    st.caption("固定仓库：2个美西 + 3个美东/中")
    
    col_west, col_east = st.columns(2)
    with col_west:
        agl_west = st.number_input(
            "美西CBM",
            min_value=0.0,
            step=0.5,
            format="%.2f",
            help="分配到美西仓库的方数",
            key="agl_west"
        )
    with col_east:
        agl_east = st.number_input(
            "美东/中CBM",
            min_value=0.0,
            step=0.5,
            format="%.2f",
            help="分配到美东/中仓库的方数",
            key="agl_east"
        )
    
    if agl_west > 0 or agl_east > 0:
        st.caption(f"美西单价: ¥{AGL_CONFIG['美西单价']} | 美东/中: ¥{AGL_CONFIG['美东中单价']}")
        st.caption(f"固定费用: ¥{AGL_CONFIG['报关费']*5} (报关) + ¥{AGL_CONFIG['固定收费']*5} (操作)")

with channel_col3:
    st.markdown("#### 🇨 纽酷")
    st.caption("仓库由亚马逊分配，输入实际分配的仓库代码")
    
    # 纽酷五仓
    with st.expander("🏢 五仓（5个仓库）", expanded=True):
        niuku5_codes = []
        cols = st.columns(3)
        for i in range(5):
            col_idx = i % 3
            with cols[col_idx]:
                code = st.text_input(
                    f"仓库{i+1}",
                    placeholder="如 LGB8",
                    key=f"niuku5_{i}",
                    help="请输入大写仓库代码"
                )
                if code:
                    niuku5_codes.append(code.strip().upper())
        
        if len(niuku5_codes) == 5:
            st.success(f"✅ 已输入 {len(niuku5_codes)} 个仓库")
        elif len(niuku5_codes) > 0:
            st.warning(f"⚠️ 还需要 {5 - len(niuku5_codes)} 个仓库")
    
    # 纽酷单点
    with st.expander("📍 单点（1个仓库）", expanded=True):
        niuku1_code = st.text_input(
            "仓库代码",
            placeholder="如 LGB8",
            key="niuku1",
            help="请输入大写仓库代码"
        ).strip().upper()
        if niuku1_code:
            st.success(f"✅ 已输入仓库: {niuku1_code}")

st.markdown("---")

# ==================== 比价按钮 ====================

center_col, _, _ = st.columns([2, 3, 2])
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
    if amp_cbm == 0 and agl_west == 0 and agl_east == 0 and not niuku5_codes and not niuku1_code:
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
            st.warning("⚠️ 发货计划中没有找到美国产品，请检查'国家'列是否包含'美国'")
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
            results.append(("AMP", amp_freight, None, AMP_CONFIG))
        
        # AGL
        if agl_west > 0 or agl_east > 0:
            agl_freight = calculate_agl(agl_west, agl_east)
            results.append(("AGL", agl_freight, None, AGL_CONFIG))
        
        # 纽酷五仓
        if len(niuku5_codes) == 5:
            freight, detail = calculate_niuku(shipment_df, niuku5_codes, niuku_rates)
            if detail and "error" not in detail:
                results.append(("纽酷五仓", freight, detail, None))
            elif detail and "error" in detail:
                st.warning(f"纽酷五仓: {detail['error']}")
        
        # 纽酷单点
        if niuku1_code:
            freight, detail = calculate_niuku(shipment_df, [niuku1_code], niuku_rates)
            if detail and "error" not in detail:
                results.append(("纽酷单点", freight, detail, None))
            elif detail and "error" in detail:
                st.warning(f"纽酷单点: {detail['error']}")
        
        if not results:
            st.error("计算失败，请检查输入数据")
            st.stop()
        
        # 找出最优
        best = min(results, key=lambda x: x[1])
        
        # ==================== 结果显示 ====================
        
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
        for name, freight, _, config in results:
            compare_data.append({
                "渠道": name,
                "总运费": f"¥{freight:,.2f}",
                "比最优贵": f"¥{freight - best[1]:,.2f}" if freight > best[1] else "最优"
            })
        
        st.dataframe(pd.DataFrame(compare_data), use_container_width=True, hide_index=True)
        
        # 纽酷详细分组（如果有）
        for name, freight, detail, _ in results:
            if detail:
                st.markdown(f"### 📦 {name} 费用明细")
                
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("固定报关费", f"¥{detail['fixed_fee']:,.2f}")
                with col_b:
                    st.metric("CBM部分", f"¥{detail['cbm_freight']:,.2f}")
                with col_c:
                    st.metric("kg部分", f"¥{detail['kg_freight']:,.2f}")
                
                st.markdown(f"""
                **计费参数**
                - kg单价：¥{detail['kg_rate']:.2f} / kg
                - CBM单价：¥{detail['cbm_rate']:.2f} / CBM
                - 体积重系数：1 CBM = {NIUKU_CONFIG['体积重系数']} kg
                """)
                
                with st.expander(f"📋 查看产品分组详情"):
                    st.markdown(f"**重货（按CBM计费）** - {len(detail['cbm_products'])}个产品")
                    if detail['cbm_products']:
                        st.write(detail['cbm_products'][:10])  # 最多显示10个
                        if len(detail['cbm_products']) > 10:
                            st.caption(f"... 还有 {len(detail['cbm_products']) - 10} 个产品")
                    else:
                        st.caption("无")
                    
                    st.markdown(f"**抛货（按kg计费）** - {len(detail['kg_products'])}个产品")
                    if detail['kg_products']:
                        kg_preview = [f"{p[0]}: {p[1]:.1f}kg" for p in detail['kg_products'][:10]]
                        st.write(kg_preview)
                        if len(detail['kg_products']) > 10:
                            st.caption(f"... 还有 {len(detail['kg_products']) - 10} 个产品")
                    else:
                        st.caption("无")
        
        # 数据概览
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
            
            st.caption("密度 > 183 kg/m³ 为重货，走CBM计费；反之走kg计费")

elif not calculate_btn:
    st.info("👆 请先上传文件并输入发货数据，然后点击「开始比价」")

# 底部说明
st.markdown("---")
st.caption("📌 说明：AMP和AGL仓库固定；纽酷仓库需输入实际分配的仓库代码。纽酷采用精细化分配：重货走CBM，抛货走kg。")
