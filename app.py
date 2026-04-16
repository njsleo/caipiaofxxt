import streamlit as st
import pandas as pd
import requests
import random
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ==========================================
# 0. 页面基础配置与 CSS 极限微雕
# ==========================================
st.set_page_config(page_title="快乐8 专业量化终端", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    .block-container { padding-top: 1rem; padding-bottom: 1rem; max-width: 98%; }
    header {visibility: hidden;}
    div[data-testid="column"] { padding: 0 1px !important; }
    div[data-testid="stVerticalBlock"] { gap: 0.1rem !important; }
    div[data-testid="stButton"] button p, div[data-testid="stDownloadButton"] button p { white-space: nowrap !important; margin: 0 !important; font-size: 11px !important; }
    
    div[data-testid="stButton"] button {
        width: 26px !important; height: 26px !important; min-height: 26px !important;
        padding: 0 !important; border-radius: 50% !important; margin: 0 auto;
        transition: all 0.1s; box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    
    /* 保护策略面板的长文本功能按钮与导出按钮 */
    div[data-testid="stButton"] button:has(p:contains("图")),
    div[data-testid="stButton"] button:has(p:contains("退")),
    div[data-testid="stButton"] button:has(p:contains("大于")),
    div[data-testid="stButton"] button:has(p:contains("默认")),
    div[data-testid="stButton"] button:has(p:contains("遗漏")),
    div[data-testid="stButton"] button:has(p:contains("冷热")),
    div[data-testid="stButton"] button:has(p:contains("单选")),
    div[data-testid="stButton"] button:has(p:contains("多选")),
    div[data-testid="stButton"] button:has(p:contains("码")),
    div[data-testid="stButton"] button:has(p:contains("推荐")),
    div[data-testid="stButton"] button:has(p:contains("自选")),
    div[data-testid="stButton"] button:has(p:contains("定义")),
    div[data-testid="stButton"] button:has(p:contains("战法")),
    div[data-testid="stButton"] button:has(p:contains("向上")),
    div[data-testid="stButton"] button:has(p:contains("诊断当前")),
    div[data-testid="stButton"] button:has(p:contains("智能组号")),
    div[data-testid="stButton"] button:has(p:contains("演化学习")),
    div[data-testid="stButton"] button:has(p:contains("🔥")),
    div[data-testid="stDownloadButton"] button {
        width: 100% !important; border-radius: 4px !important; height: 28px !important; min-height: 28px !important;
    }
    
    div[data-testid="stButton"] button:has(p:contains("📈")) {
        background-color: transparent !important; border: none !important; color: #888 !important; box-shadow: none !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. 密钥、数据引擎与 DeepSeek 接口
# ==========================================
try:
    mxnzp = st.secrets.get("mxnzp_api", {})
    APP_ID = mxnzp.get("app_id", "")
    APP_SECRET = mxnzp.get("app_secret", "")
    if not APP_ID or not APP_SECRET:
        st.error("❌ API 密钥未配置。请检查 Secrets。")
        st.stop()
        
    DS_API_KEY = st.secrets.get("deepseek", {}).get("api_key", "")
except Exception as e:
    st.error(f"❌ 配置文件解析错误: {e}")
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

def ask_deepseek(prompt_text):
    if not DS_API_KEY: return "❌ 未检测到 DeepSeek API Key，请在 secrets 中配置 [deepseek] api_key。"
    url = "https://api.deepseek.com/chat/completions"
    headers = {"Authorization": f"Bearer {DS_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是一个具备极强模式识别能力的顶级金融量化分析师兼大模型AI。请使用冷峻、专业的华尔街量化投研报告风格回答。绝对禁止使用任何 Emoji 表情符号。绝对禁止使用星号(*)对文字或号码进行加粗。请保持最纯净的文本排版，以便用户直接复制导出。"},
            {"role": "user", "content": prompt_text}
        ]
    }
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=60)
        res.raise_for_status()
        return res.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"AI 智算中心请求超时或失败: {str(e)}"

