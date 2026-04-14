import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="高级彩票分析", layout="wide")
st.title("📈 快乐8 真实遗漏值与技术分析")

# 1. 获取真实数据（带错误提示版）
@st.cache_data(ttl=3600)
def fetch_real_data(issue_count=100):
    url = "http://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice"
    params = {"name": "kl8", "issueCount": issue_count}
    # 强化伪装
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", 
        "Accept": "application/json", 
        "Referer": "http://www.cwl.gov.cn/"
    }
    try:
        res = requests.get(url, params=params, headers=headers, timeout=5)
        if res.status_code != 200:
            return pd.DataFrame(), f"服务器拒绝访问，状态码: {res.status_code}"
            
        data = res.json()
        records = [{"期号": item["code"], "中奖号码": item["red"].split(',')} for item in data.get("result", [])]
        return pd.DataFrame(records).iloc[::-1].reset_index(drop=True), "success"
    except Exception as e:
        return pd.DataFrame(), str(e)

# 备用方案：生成高仿模拟数据
def generate_fallback_data(issue_count=100):
    records = []
    base_issue = 2024001
    for i in range(issue_count):
        # 随机生成20个1-80的不重复数字，模拟快乐8开奖
        nums = sorted(np.random.choice(range(1, 81), 20, replace=False))
        str_nums = [f"{n:02d}" for n in nums]
        records.append({"期号": str(base_issue + i), "中奖号码": str_nums})
    return pd.DataFrame(records)

# 尝试获取数据
with st.spinner("正在尝试连接福彩官网数据库..."):
    df, status = fetch_real_data(100)

# 如果官方数据获取失败，启动备用方案
if df.empty:
    st.warning(f"⚠️ 无法从福彩官网获取实时数据 (原因: {status})。这通常是因为云服务器的海外IP被官网拦截。")
    st.info("🔄 已自动切换为【本地算法回测模式】（使用模拟结构数据），以便您继续测试图表与分析功能。")
    df = generate_fallback_data(100)

# 2. 核心算法：计算遗漏值
def calculate_omission(df, target_num):
    omission_list = []
    current_miss = 0
    for nums in df['中奖号码']:
        if target_num in nums:
            current_miss = 0
        else:
            current_miss += 1
        omission_list.append(current_miss)
    return omission_list

# 渲染控制面板和图表
st.sidebar.header("🎛️ 控制面板")
target = st.sidebar.selectbox("选择深度分析号码", [f"{i:02d}" for i in range(1, 81)], index=0)

df['遗漏值'] = calculate_omission(df, target)
df['MA5'] = df['遗漏值'].rolling(window=5).mean()

st.subheader(f"号码 {target} - 遗漏趋势与量能分析")

fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
fig.add_trace(go.Scatter(x=df['期号'], y=df['遗漏值'], mode='lines+markers', name='遗漏值', line=dict(color='red')), row=1, col=1)
fig.add_trace(go.Scatter(x=df['期号'], y=df['MA5'], mode='lines', name='5期均线', line=dict(color='yellow')), row=1, col=1)

df['动能'] = df['遗漏值'] - df['MA5']
colors = ['red' if val > 0 else 'green' for val in df['动能']]
fig.add_trace(go.Bar(x=df['期号'], y=df['动能'], marker_color=colors, name='多空动能'), row=2, col=1)

fig.update_layout(
    height=600, 
    paper_bgcolor="#1E1E1E", plot_bgcolor="#1E1E1E", font=dict(color="white"),
    hovermode="x unified", margin=dict(l=20, r=20, t=20, b=20)
)
fig.update_xaxes(showgrid=True, gridcolor='#333333')
fig.update_yaxes(showgrid=True, gridcolor='#333333')

st.plotly_chart(fig, use_container_width=True)

with st.expander("查看底层计算数据"):
    st.dataframe(df[['期号', '中奖号码', '遗漏值', 'MA5', '动能']].tail(10))