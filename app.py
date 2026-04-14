import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ==========================================
# 0. 页面基础配置
# ==========================================
st.set_page_config(page_title="快乐8 高级量化分析平台", layout="wide")
st.title("📈 快乐8 实时量化分析工作台")

# ==========================================
# 1. 密钥读取 (Secrets 管理)
# ==========================================
try:
    # 尝试从 Streamlit Secrets 中读取密钥
    APP_ID = st.secrets["mxnzp_api"]["app_id"]
    APP_SECRET = st.secrets["mxnzp_api"]["app_secret"]
except Exception:
    st.error("❌ 未在 Secrets 中找到密钥！请确保您已在 streamlit.io 后台设置了 [mxnzp_api] 块。")
    st.info("设置格式参考：\n\n[mxnzp_api]\napp_id = \"您的ID\"\napp_secret = \"您的Secret\"")
    st.stop()

# ==========================================
# 2. 数据获取引擎 (API 连接)
# ==========================================
@st.cache_data(ttl=1800) # 缓存30分钟
def fetch_data(issue_count=50):
    url = "https://www.mxnzp.com/api/lottery/common/history"
    # 限制最大50期（免费接口限制）
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
            # 翻转为正序（时间从旧到新）以便画线
            return pd.DataFrame(records).iloc[::-1].reset_index(drop=True), "success"
        else:
            return pd.DataFrame(), res.get("msg", "未知错误")
    except Exception as e:
        return pd.DataFrame(), str(e)

# ==========================================
# 3. 核心算法库 (一阶/二阶遗漏)
# ==========================================
def run_analysis(df, target_num):
    # 3.1 计算一阶遗漏
    omissions = []
    curr = 0
    for row in df['中奖号码']:
        if target_num in row:
            curr = 0
        else:
            curr += 1
        omissions.append(curr)
    df['遗漏值'] = omissions
    
    # 3.2 计算二阶遗漏 (遗漏值间隔)
    so_list = []
    last_pos = {} # 记录每个遗漏值上次出现的索引
    for i, v in enumerate(omissions):
        if v in last_pos:
            so_list.append(i - last_pos[v])
        else:
            so_list.append(0)
        last_pos[v] = i
    df['二阶遗漏'] = so_list
    
    # 3.3 计算均线
    df['MA5'] = df['遗漏值'].rolling(window=5).mean()
    return df

# ==========================================
# 4. UI 渲染与逻辑控制
# ==========================================
# 4.1 数据拉取
with st.spinner("正在同步全网开奖数据..."):
    df_raw, status = fetch_data(50)

if df_raw.empty:
    st.error(f"数据加载失败: {status}")
    st.stop()

# 4.2 侧边栏控制
st.sidebar.header("🎯 号码追踪")
target = st.sidebar.selectbox("选择分析号码", [f"{i:02d}" for i in range(1, 81)], index=7)
st.sidebar.markdown("---")
st.sidebar.write("**算法说明：**")
st.sidebar.caption("一阶遗漏：该号码连续未开出的期数。")
st.sidebar.caption("二阶遗漏：当前遗漏值距离上次出现的时间跨度。")

# 4.3 运算分析
df_final = run_analysis(df_raw.copy(), target)

# 4.4 顶部指标
c1, c2, c3 = st.columns(3)
c1.metric("当前遗漏", df_final['遗漏值'].iloc[-1])
c2.metric("当前二阶遗漏", df_final['二阶遗漏'].iloc[-1])
c3.metric("5期平均遗漏", round(df_final['MA5'].iloc[-1], 2))

# 4.5 专业图表绘制
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.6, 0.4])

# 上层：一阶遗漏趋势
fig.add_trace(go.Scatter(x=df_final['期号'], y=df_final['遗漏值'], mode='lines+markers', name='一阶遗漏', line=dict(color='#FF4B4B', width=2)), row=1, col=1)
fig.add_trace(go.Scatter(x=df_final['期号'], y=df_final['MA5'], mode='lines', name='5期均线', line=dict(color='#F2B134', width=1, dash='dot')), row=1, col=1)

# 下层：二阶遗漏与动能
df_final['动能'] = df_final['遗漏值'] - df_final['MA5']
bar_colors = ['#FF4B4B' if x > 0 else '#00D166' for x in df_final['动能']]
fig.add_trace(go.Bar(x=df_final['期号'], y=df_final['动能'], name='量能脉冲', marker_color=bar_colors), row=2, col=1)
fig.add_trace(go.Scatter(x=df_final['期号'], y=df_final['二阶遗漏'], name='二阶走势', line=dict(color='#00B4D8', width=1.5)), row=2, col=1)

# 统一样式
fig.update_layout(height=600, template="plotly_dark", hovermode="x unified", margin=dict(l=10, r=10, t=30, b=10))
fig.update_xaxes(showgrid=False)
fig.update_yaxes(gridcolor='#333333')

st.plotly_chart(fig, use_container_width=True)

# 底层数据
with st.expander("查看原始数据明细"):
    st.dataframe(df_final[['期号', '中奖号码', '遗漏值', '二阶遗漏', 'MA5']].iloc[::-1], use_container_width=True)