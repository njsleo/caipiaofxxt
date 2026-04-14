import streamlit as st
import pandas as pd
import requests
import math
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ==========================================
# 0. 页面基础配置 (必须在最前面)
# ==========================================
st.set_page_config(page_title="快乐8 高级量化分析平台", layout="wide", initial_sidebar_state="expanded")
st.title("📈 快乐8 实时量化分析与选号工作台")

# ==========================================
# 1. 密钥读取 (Secrets 管理)
# ==========================================
try:
    APP_ID = st.secrets["mxnzp_api"]["app_id"]
    APP_SECRET = st.secrets["mxnzp_api"]["app_secret"]
except Exception:
    st.error("❌ 未在 Secrets 中找到密钥！请确保您已在 streamlit.io 后台设置了 [mxnzp_api] 块。")
    st.info("本地测试请检查 `.streamlit/secrets.toml` 文件是否正确配置。")
    st.stop()

# ==========================================
# 2. 数据获取引擎 (API 连接)
# ==========================================
@st.cache_data(ttl=1800) # 缓存30分钟
def fetch_data(issue_count=50):
    url = "https://www.mxnzp.com/api/lottery/common/history"
    params = {
        "code": "kl8",
        "size": min(issue_count, 50),
        "app_id": APP_ID,
        "app_secret": APP_SECRET
    }
    try:
        res = requests.get(url, params=params, timeout=10).json()
        if res.get("code") == 1:
            data = res.get("data", [])
            records = [{"期号": i["expect"], "中奖号码": i["openCode"].split(',')} for i in data]
            # 翻转为正序以便画图
            return pd.DataFrame(records).iloc[::-1].reset_index(drop=True), "success"
        else:
            return pd.DataFrame(), res.get("msg", "未知错误")
    except Exception as e:
        return pd.DataFrame(), str(e)

# ==========================================
# 3. 核心算法库 (一阶/二阶遗漏)
# ==========================================
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

# ==========================================
# 4. 上半部：全网数据拉取与专业走势看板
# ==========================================
with st.spinner("正在同步全网实时开奖数据..."):
    df_raw, status = fetch_data(50)

if df_raw.empty:
    st.error(f"数据拉取失败，请稍后再试或检查 API 状态。原因: {status}")
    st.stop()

# 侧边栏：图表控制
st.sidebar.header("🎯 走势追踪引擎")
target = st.sidebar.selectbox("选择要分析的具体号码", [f"{i:02d}" for i in range(1, 81)], index=7)
st.sidebar.markdown("---")
st.sidebar.write("**【图表算法说明】**")
st.sidebar.caption("一阶遗漏：该号码自上次开出后，至今未出现的期数（压力位）。")
st.sidebar.caption("二阶遗漏：当前的遗漏状态，距离它上一次发生这种状态，中间相隔了多少期（拐点动能）。")

df_final = run_analysis(df_raw.copy(), target)

# 顶部指标卡
c1, c2, c3 = st.columns(3)
c1.metric("当前遗漏", df_final['遗漏值'].iloc[-1])
c2.metric("当前二阶遗漏", df_final['二阶遗漏'].iloc[-1])
c3.metric("5期平均遗漏线", round(df_final['MA5'].iloc[-1], 2))

# 绘制双层金融图表
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.6, 0.4])

fig.add_trace(go.Scatter(x=df_final['期号'], y=df_final['遗漏值'], mode='lines+markers', name='一阶遗漏', line=dict(color='#FF4B4B', width=2)), row=1, col=1)
fig.add_trace(go.Scatter(x=df_final['期号'], y=df_final['MA5'], mode='lines', name='5期均线', line=dict(color='#F2B134', width=1, dash='dot')), row=1, col=1)