with st.spinner("正在连接数据中心..."):
    df_raw, status = fetch_data(50)

if df_raw.empty:
    st.error(f"数据拉取失败: {status}")
    st.stop()

# ==========================================
# 2. 状态管理与核心算法
# ==========================================
if 'selected_nums' not in st.session_state: st.session_state.selected_nums = set([2, 8, 12]) 
if 'hit_condition' not in st.session_state: st.session_state.hit_condition = 2
if 'rand_count' not in st.session_state: st.session_state.rand_count = 10
if 'ind_rule' not in st.session_state: st.session_state.ind_rule = "3码>=2"
if 'scan_results' not in st.session_state: st.session_state.scan_results = []
if 'ai_report_cache' not in st.session_state: st.session_state.ai_report_cache = ""

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
    records = []; curr_val = 1000.0 
    for idx, row in df.iterrows():
        hits = sum(1 for n in selected_nums if n in row['中奖号码'])
        is_hit = hits >= min_hits
        open_val = curr_val
        if is_hit:
            close_val = open_val + 15; high_val = close_val + 2; low_val = open_val - 1
        else:
            close_val = open_val - 4; high_val = open_val + 1; low_val = close_val - 2
        curr_val = close_val
        records.append({"期号": row['期号'], "Open": open_val, "High": high_val, "Low": low_val, "Close": close_val})
        
    df_k = pd.DataFrame(records)
    df_k['MA5'] = df_k['Close'].rolling(window=5, min_periods=1).mean()
    df_k['MA10'] = df_k['Close'].rolling(window=10, min_periods=1).mean()
    df_k['MA20'] = df_k['Close'].rolling(window=20, min_periods=1).mean()
    df_k['MACD'] = df_k['Close'].ewm(span=12, adjust=False).mean() - df_k['Close'].ewm(span=26, adjust=False).mean()
    df_k['DEA'] = df_k['MACD'].ewm(span=9, adjust=False).mean()
    df_k['MACD_HIST'] = df_k['MACD'] - df_k['DEA']
    return df_k

def scan_top_trends(df, rule_str, top_n=10):
    try:
        n_nums = int(rule_str.split("码")[0]); h_cond = int(rule_str[-1])
    except:
        n_nums = 3; h_cond = 2
    results = []
    for _ in range(200):
        combo = sorted(random.sample(range(1, 81), n_nums))
        df_k = generate_strategy_kline(df, combo, h_cond)
        score = (df_k['Close'].iloc[-1] - df_k['MA20'].iloc[-1]) + (df_k['MACD_HIST'].iloc[-1] * 2) 
        results.append((score, combo, h_cond))
    results.sort(key=lambda x: x[0], reverse=True)
    return results[:top_n]

def get_hot_numbers_for_ai(df):
    hot_list = []
    for n in range(1, 81):
        df_k = generate_strategy_kline(df, [n], 1)
        score = (df_k['Close'].iloc[-1] - df_k['MA20'].iloc[-1]) + (df_k['MACD_HIST'].iloc[-1] * 2)
        hot_list.append((n, score))
    hot_list.sort(key=lambda x: x[1], reverse=True)
    return sorted([x[0] for x in hot_list[:20]])

# 🤖 提取历史全量特征用于 AI 演化学习
def extract_historical_context(df, limit=30):
    context_str = ""
    for idx, row in df.tail(limit).iterrows():
        nums = row['中奖号码']
        odd_count = sum(1 for n in nums if n % 2 != 0)
        big_count = sum(1 for n in nums if n > 40)
        total_sum = sum(nums)
        context_str += f"[{row['期号']}] 和值:{total_sum} 奇偶比:{odd_count}/{20-odd_count} 大小比:{big_count}/{20-big_count} 号码序列:{nums}\n"
    return context_str

