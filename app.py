"""
亚马逊物流比价系统 - Streamlit Web版
支持文件上传和在线比价
"""

import streamlit as st
import pandas as pd
from typing import Dict, List, Tuple

# 页面配置
st.set_page_config(
    page_title="物流比价系统",
    page_icon="📦",
    layout="wide"
)

# ==================== 固定费率配置 ====================
AMP_CONFIG = {
    "报关费": 260,
    "固定收费": 718.8,
    "cbm单价": 1169.69
}

AGL_CONFIG = {
    "报关费": 260,
    "固定收费": 434.8,
    "美西单价": 597,
    "美东中单价": 557.6
}

NIUKU_CONFIG = {
    "报关费": 85,
    "体积重系数": 183
}


# ==================== 读取数据 ====================

def read_shipment_plan(df: pd.DataFrame) -> pd.DataFrame:
    """读取发货计划DataFrame，筛选国家=美国"""
    df_us = df[df['国家'] == '美国'].copy()
    # 根据实际列名调整
    if 'CBM（m³）' in df_us.columns:
        df_us = df_us[['品名', 'CBM（m³）', '总毛重（kg）']]
        df_us.columns = ['product_name', 'cbm', 'weight_kg']
    elif 'CBM' in df_us.columns:
        df_us = df_us[['品名', 'CBM', '总毛重']]
        df_us.columns = ['product_name', 'cbm', 'weight_kg']
    else:
        # 尝试自动识别
        cbm_col = [c for c in df_us.columns if 'cbm' in c.lower()][0]
        weight_col = [c for c in df_us.columns if '毛重' in c or 'weight' in c.lower()][0]
        name_col = [c for c in df_us.columns if '品名' in c or '名称' in c][0]
        df_us = df_us[[name_col, cbm_col, weight_col]]
        df_us.columns = ['product_name', 'cbm', 'weight_kg']
    
    df_us = df_us.dropna(subset=['cbm', 'weight_kg'])
    return df_us


def load_niuku_rates(df: pd.DataFrame) -> Dict:
    """读取纽酷报价DataFrame，只取慢线"""
    rates = {}
    # 慢线kg在第6列（索引5），慢线cbm在第9列（索引8）
    for _, row in df.iterrows():
        warehouse = str(row.iloc[0])
        if pd.notna(warehouse) and warehouse != 'nan':
            kg_rate = row.iloc[5] if len(row) > 5 and pd.notna(row.iloc[5]) else None
            cbm_rate = row.iloc[8] if len(row) > 8 and pd.notna(row.iloc[8]) else None
            if kg_rate is not None or cbm_rate is not None:
                rates[warehouse] = {"kg": kg_rate, "cbm": cbm_rate}
    return rates


# ==================== 运费计算 ====================

def calculate_amp(total_cbm: float) -> float:
    return AMP_CONFIG["报关费"] + AMP_CONFIG["固定收费"] + total_cbm * AMP_CONFIG["cbm单价"]


def calculate_agl(west_cbm: float, east_cbm: float) -> float:
    return (AGL_CONFIG["报关费"] * 5 + 
            AGL_CONFIG["固定收费"] * 5 + 
            west_cbm * AGL_CONFIG["美西单价"] + 
            east_cbm * AGL_CONFIG["美东中单价"])


