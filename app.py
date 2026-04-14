import streamlit as st
import pandas as pd
import requests
import math
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ==========================================
# 0. 页面基础配置与 CSS 魔法 (必须在最前面)
# ==========================================
st.set_page_config(page_title="快乐8 专业量化终端", layout="wide", initial_sidebar_state="collapsed")

# 注入 CSS 强行修改 Streamlit 的默认样式，实现紧凑的专业 UI
st.markdown("""
<style>
    /* 缩小整体页面的上下边距 */
    .block-container { padding-top: 1rem; padding-bottom: 1rem; max-width: 98%; }
    /* 隐藏顶部默认装饰线 */
    header {visibility: hidden;}
    /* 压缩右侧按钮矩阵的间距，让它变成密集的控制台 */
    div[data-testid="column"] { padding: 0 2px !important; }
    div[data-testid="stButton"] button {
        padding: 0 !important;
        height: 32px;
        min-height: 32px;
        border-radius: 4px; /* 轻微圆角，如果想完全圆形可以改成 50% */
        font-size: 13px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


# ==========================================
# 1. 密钥读取与数据引擎 (与之前一样)
# ==========================================
try:
    APP_ID = st.secrets["mxnzp_api"]["app_id"]
    APP_SECRET = st.secrets["mxnzp_api"]["app_secret"]
except Exception:
    st.error("❌ 密钥错误。")
    st.stop()

@st.cache_data(ttl=1800)
def fetch_data(issue_count=50):
    url = "https://www.mxnzp.com/api/lottery/common/history"
    params = {"code": "kl8", "size": min(issue_count, 50), "app_id": APP_ID, "app_secret": APP_SECRET}
    try:
        res = requests.get(url, params=params, timeout=10).json()
        if res.get("code") == 1:
            data = res.get("data", [])
            records = [{"期号": i["expect"], "中奖号码": i["openCode"].split(',')} for i in data]
            return pd.DataFrame(records).iloc[::-1].reset_index(drop=True), "success"
        else:
            return pd.DataFrame(), res.get("msg", "未知错误")
    except Exception as e:
        return pd.DataFrame(), str(e)

def run_analysis(df, target_num):
    omissions = []
    curr = 0
    for row in df['中奖号码']:
        if target_num in row:
            curr = 0
        else:
            curr += 1
        omissions.append(curr)
    df['遗漏值'] = omissions
    
    so_list = []
    last_pos = {} 
    for i, v in enumerate(omissions):
        if v in last_pos:
            so_list.append(i - last_pos[v])
        else:
            so_list.append(0)
        last_pos[v] = i
    df['二阶遗漏'] = so_list
    df['MA5'] = df['遗漏值'].rolling(window=5).mean()
    return df

with st.spinner("正在连接数据中心..."):
    df_raw, status = fetch_data(50)

if df_raw.empty:
    st.error("数据拉取失败。")
    st.stop()

# ==========================================
# 2. 全局状态管理
# ==========================================
if 'selected_nums' not in st.session_state:
    st.session_state.selected_nums = set()
if 'analyze_target' not in st.session_state:
    st.session_state.analyze_target = "08" # 默认分析号码

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
# 3. 核心布局：左右分栏 (7 : 3)
# ==========================================
left_col, right_col = st.columns([7, 3], gap="medium")

# ------------------------------------------
# 左侧区域：大屏专业图表
# ------------------------------------------
with left_col:
    # 顶部状态栏
    c1, c2, c3, c4 = st.columns([2, 2, 2, 4])
    c1.markdown(f"<h3 style='margin:0;'>分析目标: <span style='color:#FF4B4B;'>{st.session_state.analyze_target}</span></h3>", unsafe_allow_html=True)
    
    df_final = run_analysis(df_raw.copy(), st.session_state.analyze_target)
    
    c2.metric("当前一阶遗漏", df_final['遗漏值'].iloc[-1])
    c3.metric("当前二阶拐点", df_final['二阶遗漏'].iloc[-1])
    
    # 画图
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.6, 0.4])

    fig.add_trace(go.Scatter(x=df_final['期号'], y=df_final['遗漏值'], mode='lines+markers', name='一阶遗漏', line=dict(color='#FF4B4B', width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_final['期号'], y=df_final['MA5'], mode='lines', name='5期均线', line=dict(color='#F2B134', width=1, dash='dot')), row=1, col=1)

    df_final['动能'] = df_final['遗漏值'] - df_final['MA5']
    bar_colors = ['#FF4B4B' if x > 0 else '#00D166' for x in df_final['动能']]
    fig.add_trace(go.Bar(x=df_final['期号'], y=df_final['动能'], name='多空脉冲', marker_color=bar_colors), row=2, col=1)
    fig.add_trace(go.Scatter(x=df_final['期号'], y=df_final['二阶遗漏'], name='二阶走势', line=dict(color='#00B4D8', width=1.5)), row=2, col=1)

    fig.update_layout(height=650, template="plotly_dark", hovermode="x unified", margin=dict(l=0, r=0, t=10, b=0))
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor='#333333')
    
    st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------
# 右侧区域：紧凑型中控台
# ------------------------------------------
with right_col:
    # 玩法与快捷筛选区
    play_mode = st.selectbox("选择玩法", [f"选{i}" for i in range(1, 11)], index=2, label_visibility="collapsed")
    play_n = int(play_mode.replace("选", ""))
    
    btn_cols = st.columns(7)
    filters = ["奇", "偶", "大", "小", "质", "合", "清"]
    for i, f in enumerate(filters):
        if btn_cols[i].button(f, key=f"btn_{f}"):
            apply_filter(f)
            st.rerun() 

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True) # 微调间距

    # 高密度 8x10 号码矩阵 (使用 Button 代替 Checkbox)
    with st.container(border=True):
        for row in range(8):
            cols = st.columns(10)
            for col in range(10):
                num = row * 10 + col + 1
                is_selected = num in st.session_state.selected_nums
                
                # 魔法：根据选中状态，动态改变按钮类型（红/灰）
                btn_type = "primary" if is_selected else "secondary"
                
                # 用户点击按钮后，更新状态并强制刷新
                if cols[col].button(f"{num:02d}", type=btn_type, key=f"n_{num}"):
                    if is_selected:
                        st.session_state.selected_nums.remove(num)
                    else:
                        st.session_state.selected_nums.add(num)
                    # 同时将点击的号码设为左侧图表的分析目标
                    st.session_state.analyze_target = f"{num:02d}"
                    st.rerun()

    # 底部结算栏
    selected_count = len(st.session_state.selected_nums)
    bets = math.comb(selected_count, play_n) if selected_count >= play_n else 0
    cost = bets * 2
    
    if selected_count < play_n:
        st.warning(f"已选 {selected_count} 个，不足 {play_n} 个无法组合。")
    else:
        st.info(f"**{play_mode}** | 已选 **{selected_count}** 个\n\n共 **{bets}** 注 | 需 **{cost}** 元")