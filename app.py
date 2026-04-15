import streamlit as st
import pandas as pd
import requests
import math
import random
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ==========================================
# 0. 页面基础配置与 CSS 极限微雕
# ==========================================
st.set_page_config(page_title="快乐8 专业量化终端", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    /* 极致压缩边距 */
    .block-container { padding-top: 1rem; padding-bottom: 1rem; max-width: 98%; }
    header {visibility: hidden;}
    div[data-testid="column"] { padding: 0 1px !important; }
    div[data-testid="stVerticalBlock"] { gap: 0.1rem !important; }
    
    /* 【彻底解决竖排文字】强制所有按钮内的 p 标签不换行 */
    div[data-testid="stButton"] button p {
        white-space: nowrap !important;
        margin: 0 !important;
        font-size: 11px !important; /* 统一缩小字体 */
    }
    
    /* 核心矩阵小圆球：缩小尺寸、紧凑排版 */
    div[data-testid="stButton"] button {
        width: 26px !important;
        height: 26px !important;
        min-height: 26px !important;
        padding: 0 !important;
        border-radius: 50% !important;
        margin: 0 auto;
        transition: all 0.1s;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    
    /* 保护长文本功能按钮（宽条状，不要变圆） */
    div[data-testid="stButton"] button:has(p:contains("图")),
    div[data-testid="stButton"] button:has(p:contains("退")),
    div[data-testid="stButton"] button:has(p:contains("大于")),
    div[data-testid="stButton"] button:has(p:contains("默认")),
    div[data-testid="stButton"] button:has(p:contains("遗漏")),
    div[data-testid="stButton"] button:has(p:contains("冷热")),
    div[data-testid="stButton"] button:has(p:contains("单选")),
    div[data-testid="stButton"] button:has(p:contains("多选")) {
        width: 100% !important; 
        border-radius: 4px !important;
        height: 28px !important;
    }
    
    /* 行末曲线图标特调 */
    div[data-testid="stButton"] button:has(p:contains("📈")) {
        background-color: transparent !important; border: none !important; color: #888 !important; box-shadow: none !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. 密钥与数据引擎
# ==========================================
try:
    APP_ID = st.secrets["mxnzp_api"]["app_id"]
    APP_SECRET = st.secrets["mxnzp_api"]["app_secret"]
except Exception:
    st.error("❌ 密钥未配置。请检查 Secrets。")
    st.stop()

@st.cache_data(ttl=1800)
def fetch_data(issue_count=100):
    url = "https://www.mxnzp.com/api/lottery/common/history"
    params = {"code": "kl8", "size": min(issue_count, 50), "app_id": APP_ID, "app_secret": APP_SECRET}
    try:
        res = requests.get(url, params=params, timeout=10).json()
        if res.get("code") == 1:
            data = res.get("data", [])
            records = [{"期号": i["expect"], "中奖号码": [int(x) for x in i["openCode"].split(',')]} for i in data]
            return pd.DataFrame(records).iloc[::-1].reset_index(drop=True), "success"
        else:
            return pd.DataFrame(), res.get("msg", "未知错误")
    except Exception as e:
        return pd.DataFrame(), str(e)

with st.spinner("正在连接数据中心..."):
    df_raw, status = fetch_data(50)

if df_raw.empty:
    st.error("数据拉取失败。")
    st.stop()

# ==========================================
# 2. 全局状态与机选逻辑
# ==========================================
if 'selected_nums' not in st.session_state: st.session_state.selected_nums = set()
if 'hit_condition' not in st.session_state: st.session_state.hit_condition = 2
if 'rand_count' not in st.session_state: st.session_state.rand_count = 10 # 默认机选10个

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

def generate_strategy_kline(df, selected_nums, min_hits):
    records = []
    curr_val = 1000.0 
    for idx, row in df.iterrows():
        nums = row['中奖号码']
        hits = sum(1 for n in selected_nums if n in nums)
        is_hit = hits >= min_hits
        
        open_val = curr_val
        if is_hit:
            close_val = open_val + 15
            high_val = close_val + 2
            low_val = open_val - 1
        else:
            close_val = open_val - 4
            high_val = open_val + 1
            low_val = close_val - 2
            
        curr_val = close_val
        records.append({"期号": row['期号'], "Open": open_val, "High": high_val, "Low": low_val, "Close": close_val})
        
    df_k = pd.DataFrame(records)
    df_k['MA5'] = df_k['Close'].rolling(window=5, min_periods=1).mean()
    
    ema_fast = df_k['Close'].ewm(span=12, adjust=False).mean()
    ema_slow = df_k['Close'].ewm(span=26, adjust=False).mean()
    df_k['MACD'] = ema_fast - ema_slow
    df_k['DEA'] = df_k['MACD'].ewm(span=9, adjust=False).mean()
    df_k['MACD_HIST'] = df_k['MACD'] - df_k['DEA']
    return df_k

# ==========================================
# 3. 核心布局：左右分栏 (调整为 7.2 : 2.8 极限压缩右侧)
# ==========================================
left_col, right_col = st.columns([7.2, 2.8], gap="large")

with left_col:
    st.markdown(f"<h4 style='color:#FF4B4B;'>策略追踪: 选中 {len(st.session_state.selected_nums)} 号码 | 命中 ≥ {st.session_state.hit_condition} 动能趋势</h4>", unsafe_allow_html=True)
    
    if len(st.session_state.selected_nums) == 0:
        st.info("👈 请在右侧面板点选号码，左侧将自动生成这组号码的历史表现 K 线图！")
    else:
        df_kline = generate_strategy_kline(df_raw, st.session_state.selected_nums, st.session_state.hit_condition)
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
        
        fig.add_trace(go.Candlestick(
            x=df_kline['期号'], open=df_kline['Open'], high=df_kline['High'], low=df_kline['Low'], close=df_kline['Close'],
            increasing_line_color='#FF4B4B', decreasing_line_color='#00D166', name='净值K线'
        ), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_kline['期号'], y=df_kline['MA5'], mode='lines', name='MA5', line=dict(color='#F2B134', width=1)), row=1, col=1)

        macd_colors = ['#FF4B4B' if val > 0 else '#00D166' for val in df_kline['MACD_HIST']]
        fig.add_trace(go.Bar(x=df_kline['期号'], y=df_kline['MACD_HIST'], marker_color=macd_colors, name='MACD量能'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df_kline['期号'], y=df_kline['MACD'], mode='lines', name='DIF', line=dict(color='#FFF', width=1)), row=2, col=1)

        fig.update_layout(height=650, template="plotly_dark", hovermode="x unified", margin=dict(l=0, r=0, t=10, b=0), xaxis_rangeslider_visible=False)
        fig.update_yaxes(gridcolor='#333333')
        st.plotly_chart(fig, use_container_width=True)

with right_col:
    # 顶部下拉框与退出按钮
    top_c1, top_c2, top_c3 = st.columns([3, 4, 2])
    top_c1.selectbox("彩种", ["快乐8", "双色球"], label_visibility="collapsed")
    latest_issue = df_raw.iloc[-1]['期号']
    top_c2.markdown(f"<div style='line-height: 2; color:#888; font-size:12px; text-align:center;'>第{latest_issue}期 ↻</div>", unsafe_allow_html=True)
    top_c3.button("退出", use_container_width=True) # 文字缩短避免挤压

    # 真实的开奖红球展示
    latest_nums = df_raw.iloc[-1]['中奖号码']
    html_balls = "".join([f"<div style='display:inline-block; width:22px; height:22px; line-height:22px; text-align:center; background-color:#FF4B4B; color:white; border-radius:50%; margin:1px 1px; font-size:10px; font-weight:bold;'>{n:02d}</div>" for n in latest_nums])
    st.markdown(f"<div style='margin: 5px 0 10px 0;'>{html_balls} 〉</div>", unsafe_allow_html=True)
    
    tabs = st.tabs(["号码", "走势图", "指标", "分区", "头尾", "奖金", "社区"])
    
    with tabs[0]:
        sub_c1, sub_c2, sub_c3, sub_c4, sub_c5, sub_c6, sub_c7 = st.columns(7)
        sub_c1.button("默认", type="primary")
        sub_c2.button("遗漏")
        sub_c3.button("冷热")
        sub_c6.button("单选")
        sub_c7.button("多选", type="primary")
        
        st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True)

        with st.container(border=False):
            for row in range(8):
                cols = st.columns([1,1,1,1,1,1,1,1,1,1, 0.9])
                for col in range(10):
                    num = row * 10 + col + 1
                    is_selected = num in st.session_state.selected_nums
                    btn_type = "primary" if is_selected else "secondary"
                    
                    if cols[col].button(f"{num:02d}", type=btn_type, key=f"n_{num}"):
                        if is_selected: st.session_state.selected_nums.remove(num)
                        else: st.session_state.selected_nums.add(num)
                        st.rerun()
                cols[10].button("📈", key=f"chart_{row}")

        st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True)
        
        # 快捷筛选栏与机选逻辑
        f_cols = st.columns(10)
        filters = ["奇", "偶", "大", "小", "质", "合", "清"]
        for i, f in enumerate(filters):
            if f_cols[i].button(f, key=f"bf_{f}"):
                apply_filter(f)
                st.rerun()
                
        # 机选控制按钮 (随 / 数量切换)
        if f_cols[7].button("随", key="bf_rand", type="primary"):
            st.session_state.selected_nums = set(random.sample(range(1, 81), st.session_state.rand_count))
            st.rerun()
            
        # 机选数量循环切换: 1 -> 3 -> 5 -> 10 -> 20
        if f_cols[8].button(str(st.session_state.rand_count), key="bf_rcnt"):
            cycle_dict = {1: 3, 3: 5, 5: 10, 10: 20, 20: 1}
            st.session_state.rand_count = cycle_dict.get(st.session_state.rand_count, 10)
            st.rerun()
            
        f_cols[9].button("导入", key="bf_in")

        # 条件选择器
        st.markdown("<hr style='margin: 8px 0; border-color: #333;'>", unsafe_allow_html=True)
        cond_c1, cond_c2, cond_c3 = st.columns([3, 4, 3])
        cond_c2.selectbox("逻辑", ["大于等于 ▼", "等于 ▼", "小于等于 ▼"], label_visibility="collapsed")
        
        num_cols = st.columns([1.5, 1, 1, 1, 1, 1, 1, 1, 1.5])
        for i in range(7):
            ctype = "primary" if st.session_state.hit_condition == i else "secondary"
            if num_cols[i+1].button(str(i), type=ctype, key=f"cond_{i}"):
                st.session_state.hit_condition = i
                st.rerun() 

        # 底部三大出图按钮
        st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True)
        b1, b2, b3 = st.columns([1, 1, 1.1]) 
        b1.button("单码出图", use_container_width=True)
        b2.button("合并出图", use_container_width=True)
        b3.button("选中条件", use_container_width=True) # 简化文字防止折行