df_final['动能'] = df_final['遗漏值'] - df_final['MA5']
bar_colors = ['#FF4B4B' if x > 0 else '#00D166' for x in df_final['动能']]
fig.add_trace(go.Bar(x=df_final['期号'], y=df_final['动能'], name='多空脉冲', marker_color=bar_colors), row=2, col=1)
fig.add_trace(go.Scatter(x=df_final['期号'], y=df_final['二阶遗漏'], name='二阶走势', line=dict(color='#00B4D8', width=1.5)), row=2, col=1)

fig.update_layout(height=500, template="plotly_dark", hovermode="x unified", margin=dict(l=10, r=10, t=30, b=10))
fig.update_xaxes(showgrid=False)
fig.update_yaxes(gridcolor='#333333')

st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 5. 下半部：智能选号与模拟投注计算器
# ==========================================
st.markdown("---")
st.subheader("🎛️ 智能选号中控台")

# 5.1 状态管理
if 'selected_nums' not in st.session_state:
    st.session_state.selected_nums = set()

# 5.2 快捷筛选逻辑
def apply_filter(f_type):
    st.session_state.selected_nums.clear()
    nums = range(1, 81)
    if f_type == "奇":
        st.session_state.selected_nums.update(n for n in nums if n % 2 != 0)
    elif f_type == "偶":
        st.session_state.selected_nums.update(n for n in nums if n % 2 == 0)
    elif f_type == "大":
        st.session_state.selected_nums.update(n for n in nums if n > 40)
    elif f_type == "小":
        st.session_state.selected_nums.update(n for n in nums if n <= 40)
    elif f_type == "质":
        primes = [2,3,5,7,11,13,17,19,23,29,31,37,41,43,47,53,59,61,67,71,73,79]
        st.session_state.selected_nums.update(primes)
    elif f_type == "合":
        primes = [2,3,5,7,11,13,17,19,23,29,31,37,41,43,47,53,59,61,67,71,73,79]
        st.session_state.selected_nums.update(n for n in nums if n not in primes and n != 1)

# 5.3 控制栏
ctrl_col1, ctrl_col2 = st.columns([1, 3])
with ctrl_col1:
    play_mode = st.selectbox("选择预演玩法", [f"选{i}" for i in range(1, 11)], index=2)
    play_n = int(play_mode.replace("选", ""))

with ctrl_col2:
    st.write("快捷条件过滤 (点击将清空当前选择):")
    btn_cols = st.columns(7)
    filters = ["奇", "偶", "大", "小", "质", "合", "清"]
    for i, f in enumerate(filters):
        if btn_cols[i].button(f, use_container_width=True, key=f"btn_{f}"):
            apply_filter(f)
            st.rerun() 

# 5.4 绘制 8x10 号码矩阵
with st.container(border=True):
    for row in range(8):
        cols = st.columns(10)
        for col in range(10):
            num = row * 10 + col + 1
            is_selected = num in st.session_state.selected_nums
            
            changed = cols[col].checkbox(f"{num:02d}", value=is_selected, key=f"num_{num}")
            
            if changed and not is_selected:
                st.session_state.selected_nums.add(num)
            elif not changed and is_selected:
                st.session_state.selected_nums.remove(num)

# 5.5 底部结算栏 (组合数学计算)
st.markdown("---")
selected_count = len(st.session_state.selected_nums)
bets = math.comb(selected_count, play_n) if selected_count >= play_n else 0
cost = bets * 2

result_col1, result_col2 = st.columns([3, 1])
with result_col1:
    if selected_count < play_n:
        st.warning(f"⚠️ 您当前选择了 {selected_count} 个号码，玩法为“{play_mode}”，号码数量不足，无法组合。")
    else:
        st.success(f"📌 **当前沙盘推演：** 已选 **{selected_count}** 个号码 ➡️ 生成组合 **{bets}** 注 ➡️ 模拟投入 **{cost}** 元。")

with result_col2:
    if st.button("🚀 根据选中号码重新生成分析图", type="primary", use_container_width=True):
        if selected_count == 0:
            st.toast("请至少选择一个号码！")
        else:
            st.toast("联调分析模块正在开发中，敬请期待！")