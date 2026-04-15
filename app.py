import streamlit as st
import pandas as pd
import requests
import math
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ==========================================
# 0. 页面基础配置与 CSS 魔法
# ==========================================
st.set_page_config(page_title="快乐8 专业量化终端", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    .block-container { padding-top: 1rem; padding-bottom: 1rem; max-width: 98%; }
    header {visibility: hidden;}
    div[data-testid="column"] { padding: 0 1px !important; }
    div[data-testid="stVerticalBlock"] { gap: 0.1rem !important; }
    div[data-testid="stVerticalBlock"] > div { padding-bottom: 1px !important; }
    
    /* 圆形数字按钮 */
    div[data-testid="stButton"] button {
        width: 30px !important;
        height: 30px !important;
        min-height: 30px !important;
        padding: 0 !important;
        border-radius: 50% !important;
        font-size: 13px !important;
        font-weight: 600;
        margin: 0 auto;
        transition: all 0.15s;
    }
    /* 保护宽按钮和下拉框 */
    div[data-testid="stButton"] button:has(p:contains("图")),
    div[data-testid="stButton"] button:has(p:contains("重新")),
    div[data-testid="stButton"] button:has(p:contains("大于")) {
        width: 100% !important; border-radius: 4px !important;
    }
    /* 行末的曲线图标按钮特调 */
    div[data-testid="stButton"] button:has(p:contains("📈")) {
        background-color: transparent !important; border: none !important; color: #888 !important; box-shadow: none !important;
    }
    div[data-testid="stButton"] button:has(p:contains("📈")):hover { color: #FFF !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. 状态管理与初始化
# ==========================================
if 'selected_nums' not in st.session_state: st.session_state.selected_nums = set()
if 'analyze_target' not in st.session_state: st.session_state.analyze_target = "08"
if 'hit_condition' not in st.session_state: st.session_state.hit_condition = 3 # 默认命中条件大于等于3

def apply_filter(f_type):
    st.session_state.selected_nums.clear()
    nums = range(1, 81)
    if f_type == "奇": st.session_state.selected_nums.update(n for n in nums if n % 2 != 0)
    elif f_type == "偶": st.session_state.selected_nums.update(n for n in nums if n % 2 == 0)
    elif f_type == "大": st.session_state.selected_nums.update(n for n in nums if n > 40)
    elif f_type == "小": st.session_state.selected_nums.update(n for n in nums if n <= 40)
    elif f_type == "质": 
        primes = [2,3,5,7,11,13,17,19,23,29,31,37,41,43,47,53,59,61,67,71,73,79]
        st.session_state.selected_nums.update(primes)
    elif f_type == "合": 
        primes = [2,3,5,7,11,13,17,19,23,29,31,37,41,43,47,53,59,61,67,71,73,79]
        st.session_state.selected_nums.update(n for n in nums if n not in primes and n != 1)

# ==========================================
# 2. 模拟数据获取 (避免你没有API报错，这里精简了)
# ==========================================
@st.cache_data
def get_mock_data():
    records = []
    for i in range(50):
        records.append({"期号": f"2026{i:03d}", "中奖号码": [1,2,3,4,5,12,15,22,35,40,49,50,55,60,67,69,70,71,77,80]})
    return pd.DataFrame(records).iloc[::-1].reset_index(drop=True)

df_raw = get_mock_data()

# ==========================================
# 3. 核心布局：左右分栏
# ==========================================
left_col, right_col = st.columns([6.5, 3.5], gap="large")

# ------------------------------------------
# 左侧区域：占位图表区 (保持原样)
# ------------------------------------------
with left_col:
    st.markdown("<h3 style='color:#888;'>左侧：多维条件 K 线分析系统</h3>", unsafe_allow_html=True)
    fig = go.Figure(data=[go.Candlestick(x=[1,2,3], open=[10,12,11], high=[13,15,14], low=[9,10,10], close=[12,11,13])])
    fig.update_layout(height=650, template="plotly_dark", margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------
# 右侧区域：极致复刻的中控台
# ------------------------------------------
with right_col:
    # 顶部下拉框与退出按钮
    top_c1, top_c2, top_c3 = st.columns([3, 5, 2])
    top_c1.selectbox("彩种", ["快乐8", "双色球"], label_visibility="collapsed")
    top_c2.markdown("<div style='line-height: 2.5; color:#ccc; font-size:14px;'>第2026093期 ↻</div>", unsafe_allow_html=True)
    top_c3.button("退出模拟", use_container_width=True)

    # 开奖红球展示
    latest_nums = [2,3,7,11,18,22,25,27,38,40,46,48,57,59,60,63,64,69,76,79]
    html_balls = "".join([f"<div style='display:inline-block; width:24px; height:24px; line-height:24px; text-align:center; background-color:#FF4B4B; color:white; border-radius:50%; margin:2px 2px; font-size:11px; font-weight:bold;'>{n:02d}</div>" for n in latest_nums])
    st.markdown(f"<div style='margin: 10px 0;'>{html_balls} 〉</div>", unsafe_allow_html=True)
    
    # 【细节1】主导航 Tabs
    tabs = st.tabs(["号码", "走势图", "指标", "分区", "头尾", "奖金", "社区"])
    
    with tabs[0]:
        # 【细节2】副导航 Buttons
        sub_c1, sub_c2, sub_c3, sub_c4, sub_c5, sub_c6, sub_c7 = st.columns(7)
        sub_c1.button("默认", type="primary")
        sub_c2.button("遗漏")
        sub_c3.button("冷热")
        sub_c6.button("单选")
        sub_c7.button("多选", type="primary")
        
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

        # 【细节3】带行末图标的 8x10+1 矩阵！
        with st.container(border=False):
            for row in range(8):
                # 划分为 11 列，最后一列稍微窄一点用来放图标
                cols = st.columns([1,1,1,1,1,1,1,1,1,1, 0.8])
                for col in range(10):
                    num = row * 10 + col + 1
                    is_selected = num in st.session_state.selected_nums
                    btn_type = "primary" if is_selected else "secondary"
                    
                    if cols[col].button(f"{num:02d}", type=btn_type, key=f"n_{num}"):
                        if is_selected: st.session_state.selected_nums.remove(num)
                        else: st.session_state.selected_nums.add(num)
                        st.rerun()
                # 第 11 列：小图标按钮
                cols[10].button("📈", key=f"chart_{row}")

        # 快捷筛选栏
        st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True)
        f_cols = st.columns(10)
        filters = ["奇", "偶", "大", "小", "质", "合", "清", "随", "10", "导入"]
        for i, f in enumerate(filters):
            if f_cols[i].button(f, key=f"bf_{f}"):
                if f in ["奇", "偶", "大", "小", "质", "合", "清"]: apply_filter(f)
                st.rerun()

        # 【细节4】条件选择器：大于等于 [0 1 2 3 4 5 6]
        st.markdown("<hr style='margin: 10px 0; border-color: #333;'>", unsafe_allow_html=True)
        cond_c1, cond_c2, cond_c3 = st.columns([3, 4, 3])
        cond_c2.selectbox("逻辑", ["大于等于 ▼", "等于 ▼", "小于等于 ▼"], label_visibility="collapsed")
        
        # 0-6 的条件数字球
        num_cols = st.columns([1.5, 1, 1, 1, 1, 1, 1, 1, 1.5])
        for i in range(7):
            ctype = "primary" if st.session_state.hit_condition == i else "secondary"
            if num_cols[i+1].button(str(i), type=ctype, key=f"cond_{i}"):
                st.session_state.hit_condition = i
                st.rerun()

        # 【细节5】底部三大出图按钮
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        b1, b2, b3 = st.columns(3)
        b1.button("单码出图", use_container_width=True)
        b2.button("合并出图", use_container_width=True)
        if b3.button("选中条件出图", use_container_width=True):
            st.toast(f"已下发指令：计算选中的 {len(st.session_state.selected_nums)} 个号码，条件为 大于等于 {st.session_state.hit_condition}")