# ==========================================
# 3. 核心布局：左右分栏
# ==========================================
left_col, right_col = st.columns([7.2, 2.8], gap="large")

with left_col:
    num_str = " ".join([f"{n:02d}" for n in sorted(list(st.session_state.selected_nums))])
    st.markdown(f"<h4 style='color:#FFF; margin-bottom:0;'>追踪阵型: <span style='color:#FF4B4B;'>[{num_str}]</span> | 爆发条件: 命中 ≥ <span style='color:#FF4B4B;'>{st.session_state.hit_condition}</span></h4>", unsafe_allow_html=True)
    
    if len(st.session_state.selected_nums) == 0:
        st.info("👈 请在右侧面板点选号码。")
    else:
        df_kline = generate_strategy_kline(df_raw, st.session_state.selected_nums, st.session_state.hit_condition)
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
        
        fig.add_trace(go.Candlestick(x=df_kline['期号'], open=df_kline['Open'], high=df_kline['High'], low=df_kline['Low'], close=df_kline['Close'], increasing_line_color='#FF4B4B', decreasing_line_color='#00D166', name='资金曲线'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_kline['期号'], y=df_kline['MA5'], mode='lines', name='MA5', line=dict(color='#F2B134', width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_kline['期号'], y=df_kline['MA10'], mode='lines', name='MA10', line=dict(color='#00B4D8', width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_kline['期号'], y=df_kline['MA20'], mode='lines', name='MA20', line=dict(color='#00D166', width=1)), row=1, col=1)

        macd_colors = ['#FF4B4B' if val > 0 else '#00D166' for val in df_kline['MACD_HIST']]
        fig.add_trace(go.Bar(x=df_kline['期号'], y=df_kline['MACD_HIST'], marker_color=macd_colors, name='MACD量能'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df_kline['期号'], y=df_kline['MACD'], mode='lines', name='DIF', line=dict(color='#FFF', width=1)), row=2, col=1)

        fig.update_layout(height=480, template="plotly_dark", hovermode="x unified", margin=dict(l=0, r=0, t=10, b=0), xaxis_rangeslider_visible=False)
        fig.update_yaxes(gridcolor='#333333')
        st.plotly_chart(fig, use_container_width=True)

        # 🤖 DeepSeek 智能组号与感知学习中心
        with st.expander("🤖 DeepSeek 智算中心 - 感知演化与智能决策", expanded=True):
            ai_c1, ai_c2, ai_c3 = st.columns([1, 1, 1.2]) # 分配三个按钮
            
            if ai_c1.button("📉 诊断当前阵型", use_container_width=True):
                latest = df_kline.iloc[-1]
                p_close = round(latest['Close'], 2); p_ma5 = round(latest['MA5'], 2); p_ma20 = round(latest['MA20'], 2); p_macd = round(latest['MACD_HIST'], 2)
                prompt = f"分析标的：[{num_str}]。条件：≥{st.session_state.hit_condition}。当前收盘净值 {p_close}，MA20(牛熊线) {p_ma20}，MACD动能柱 {p_macd}。请给出极简的趋势判定和操作建议。"
                with st.spinner("AI 正在解析当前均线与动能..."):
                    st.session_state.ai_report_cache = ask_deepseek(prompt)
            
            if ai_c2.button("🔮 算力智能组号", use_container_width=True):
                with st.spinner("后台算力正在扫描底层动能模型..."):
                    hot_20 = get_hot_numbers_for_ai(df_raw)
                    hot_str = " ".join([f"{n:02d}" for n in hot_20])
                    prompt = f"系统算出的 Top 20 强势核心号码为：[{hot_str}]。\n请严格执行：\n1. 简要分析这批号码特征。\n2. 利用这20个号码，依次推荐【选10】到【选2】组合（每种玩法严格提供 3 注）。\n3. 选出一组【终极最优选组合】。\n警告：全篇必须是纯文本，绝对禁止加星号(*)！"
                    st.session_state.ai_report_cache = ask_deepseek(prompt)
            
            # 💡 【新增功能】AI 自主感知演化学习
            if ai_c3.button("🧠 启动 AI 深度演化学习", type="primary", use_container_width=True):
                with st.spinner("系统正在将最近 30 期海量数据压入大模型进行 In-Context 感知学习..."):
                    hist_data_str = extract_historical_context(df_raw, 30)
                    prompt = f"""
                    你现在进入【深度演化学习模式】。以下是目标彩种最近 30 期的完整底层开奖轨迹数据（包含和值、奇偶比、大小比及号码矩阵）：
                    \n{hist_data_str}\n
                    请你作为具备自我演化能力的 AI，完成以下三大任务：
                    1. 【特征感知】：抛弃传统的频率统计，通过阅读上述长序列数据，感知其隐含的非线性趋势（例如：连号转移规律、冷热极限反转点、跨区漂移特征）。
                    2. 【理论建立】：结合你的感知，强行总结出一套只属于针对下一期开奖的【AI 独家感知理论】（100字以内说明逻辑）。
                    3. 【演化预测】：基于你刚刚建立的这套感知理论，直接推演并精准给出下一期极大概率会爆发的 10 个独立号码（作为一注超强潜力池）。
                    警告：全篇必须是极其干净的纯文本！绝对禁止在号码或文字两边加星号(*)和表情符号！
                    """
                    st.session_state.ai_report_cache = ask_deepseek(prompt)

            if st.session_state.ai_report_cache:
                st.markdown(f"<div style='background-color:#1E1E1E; padding:15px; border-radius:8px; border-left:4px solid #FF4B4B; color:#E0E0E0; font-size: 14px; white-space: pre-wrap;'>{st.session_state.ai_report_cache}</div>", unsafe_allow_html=True)
                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                st.download_button(label="💾 下载纯净版 AI 分析报告", data=st.session_state.ai_report_cache, file_name="DeepSeek_量化智能决策.txt", mime="text/plain", use_container_width=True)

with right_col:
    top_c1, top_c2, top_c3 = st.columns([3, 4, 2])
    top_c1.selectbox("彩种", ["快乐8", "双色球"], label_visibility="collapsed")
    top_c2.markdown(f"<div style='line-height: 2; color:#888; font-size:12px; text-align:center;'>第{df_raw.iloc[-1]['期号']}期 ↻</div>", unsafe_allow_html=True)
    top_c3.button("退出", use_container_width=True)

    html_balls = "".join([f"<div style='display:inline-block; width:22px; height:22px; line-height:22px; text-align:center; background-color:#FF4B4B; color:white; border-radius:50%; margin:1px 1px; font-size:10px; font-weight:bold;'>{n:02d}</div>" for n in df_raw.iloc[-1]['中奖号码']])
    st.markdown(f"<div style='margin: 5px 0 10px 0;'>{html_balls} 〉</div>", unsafe_allow_html=True)
    
    tabs = st.tabs(["号码", "走势图", "指标", "分区", "头尾"])
    
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
        f_cols = st.columns(10)
        filters = ["奇", "偶", "大", "小", "质", "合", "清"]
        for i, f in enumerate(filters):
            if f_cols[i].button(f, key=f"bf_{f}"):
                apply_filter(f)
                st.rerun()
                
        if f_cols[7].button("随", key="bf_rand", type="primary"):
            st.session_state.selected_nums = set(random.sample(range(1, 81), st.session_state.rand_count))
            st.rerun()
        if f_cols[8].button(str(st.session_state.rand_count), key="bf_rcnt"):
            st.session_state.rand_count = {1:3, 3:5, 5:10, 10:20, 20:1}.get(st.session_state.rand_count, 10)
            st.rerun()
            
        export_text = " ".join([f"{n:02d}" for n in sorted(list(st.session_state.selected_nums))])
        with f_cols[9]:
            st.download_button(label="导出", data=export_text, file_name="快乐8_手选组合.txt", mime="text/plain", key="bf_out")

    with tabs[2]:
        ic1, ic2, ic3 = st.columns(3)
        ic1.button("推荐", type="primary", use_container_width=True)
        ic2.button("自选", use_container_width=True)
        ic3.button("自定义", use_container_width=True)
        
        st.markdown("<div style='margin-top:5px; margin-bottom:5px; font-size:12px; color:#aaa; font-weight:bold;'>共振战法选择</div>", unsafe_allow_html=True)
        ic4, ic5 = st.columns(2)
        ic4.button("共振战法", use_container_width=True)
        ic5.button("趋势向上", type="primary", use_container_width=True)
        
        st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True)
        rules = ["2码=0", "2码>=1", "3码=0", "3码>=1", "3码>=2", "4码>=2", "5码>=2", "6码>=2", "6码>=3", "7码>=3", "8码>=3", "10码>=4"]
        rule_cols = st.columns(4)
        for i, rule in enumerate(rules):
            b_type = "primary" if st.session_state.ind_rule == rule else "secondary"
            if rule_cols[i%4].button(rule, type=b_type, key=f"ir_{rule}"):
                st.session_state.ind_rule = rule
                with st.spinner(f"正在扫描 200 组底层数据..."):
                    st.session_state.scan_results = scan_top_trends(df_raw, rule, top_n=10)
                st.rerun()
                
        if not st.session_state.scan_results:
            st.session_state.scan_results = scan_top_trends(df_raw, st.session_state.ind_rule, top_n=10)

        curr_rule = st.session_state.ind_rule
        st.markdown(f"<hr style='margin:10px 0; border-color:#333;'><div style='font-size:12px; color:#00D166; margin-bottom:5px;'>✓ 已为您提取出 <b>[{curr_rule}]</b> 趋势最强的 Top 10 组：</div>", unsafe_allow_html=True)
        
        res_cols = st.columns(2)
        for idx, (score, combo, h_cond) in enumerate(st.session_state.scan_results):
            set_str = " ".join([f"{n:02d}" for n in combo])
            icon = "🔥" if idx < 3 else "🚀"
            if res_cols[idx % 2].button(f"{icon} {set_str}", key=f"res_{idx}"):
                st.session_state.selected_nums = set(combo)
                st.session_state.hit_condition = h_cond
                st.rerun()

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        scan_export_text = f"【共振战法：{curr_rule}】均线多头与MACD底背离 最强 Top 10 组合：\n\n"
        for idx, (score, combo, h_cond) in enumerate(st.session_state.scan_results):
            scan_export_text += f"Top {idx+1}: " + " ".join([f"{n:02d}" for n in combo]) + "\n"
        st.download_button(label="💾 一键导出这 10 组指标精选号码", data=scan_export_text, file_name=f"指标精选_{curr_rule}.txt", mime="text/plain", use_container_width=True, type="secondary")

    st.markdown("<hr style='margin: 8px 0; border-color: #333;'>", unsafe_allow_html=True)
    cond_c1, cond_c2, cond_c3 = st.columns([3, 4, 3])
    cond_c2.selectbox("逻辑", ["大于等于 ▼", "等于 ▼", "小于等于 ▼"], label_visibility="collapsed")
    
    num_cols = st.columns([1.5, 1, 1, 1, 1, 1, 1, 1, 1.5])
    for i in range(7):
        ctype = "primary" if st.session_state.hit_condition == i else "secondary"
        if num_cols[i+1].button(str(i), type=ctype, key=f"cond_{i}"):
            st.session_state.hit_condition = i
            st.rerun() 

    st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True)
    b1, b2, b3 = st.columns([1, 1, 1.1]) 
    b1.button("单码出图", use_container_width=True)
    b2.button("合并出图", use_container_width=True)
    b3.button("选中条件", use_container_width=True)