def calculate_niuku(shipment_df: pd.DataFrame, 
                    warehouse_codes: List[str], 
                    rates: Dict) -> Tuple[float, Dict]:
    """计算纽酷总运费（精细化分配）"""
    if not warehouse_codes:
        return 0, {"error": "未提供仓库代码"}
    
    fixed_fee = NIUKU_CONFIG["报关费"] * len(warehouse_codes)
    
    first_warehouse = warehouse_codes[0]
    if first_warehouse not in rates:
        return 0, {"error": f"仓库 {first_warehouse} 不存在"}
    
    kg_rate = rates[first_warehouse]["kg"]
    cbm_rate = rates[first_warehouse]["cbm"]
    
    if kg_rate is None or cbm_rate is None:
        return 0, {"error": f"仓库 {first_warehouse} 缺少报价"}
    
    cbm_group = []
    kg_group = []
    
    for _, row in shipment_df.iterrows():
        cbm = row['cbm']
        weight = row['weight_kg']
        density = weight / cbm if cbm > 0 else 0
        
        if density > NIUKU_CONFIG["体积重系数"]:
            cbm_group.append(cbm)
        else:
            volume_weight = cbm * NIUKU_CONFIG["体积重系数"]
            chargeable_weight = max(weight, volume_weight)
            kg_group.append(chargeable_weight)
    
    total_cbm = sum(cbm_group)
    total_kg = sum(kg_group)
    
    cbm_freight = total_cbm * cbm_rate
    kg_freight = total_kg * kg_rate
    total_freight = fixed_fee + cbm_freight + kg_freight
    
    detail = {
        "fixed_fee": fixed_fee,
        "warehouse_count": len(warehouse_codes),
        "warehouses": warehouse_codes,
        "kg_rate": kg_rate,
        "cbm_rate": cbm_rate,
        "total_cbm": total_cbm,
        "total_kg": total_kg,
        "cbm_freight": cbm_freight,
        "kg_freight": kg_freight,
        "total_freight": total_freight,
        "cbm_product_count": len(cbm_group),
        "kg_product_count": len(kg_group)
    }
    
    return total_freight, detail


# ==================== UI界面 ====================

st.title("📦 亚马逊物流比价系统")
st.markdown("支持 AMP、AGL、纽酷 三渠道比价")

# 侧边栏 - 文件上传
with st.sidebar:
    st.header("📁 上传文件")
    
    shipment_file = st.file_uploader(
        "发货计划Excel", 
        type=['xlsx', 'xls'],
        help="需包含：国家、品名、CBM、总毛重"
    )
    
    niuku_file = st.file_uploader(
        "纽酷报价Excel", 
        type=['xlsx', 'xls'],
        help="需包含仓库代码、慢线含税/kg、自税/cbm"
    )
    
    st.markdown("---")
    st.header("🏭 渠道输入")
    
    # AMP
    st.subheader("AMP")
    amp_cbm = st.number_input("总CBM（方数）", min_value=0.0, step=0.1, key="amp_cbm")
    
    # AGL
    st.subheader("AGL")
    col1, col2 = st.columns(2)
    with col1:
        agl_west = st.number_input("美西CBM", min_value=0.0, step=0.1, key="agl_west")
    with col2:
        agl_east = st.number_input("美东/中CBM", min_value=0.0, step=0.1, key="agl_east")
    
    # 纽酷五仓
    st.subheader("纽酷五仓")
    niuku5_codes = []
    for i in range(5):
        code = st.text_input(f"仓库{i+1}", key=f"niuku5_{i}", placeholder="如 LGB8")
        if code:
            niuku5_codes.append(code.upper())
    
    # 纽酷单点
    st.subheader("纽酷单点")
    niuku1_code = st.text_input("仓库代码", key="niuku1", placeholder="如 LGB8")
    
    # 计算按钮
    st.markdown("---")
    calculate_btn = st.button("🚀 开始比价", type="primary", use_container_width=True)

