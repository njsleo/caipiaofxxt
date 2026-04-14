import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="高级彩票分析", layout="wide")
st.title("📈 快乐8 真实遗漏值与技术分析")

# 1. 获取真实数据
@st.cache_data(ttl=3600)
def fetch_real_data(issue_count=100):
    url = "http://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice"
    params = {"name": "kl8", "issueCount": issue_count}
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json", "Referer": "http://www.cwl.gov.cn/"}
    try:
        res = requests.get(url, params=params, headers=headers, timeout=10).json()
        records = [{"期号": item["code"], "中奖号码": item["red"].split(',')} for item in res.get("result", [])]
        # 官方数据是倒序的（最新在最前面），我们需要按照时间正序排列来画走势图
        return pd.DataFrame(records).iloc[::-1].reset_index(drop=True)
    except Exception:
        return pd.DataFrame()

df = fetch_real_data(100) # 获取100期真实数据

# 2. 核心算法：计算真实遗漏值
def calculate_omission(df, target_num):
    """计算某个具体号码的遗漏走势"""
    omission_list = []
    current_miss = 0
    
    for nums in df['中奖号码']:
        if target_num in nums:
            current_miss = 0 # 如果中了，遗漏清零
        else:
            current_miss += 1 # 如果没中，遗漏+1
        omission_list.append(current_miss)
        
    return omission_list

if not df.empty:
    st.sidebar.header("🎛️ 控制面板")
    # 让用户选择一个号码进行深度分析
    target = st.sidebar.selectbox("选择深度分析号码", [f"{i:02d}" for i in range(1, 81)], index=0)
    
    # 计算该号码的遗漏数据
    df['遗漏值'] = calculate_omission(df, target)
    
    # 计算简单的5期均线 (MA5)
    df['MA5'] = df['遗漏值'].rolling(window=5).mean()

    # 3. 绘制专业双层图表 (类似图一的上下结构)
    st.subheader(f"号码 {target} - 遗漏趋势与量能分析")
    
    # 创建包含两行的子图，比例为 7:3
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])

    # 上层：遗漏走势与均线
    fig.add_trace(go.Scatter(x=df['期号'], y=df['遗漏值'], mode='lines+markers', name='遗漏值', line=dict(color='red')), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['期号'], y=df['MA5'], mode='lines', name='5期均线', line=dict(color='yellow')), row=1, col=1)

    # 下层：模拟 MACD 的动能柱 (这里我们简单用 遗漏值-均线 来模拟红绿柱)
    df['动能'] = df['遗漏值'] - df['MA5']
    colors = ['red' if val > 0 else 'green' for val in df['动能']] # 大于0红色，小于0绿色
    fig.add_trace(go.Bar(x=df['期号'], y=df['动能'], marker_color=colors, name='多空动能'), row=2, col=1)

    # 图表样式微调，模仿暗黑专业风格
    fig.update_layout(
        height=600, 
        paper_bgcolor="#1E1E1E", plot_bgcolor="#1E1E1E", font=dict(color="white"),
        hovermode="x unified", margin=dict(l=20, r=20, t=20, b=20)
    )
    fig.update_xaxes(showgrid=True, gridcolor='#333333')
    fig.update_yaxes(showgrid=True, gridcolor='#333333')

    st.plotly_chart(fig, use_container_width=True)
    
    # 展示底层数据框，方便核对
    with st.expander("查看底层计算数据"):
        st.dataframe(df[['期号', '中奖号码', '遗漏值', 'MA5', '动能']].tail(10))