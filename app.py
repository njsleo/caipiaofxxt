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
    
    /* 核心魔法：将所有选号按钮变成 32x32 的精美小正圆 */
    div[data-testid="stButton"] button {
        width: 32px !important;
        height: 32px !important;
        min-height: 32px !important;
        padding: 0 !important;
        border-radius: 50% !important;
        font-size: 13px !important;
        font-weight: 600;
        margin: 0 auto;
        box-shadow: 0 2px 3px rgba(0,0,0,0.08);
        transition: all 0.15s;
    }
    /* 特例保护 */
    div[data-testid="stButton"] button:has(p:contains("图")),
    div[data-testid="stButton"] button:has(p:contains("重新")) {
        width: 100% !important; border-radius: 6px !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. 密钥读取与数据引擎
# ==========================================
try:
    APP_ID = st.secrets["mxnzp_api"]["app_id"]
    APP_SECRET = st.secrets["mxnzp_api"]["app_secret"]
except Exception:
    st.error("❌ 密钥错误或未配置。")
    st.stop()

@st.cache_data(ttl=1800)
def fetch_data(issue_count=100): # 增加到100期，K线更好看
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
# 2. 全局状态与快捷工具
# ==========================================
if 'selected_nums' not in st.session_state: st.session_state.selected_nums = set()

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
# 3. 核心量化算法引擎 (生成K线与MACD)
# ==========================================
def generate_strategy_kline(df, strategy, selected_nums, min_hits):
    records = []
    curr_val = 1000.0 # 初始净值资金
    
    for idx, row in df.iterrows():
        nums = row['中奖号码']
        is_hit = False
        
        # 多维条件判定逻辑
        if strategy == "自定义选号狙击":
            hits = sum(1 for n in selected_nums if n in nums)
            is_hit = hits >= min_hits
        elif strategy == "全局大数压制":
            is_hit = sum(1 for n in nums if n > 40) >= 11
        elif strategy == "全局奇数压制":
            is_hit = sum(1 for n in nums if n % 2 != 0) >= 11
        elif strategy == "极端和值爆发":
            is_hit = sum(nums) > 810
            
        # 生成 K 线四个价格
        open_val = curr_val
        if is_hit:
            close_val = open_val + 15  # 阳线大涨
            high_val = close_val + 2
            low_val = open_val - 1
        else:
            close_val = open_val - 4   # 阴线阴跌
            high_val = open_val + 1
            low_val = close_val - 2
            
        curr_val = close_val
        records.append({
            "期号": row['期号'], "Open": open_val, "High": high_val, "Low": low_val, "Close": close_val, "is_hit": is_hit
        })
        
    df_k = pd.DataFrame(records)
    # 计算 MA 均线
    df_k['MA5'] = df_k['Close'].rolling(window=5, min_periods=1).mean()
    df_k['MA10'] = df_k['Close'].rolling(window=10, min_periods=1).mean()
    
    # 计算专业 MACD
    ema_fast = df_k['Close'].ewm(span=12, adjust=False).mean()
    ema_slow = df_k['Close'].ewm(span=26, adjust=False).mean()
    df_k['MACD'] = ema_fast - ema_slow
    df_k['DEA'] = df_k['MACD'].ewm(span=9, adjust=False).mean()
    df_k['MACD_HIST'] = df_k['MACD'] - df_k['DEA']
    
    return df_k

# ==========================================
# 4. 核心布局：左右分栏 (7 : 3)
# ==========================================
left_col, right_col = st.columns([7, 3], gap="medium")

# ------------------------------------------
# 左侧区域：策略回测 K 线引擎
# ------------------------------------------
with left_col:
    top_c1, top_c2, top_c3 = st.columns([2, 1, 3])
    with top_c1:
        strategy_mode = st.selectbox("🔮 量化回测策略模型", ["自定义选号狙击", "全局大数压制", "全局奇数压制", "极端和值爆发"])
    with top_c2:
        hit_target = 2
        if strategy_mode == "自定义选号狙击":
            hit_target = st.number_input("条件: 命中数 ≥", min_value=1, max_value=20, value=2)
            
    if strategy_mode == "自定义选号狙击" and len(st.session_state.selected_nums) == 0:
        st.warning("⚠️ 请先在右侧面板点选至少 1 个号码，以生成回测 K 线。")
    else:
        # 生成 K 线数据
        df_kline = generate_strategy_kline(df_raw, strategy_mode, st.session_state.selected_nums, hit_target)
        
        # 绘制终极金融图表
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
        
        # 上部：K线与均线
        fig.add_trace(go.Candlestick(
            x=df_kline['期号'], open=df_kline['Open'], high=df_kline['High'], low=df_kline['Low'], close=df_kline['Close'],
            increasing_line_color='#FF4B4B', decreasing_line_color='#00D166', name='净值K线'
        ), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_kline['期号'], y=df_kline['MA5'], mode='lines', name='MA5', line=dict(color='#F2B134', width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_kline['期号'], y=df_kline['MA10'], mode='lines', name='MA10', line=dict(color='#00B4D8', width=1)), row=1, col=1)

        # 下部：MACD 柱状图
        macd_colors = ['#FF4B4B' if val > 0 else '#00D166' for val in df_kline['MACD_HIST']]
        fig.add_trace(go.Bar(x=df_kline['期号'], y=df_kline['MACD_HIST'], marker_color=macd_colors, name='MACD量能'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df_kline['期号'], y=df_kline['MACD'], mode='lines', name='DIF', line=dict(color='#FFF', width=1)), row=2, col=1)
        fig.add_trace(go.Scatter(x=df_kline['期号'], y=df_kline['DEA'], mode='lines', name='DEA', line=dict(color='#F2B134', width=1)), row=2, col=1)

        fig.update_layout(height=650, template="plotly_dark", hovermode="x unified", margin=dict(l=0, r=0, t=10, b=0), xaxis_rangeslider_visible=False)
        fig.update_yaxes(gridcolor='#333333')
        st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------
# 右侧区域：紧凑型中控台
# ------------------------------------------
with right_col:
    latest_row = df_raw.iloc[-1]
    latest_issue = latest_row['期号']
    latest_nums = latest_row['中奖号码']
    
    st.markdown(f"<span style='font-size:14px; font-weight:bold;'>🏆 第 {latest_issue} 期 开奖号码</span>", unsafe_allow_html=True)
    html_balls = "".join([f"<div style='display:inline-block; width:26px; height:26px; line-height:26px; text-align:center; background-color:#FF4B4B; color:white; border-radius:50%; margin:4px 4px 15px 0; font-size:12px; font-weight:bold; box-shadow: 0 2px 4px rgba(0,0,0,0.2);'>{n:02d}</div>" for n in latest_nums])
    st.markdown(f"<div style='margin-bottom: 25px;'>{html_balls}</div>", unsafe_allow_html=True)
    
    sel_c1, sel_c2 = st.columns([1.2, 1]) 
    with sel_c1:
        play_mode = st.selectbox("选择玩法", [f"选{i}" for i in range(1, 11)], index=4, label_visibility="collapsed") # 默认选5
        play_n = int(play_mode.replace("选", ""))
    
    btn_cols = st.columns(7)
    filters = ["奇", "偶", "大", "小", "质", "合", "清"]
    for i, f in enumerate(filters):
        if btn_cols[i].button(f, key=f"btn_{f}"):
            apply_filter(f)
            st.rerun() 

    st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True)

    with st.container(border=True):
        for row in range(8):
            cols = st.columns(10)
            for col in range(10):
                num = row * 10 + col + 1
                is_selected = num in st.session_state.selected_nums
                btn_type = "primary" if is_selected else "secondary"
                
                if cols[col].button(f"{num:02d}", type=btn_type, key=f"n_{num}"):
                    if is_selected: st.session_state.selected_nums.remove(num)
                    else: st.session_state.selected_nums.add(num)
                    st.rerun()

    selected_count = len(st.session_state.selected_nums)
    bets = math.comb(selected_count, play_n) if selected_count >= play_n else 0
    cost = bets * 2
    
    if selected_count < play_n:
        st.warning(f"已选 {selected_count} 个，不足 {play_n} 个无法组合。")
    else:
        st.info(f"**{play_mode}** | 已选 **{selected_count}** 个\n\n共 **{bets}** 注 | 需 **{cost}** 元")