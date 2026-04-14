import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ==========================================
# 0. 页面基础配置
# ==========================================
st.set_page_config(page_title="高级彩票量化分析系统", layout="wide", initial_sidebar_state="expanded")
st.title("📊 快乐8 量化分析工作台 (本地回测版)")

# ==========================================
# 1. 数据引擎 (Mock Data Generator)
# ==========================================
@st.cache_data
def generate_fallback_data(issue_count=200):
    """生成高质量的模拟开奖数据用于前端研发"""
    records = []
    base_issue = 2024001
    for i in range(issue_count):
        # 快乐8：从1-80中随机抽取20个不重复的数字
        nums = sorted(np.random.choice(range(1, 81), 20, replace=False))
        str_nums = [f"{n:02d}" for n in nums]
        records.append({"期号": str(base_issue + i), "中奖号码": str_nums})
    return pd.DataFrame(records)

# 加载200期模拟数据
df = generate_fallback_data(200)

# ==========================================
# 2. 核心量化算法库
# ==========================================
def calc_advanced_metrics(df, target_num):
    """计算一阶遗漏、二阶遗漏与大小奇偶属性"""
    
    # 2.1 一阶遗漏 (Omission)
    omissions = []
    current_miss = 0
    for nums in df['中奖号码']:
        if target_num in nums:
            current_miss = 0
        else:
            current_miss += 1
        omissions.append(current_miss)
    df['遗漏值'] = omissions
    
    # 2.2 二阶遗漏 (Second-Order Omission) - 核心难点！
    # 逻辑：当前这个【遗漏值】上次出现距今隔了多少期？
    second_order = []
    last_seen_dict = {} # 记录每个遗漏值最后一次出现的索引(期数)
    
    for i, val in enumerate(omissions):
        if val in last_seen_dict:
            # 当前期数 - 上次出现这个遗漏值的期数
            so_val = i - last_seen_dict[val]
        else:
            # 如果这个遗漏值是历史第一次出现，二阶遗漏记为 0 或者当前期数
            so_val = 0 
        second_order.append(so_val)
        last_seen_dict[val] = i # 更新该遗漏值最后出现的位置
        
    df['二阶遗漏'] = second_order
    
    # 2.3 移动平均线 (MA5 / MA10)
    df['MA5'] = df['遗漏值'].rolling(window=5, min_periods=1).mean()
    df['MA10'] = df['遗漏值'].rolling(window=10, min_periods=1).mean()
    
    # 2.4 基础属性判定 (奇偶、大小)
    target_int = int(target_num)
    attr_parity = "奇数" if target_int % 2 != 0 else "偶数"
    attr_size = "小数" if target_int <= 40 else "大数"
    
    return df, attr_parity, attr_size

# ==========================================
# 3. 前端 UI 与交互控制 (Sidebar)
# ==========================================
st.sidebar.markdown("### 🎛️ 算法参数面板")
target_num = st.sidebar.selectbox("🎯 选择追踪号码", [f"{i:02d}" for i in range(1, 81)], index=7) # 默认选08

# 运行算法计算当前号码的完整数据
df_calc, attr_parity, attr_size = calc_advanced_metrics(df.copy(), target_num)

st.sidebar.markdown("---")
st.sidebar.markdown(f"**号码属性：** `{attr_parity}` | `{attr_size}`")

# 过滤器开关 (模拟复杂软件的筛选逻辑)
show_second_order = st.sidebar.checkbox("👁️ 显示二阶遗漏线", value=True)
show_ma10 = st.sidebar.checkbox("👁️ 显示10期均线 (MA10)", value=False)

# ==========================================
# 4. 图表渲染引擎 (Plotly 高级定制)
# ==========================================
# 顶部指标卡片
col1, col2, col3, col4 = st.columns(4)
current_miss = df_calc['遗漏值'].iloc[-1]
max_miss = df_calc['遗漏值'].max()
current_so = df_calc['二阶遗漏'].iloc[-1]

col1.metric(label=f"[{target_num}] 当前遗漏", value=current_miss)
col2.metric(label="历史最大遗漏", value=max_miss)
col3.metric(label="当前二阶遗漏", value=current_so, help="该遗漏值距离上次出现间隔的期数")
col4.metric(label="5期均值趋向", value=round(df_calc['MA5'].iloc[-1], 2))

st.markdown("---")

# 构建专业双层金融图表
fig = make_subplots(
    rows=2, cols=1, 
    shared_xaxes=True, 
    vertical_spacing=0.03, 
    row_heights=[0.65, 0.35], # 上下高度比
    subplot_titles=(f"号码 {target_num} 基础遗漏走势", "量能与二阶形态分析")
)

# 【上层】遗漏走势图
fig.add_trace(go.Scatter(
    x=df_calc['期号'], y=df_calc['遗漏值'], 
    mode='lines+markers', name='一阶遗漏', 
    line=dict(color='#ef5350', width=2),
    marker=dict(size=4)
), row=1, col=1)

fig.add_trace(go.Scatter(
    x=df_calc['期号'], y=df_calc['MA5'], 
    mode='lines', name='MA5 (黄线)', 
    line=dict(color='#ffee58', width=1.5, dash='solid')
), row=1, col=1)

if show_ma10:
    fig.add_trace(go.Scatter(
        x=df_calc['期号'], y=df_calc['MA10'], 
        mode='lines', name='MA10 (紫线)', 
        line=dict(color='#ab47bc', width=1.5, dash='dot')
    ), row=1, col=1)

# 【下层】MACD红绿柱 & 二阶遗漏
df_calc['动能MACD'] = df_calc['遗漏值'] - df_calc['MA5']
colors = ['#ef5350' if val > 0 else '#26a69a' for val in df_calc['动能MACD']]

fig.add_trace(go.Bar(
    x=df_calc['期号'], y=df_calc['动能MACD'], 
    marker_color=colors, name='多空动能',
    opacity=0.8
), row=2, col=1)

if show_second_order:
    fig.add_trace(go.Scatter(
        x=df_calc['期号'], y=df_calc['二阶遗漏'], 
        mode='lines', name='二阶遗漏', 
        line=dict(color='#29b6f6', width=1.5),
        yaxis='y3' # 绑定到右侧Y轴
    ), row=2, col=1)

# 【核心排版】暗黑专业风格定制
fig.update_layout(
    height=650, 
    paper_bgcolor="#121212", 
    plot_bgcolor="#1e1e1e", 
    font=dict(color="#e0e0e0"),
    hovermode="x unified", # 鼠标悬停时显示一条竖线上的所有数据！
    margin=dict(l=10, r=10, t=40, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

fig.update_xaxes(showgrid=True, gridcolor='#333333', zeroline=False)
fig.update_yaxes(showgrid=True, gridcolor='#333333', zeroline=False, row=1, col=1)
fig.update_yaxes(title_text="MACD动能", showgrid=True, gridcolor='#333333', zeroline=True, zerolinecolor='#666666', row=2, col=1)

st.plotly_chart(fig, use_container_width=True)

# 底部数据表
with st.expander("🛠️ 查看底层运算明细表"):
    st.dataframe(df_calc[['期号', '遗漏值', '二阶遗漏', 'MA5', 'MA10', '动能MACD']].iloc[::-1], use_container_width=True)