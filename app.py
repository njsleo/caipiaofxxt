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
    import streamlit as st
import math

st.markdown("---")
st.subheader("🎛️ 智能选号与奖金计算器")

# ==========================================
# 1. 初始化状态 (大脑记忆区)
# ==========================================
if 'selected_nums' not in st.session_state:
    st.session_state.selected_nums = set()

# 快捷操作回调函数
def apply_filter(filter_type):
    st.session_state.selected_nums.clear()
    nums = range(1, 81)
    if filter_type == "奇":
        st.session_state.selected_nums.update(n for n in nums if n % 2 != 0)
    elif filter_type == "偶":
        st.session_state.selected_nums.update(n for n in nums if n % 2 == 0)
    elif filter_type == "大":
        st.session_state.selected_nums.update(n for n in nums if n > 40)
    elif filter_type == "小":
        st.session_state.selected_nums.update(n for n in nums if n <= 40)
    elif filter_type == "质":
        primes = [2,3,5,7,11,13,17,19,23,29,31,37,41,43,47,53,59,61,67,71,73,79]
        st.session_state.selected_nums.update(primes)
    elif filter_type == "合":
        primes = [2,3,5,7,11,13,17,19,23,29,31,37,41,43,47,53,59,61,67,71,73,79]
        st.session_state.selected_nums.update(n for n in nums if n not in primes and n != 1)
    elif filter_type == "清":
        pass # 前面已经 clear() 了

# ==========================================
# 2. 绘制 8x10 选号矩阵
# ==========================================
st.write("**号码矩阵**")
# 快捷按钮排排坐
f_cols = st.columns(8)
filters = ["奇", "偶", "大", "小", "质", "合", "清"]
for i, f in enumerate(filters):
    if f_cols[i].button(f, use_container_width=True, key=f"btn_{f}"):
        apply_filter(f)

st.write("") # 留点空隙
container = st.container()
with container:
    for row in range(8):
        cols = st.columns(10)
        for col in range(10):
            num = row * 10 + col + 1
            is_selected = num in st.session_state.selected_nums
            
            # 用 checkbox 模拟高密度按钮
            changed = cols[col].checkbox(f"{num:02d}", value=is_selected, key=f"chk_{num}")
            
            # 同步状态
            if changed and num not in st.session_state.selected_nums:
                st.session_state.selected_nums.add(num)
            elif not changed and num in st.session_state.selected_nums:
                st.session_state.selected_nums.remove(num)

# ==========================================
# 3. 奖金计算与出图控制区
# ==========================================
st.markdown("---")
c1, c2, c3 = st.columns([1, 2, 1])

# 玩法选择
play_mode = c1.selectbox("选择玩法", [f"选{i}" for i in range(1, 11)], index=2) # 默认选3
play_n = int(play_mode.replace("选", ""))

selected_count = len(st.session_state.selected_nums)

# 计算注数 (组合数学 C(n, k))
if selected_count >= play_n:
    bets = math.comb(selected_count, play_n)
else:
    bets = 0

cost = bets * 2

c2.markdown(f"<h4 style='text-align: center;'>已选 {selected_count} 个号 | 共 {bets} 注 | 投入 {cost} 元</h4>", unsafe_allow_html=True)

if c3.button("🚀 选中条件出图", type="primary", use_container_width=True):
    if selected_count == 0:
        st.warning("请先在上方选择号码！")
    elif selected_count > 10:
        st.warning("为了图表显示清晰，建议同时对比的号码不超过 10 个哦！")
    else:
        st.success(f"正在生成 {sorted(list(st.session_state.selected_nums))} 的专属对比走势图...")
        
        # === 动态生成多线对比图 ===
        fig_multi = go.Figure()
        
        # 遍历所有选中的号码
        for num in sorted(list(st.session_state.selected_nums)):
            num_str = f"{num:02d}"
            omissions = []
            curr = 0
            
            # 为每个选中的号码计算一阶遗漏
            # 注意：这里的 df_raw 是最上面 API 获取到的原始数据
            for row in df_raw['中奖号码']: 
                if num_str in row:
                    curr = 0
                else:
                    curr += 1
                omissions.append(curr)
            
            # 将该号码的折线加入图表
            fig_multi.add_trace(go.Scatter(
                x=df_raw['期号'], 
                y=omissions, 
                mode='lines+markers', 
                name=f'号码 {num_str}',
                marker=dict(size=6)
            ))

        # 设置图表样式
        fig_multi.update_layout(
            title="📊 选中号码遗漏走势对比 (谁在飙升，谁在触底？)",
            height=400,
            hovermode="x unified",
            margin=dict(l=10, r=10, t=40, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        fig_multi.update_xaxes(showgrid=False)
        fig_multi.update_yaxes(gridcolor='#333333')

        # 在页面最下方展示这个新图表
        st.plotly_chart(fig_multi, use_container_width=True)