# 主区域 - 结果显示
if calculate_btn:
    if not shipment_file or not niuku_file:
        st.error("请上传发货计划和纽酷报价文件")
    elif amp_cbm <= 0 and agl_west <= 0 and agl_east <= 0 and not niuku5_codes and not niuku1_code:
        st.error("请至少输入一个渠道的数据")
    else:
        with st.spinner("计算中..."):
            # 读取文件
            shipment_df_raw = pd.read_excel(shipment_file)
            niuku_df_raw = pd.read_excel(niuku_file)
            
            # 处理数据
            shipment_df = read_shipment_plan(shipment_df_raw)
            niuku_rates = load_niuku_rates(niuku_df_raw)
            
            if shipment_df.empty:
                st.warning("发货计划中没有美国产品")
                st.stop()
            
            if not niuku_rates:
                st.warning("纽酷报价表为空")
                st.stop()
            
            # 计算结果
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
            niuku5_freight = None
            niuku5_detail = None
            if len(niuku5_codes) == 5:
                niuku5_freight, niuku5_detail = calculate_niuku(shipment_df, niuku5_codes, niuku_rates)
                if "error" not in niuku5_detail:
                    results.append(("纽酷五仓", niuku5_freight, niuku5_detail))
            
            # 纽酷单点
            niuku1_freight = None
            niuku1_detail = None
            if niuku1_code:
                niuku1_freight, niuku1_detail = calculate_niuku(shipment_df, [niuku1_code], niuku_rates)
                if "error" not in niuku1_detail:
                    results.append(("纽酷单点", niuku1_freight, niuku1_detail))
            
            if not results:
                st.error("计算失败，请检查输入数据")
                st.stop()
            
            # 找出最优
            best = min(results, key=lambda x: x[1])
            
            # 显示结果
            st.success(f"🏆 推荐渠道：{best[0]}，总运费：¥{best[1]:,.2f}")
            
            # 详细结果表格
            st.subheader("📊 各渠道运费对比")
            compare_data = []
            for name, freight, detail in results:
                compare_data.append({
                    "渠道": name,
                    "总运费(元)": f"¥{freight:,.2f}",
                    "比最优贵(元)": f"¥{freight - best[1]:,.2f}" if name != best[0] else "最优"
                })
            st.dataframe(pd.DataFrame(compare_data), use_container_width=True)
            
            # 纽酷详细分组
            st.subheader("📦 纽酷精细化分配详情")
            
            col1, col2 = st.columns(2)
            
            if niuku5_detail and "error" not in niuku5_detail:
                with col1:
                    st.markdown("**纽酷五仓**")
                    st.markdown(f"""
                    - 仓库：{', '.join(niuku5_detail['warehouses'])}
                    - kg单价：¥{niuku5_detail['kg_rate']:.2f}
                    - CBM单价：¥{niuku5_detail['cbm_rate']:.2f}
                    - 固定报关费：¥{niuku5_detail['fixed_fee']:.2f}
                    - CBM组：{niuku5_detail['cbm_product_count']}个产品，{niuku5_detail['total_cbm']:.2f} CBM → ¥{niuku5_detail['cbm_freight']:.2f}
                    - kg组：{niuku5_detail['kg_product_count']}个产品，{niuku5_detail['total_kg']:.2f} kg → ¥{niuku5_detail['kg_freight']:.2f}
                    - **小计：¥{niuku5_detail['total_freight']:.2f}**
                    """)
            
            if niuku1_detail and "error" not in niuku1_detail:
                with col2:
                    st.markdown("**纽酷单点**")
                    st.markdown(f"""
                    - 仓库：{niuku1_detail['warehouses'][0]}
                    - kg单价：¥{niuku1_detail['kg_rate']:.2f}
                    - CBM单价：¥{niuku1_detail['cbm_rate']:.2f}
                    - 固定报关费：¥{niuku1_detail['fixed_fee']:.2f}
                    - CBM组：{niuku1_detail['cbm_product_count']}个产品，{niuku1_detail['total_cbm']:.2f} CBM → ¥{niuku1_detail['cbm_freight']:.2f}
                    - kg组：{niuku1_detail['kg_product_count']}个产品，{niuku1_detail['total_kg']:.2f} kg → ¥{niuku1_detail['kg_freight']:.2f}
                    - **小计：¥{niuku1_detail['total_freight']:.2f}**
                    """)
            
            # 产品明细表（可选）
            with st.expander("📋 产品明细（用于纽酷分组）"):
                st.dataframe(shipment_df, use_container_width=True)
