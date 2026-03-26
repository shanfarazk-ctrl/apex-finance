import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from anthropic import Anthropic

st.set_page_config(
    page_title="Apex Finance",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded"
)

FMP_KEY = st.secrets.get("FMP_API_KEY", "")
AI_KEY  = st.secrets.get("ANTHROPIC_API_KEY", "")

BASE = "https://financialmodelingprep.com/stable"

def fmp(endpoint, params={}):
    try:
        params["apikey"] = FMP_KEY
        r = requests.get(f"{BASE}/{endpoint}", params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API Error: {e}")
        return []

@st.cache_data(ttl=3600)
def get_profile(symbol):
    data = fmp("profile", {"symbol": symbol})
    return data[0] if data else {}

@st.cache_data(ttl=300)
def get_quote(symbol):
    data = fmp("quote", {"symbol": symbol})
    return data[0] if data else {}

@st.cache_data(ttl=3600)
def get_income(symbol, period="annual"):
    return fmp("income-statement", {"symbol": symbol, "period": period, "limit": 5})

@st.cache_data(ttl=3600)
def get_balance(symbol):
    return fmp("balance-sheet-statement", {"symbol": symbol, "limit": 1})

@st.cache_data(ttl=3600)
def get_cashflow(symbol):
    return fmp("cash-flow-statement", {"symbol": symbol, "limit": 1})

@st.cache_data(ttl=3600)
def get_metrics(symbol):
    data = fmp("key-metrics", {"symbol": symbol, "limit": 1})
    return data[0] if data else {}

@st.cache_data(ttl=3600)
def get_ratios(symbol):
    data = fmp("ratios", {"symbol": symbol, "limit": 1})
    return data[0] if data else {}

@st.cache_data(ttl=300)
def search_symbol(query):
    return fmp("search", {"query": query, "limit": 8})

def calc_score(metrics, ratios):
    try:
        pe     = ratios.get("priceToEarningsRatio", 30)
        roe    = ratios.get("returnOnEquityRatio", 0.1) * 100
        margin = ratios.get("netProfitMargin", 0.1) * 100
        cr     = ratios.get("currentRatio", 1.5)
        de     = ratios.get("debtToEquityRatio", 1)

        growth        = min(100, max(0, 50 + metrics.get("revenueGrowth", 0) * 200))
        profitability = min(100, max(0, margin * 2 + roe * 0.4))
        liquidity     = min(100, max(0, cr * 30))
        leverage      = min(100, max(0, 80 - de * 15))
        valuation     = min(100, max(0, 80 - pe * 0.8))

        total = int(growth*0.25 + profitability*0.3 + liquidity*0.1 + leverage*0.15 + valuation*0.2)
        return {"total": total, "growth": int(growth), "profitability": int(profitability),
                "liquidity": int(liquidity), "leverage": int(leverage), "valuation": int(valuation)}
    except:
        return {"total": 50, "growth": 50, "profitability": 50,
                "liquidity": 50, "leverage": 50, "valuation": 50}

def get_rating(score):
    if score >= 75: return "Strong Buy", "🟢"
    if score >= 60: return "Buy", "🟡"
    if score >= 45: return "Hold", "🟠"
    return "Risky", "🔴"

st.markdown("""
<style>
    .main { background-color: #0a0e1a; }
    .block-container { padding: 1.5rem 2rem; }
    div[data-testid="stMetricValue"] { font-size: 1.4rem; font-weight: 700; }
    .stTabs [data-baseweb="tab"] { font-size: 13px; font-weight: 500; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## ◈ Apex Finance")
    st.markdown("---")

    query = st.text_input("🔍 Search Company", placeholder="e.g. Apple, TSLA")
    symbol = "AAPL"

    if query:
        results = search_symbol(query)
        if results:
            options = {f"{r['symbol']} — {r.get('name', r.get('companyName',''))}": r['symbol'] for r in results}
            choice = st.selectbox("Select", list(options.keys()))
            symbol = options[choice]
        else:
            st.warning("No results found")
    else:
        symbol = st.text_input("Or enter ticker directly", value="AAPL").upper()

    st.markdown("---")
    st.markdown("### 📌 Quick Picks")
    cols = st.columns(3)
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA"]
    for i, t in enumerate(tickers):
        if cols[i % 3].button(t, key=f"btn_{t}"):
            symbol = t

    st.markdown("---")
    period = st.radio("Statement Period", ["annual", "quarter"], horizontal=True)

    st.markdown("---")
    st.markdown("### 👥 Peer Analysis")
    peers_input = st.text_input("Add peers (comma separated)", "MSFT,GOOGL,AMZN")
    peers = [p.strip().upper() for p in peers_input.split(",") if p.strip()]

    st.markdown("---")
    st.caption("◈ Apex Intelligence Platform")
    st.caption("Data: Financial Modeling Prep")

if not FMP_KEY:
    st.error("⚠️ FMP API key missing. Add it to .streamlit/secrets.toml")
    st.stop()

with st.spinner(f"Loading {symbol}..."):
    profile  = get_profile(symbol)
    quote    = get_quote(symbol)
    income   = get_income(symbol, period)
    balance  = get_balance(symbol)
    cashflow = get_cashflow(symbol)
    metrics  = get_metrics(symbol)
    ratios   = get_ratios(symbol)

    if quote:
        profile["mktCap"]            = quote.get("marketCap", profile.get("mktCap", 0))
        profile["price"]             = quote.get("price", profile.get("price", 0))
        profile["changesPercentage"] = quote.get("changesPercentage", 0)

if not profile:
    st.error(f"Could not load data for {symbol}. Check the ticker.")
    st.stop()

score = calc_score(metrics, ratios)
rating, emoji = get_rating(score["total"])

col1, col2, col3 = st.columns([3, 1, 1])
with col1:
    st.markdown(f"## {profile.get('companyName','—')} `{symbol}`")
    price  = profile.get("price", 0)
    change = profile.get("changesPercentage", 0)
    color  = "🟢" if change >= 0 else "🔴"
    st.markdown(f"### ${price:,.2f}  {color} {change:+.2f}%  ·  {profile.get('exchangeShortName','')}")
with col2:
    mktcap = profile.get("mktCap", 0)
    st.metric("Market Cap", f"${mktcap/1e9:.1f}B" if mktcap else "—")
    st.metric("Sector", profile.get("sector","—"))
with col3:
    st.markdown(f"### {emoji} {rating}")
    st.markdown(f"**Apex Score: {score['total']}/100**")

st.markdown("---")

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📊 Overview", "📋 Financials", "💰 Valuation",
    "👥 Peers", "⚠️ Risk", "🎯 Scenario", "🤖 AI Analyst"
])

with tab1:
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Revenue",      f"${income[0].get('revenue',0)/1e9:.1f}B" if income else "—")
    c2.metric("Net Income",   f"${income[0].get('netIncome',0)/1e9:.1f}B" if income else "—")
    c3.metric("Gross Margin", f"{ratios.get('grossProfitMargin',0)*100:.1f}%")
    c4.metric("ROE",          f"{ratios.get('returnOnEquityRatio',0)*100:.1f}%")

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("P/E Ratio",     f"{ratios.get('priceToEarningsRatio',0):.1f}x")
    c2.metric("EV/EBITDA",     f"{metrics.get('enterpriseValueMultiple',0):.1f}x")
    c3.metric("Current Ratio", f"{ratios.get('currentRatio',0):.2f}x")
    c4.metric("Debt/Equity",   f"{ratios.get('debtToEquityRatio',0):.2f}x")

    st.markdown("---")
    if income:
        df = pd.DataFrame(income).head(5)
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**Revenue Trend**")
            fig = px.bar(df, x="date", y="revenue",
                         color_discrete_sequence=["#3b82f6"])
            fig.update_layout(paper_bgcolor="#0a0e1a", plot_bgcolor="#0a0e1a",
                              font_color="white", showlegend=False, height=280)
            st.plotly_chart(fig, use_container_width=True)
        with col_b:
            st.markdown("**Net Income Trend**")
            fig2 = px.bar(df, x="date", y="netIncome",
                          color_discrete_sequence=["#22c55e"])
            fig2.update_layout(paper_bgcolor="#0a0e1a", plot_bgcolor="#0a0e1a",
                               font_color="white", showlegend=False, height=280)
            st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")
    st.markdown("**Score Breakdown**")
    score_df = pd.DataFrame({
        "Category": ["Growth","Profitability","Liquidity","Leverage","Valuation"],
        "Score": [score["growth"], score["profitability"], score["liquidity"],
                  score["leverage"], score["valuation"]]
    })
    fig3 = px.bar(score_df, x="Score", y="Category", orientation="h",
                  color="Score", color_continuous_scale="RdYlGn", range_color=[0,100])
    fig3.update_layout(paper_bgcolor="#0a0e1a", plot_bgcolor="#0a0e1a",
                       font_color="white", height=250, showlegend=False)
    st.plotly_chart(fig3, use_container_width=True)

    st.markdown("**About**")
    st.write(profile.get("description","—"))

with tab2:
    if income:
        st.markdown("### Income Statement")
        df_inc = pd.DataFrame(income)[["date","revenue","grossProfit","operatingIncome","netIncome","eps"]].head(5)
        df_inc.columns = ["Date","Revenue","Gross Profit","Op. Income","Net Income","EPS"]
        for col in ["Revenue","Gross Profit","Op. Income","Net Income"]:
            df_inc[col] = df_inc[col].apply(lambda x: f"${x/1e9:.2f}B" if x else "—")
        st.dataframe(df_inc, use_container_width=True, hide_index=True)

    if balance:
        st.markdown("### Balance Sheet")
        b = balance[0]
        st.dataframe(pd.DataFrame({
            "Metric": ["Total Assets","Total Debt","Total Equity","Cash"],
            "Value":  [f"${b.get('totalAssets',0)/1e9:.2f}B",
                       f"${b.get('totalDebt',0)/1e9:.2f}B",
                       f"${b.get('totalStockholdersEquity',0)/1e9:.2f}B",
                       f"${b.get('cashAndCashEquivalents',0)/1e9:.2f}B"]
        }), use_container_width=True, hide_index=True)

    if cashflow:
        st.markdown("### Cash Flow")
        cf = cashflow[0]
        st.dataframe(pd.DataFrame({
            "Metric": ["Operating CF","CapEx","Free Cash Flow","Dividends Paid"],
            "Value":  [f"${cf.get('operatingCashFlow',0)/1e9:.2f}B",
                       f"${cf.get('capitalExpenditure',0)/1e9:.2f}B",
                       f"${cf.get('freeCashFlow',0)/1e9:.2f}B",
                       f"${cf.get('dividendsPaid',0)/1e9:.2f}B"]
        }), use_container_width=True, hide_index=True)

with tab3:
    st.markdown("### Valuation Multiples")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("P/E",       f"{ratios.get('priceToEarningsRatio',0):.1f}x")
    c2.metric("P/B",       f"{ratios.get('priceToBookRatio',0):.1f}x")
    c3.metric("EV/EBITDA", f"{metrics.get('enterpriseValueMultiple',0):.1f}x")
    c4.metric("EV/Sales",  f"{metrics.get('priceToSalesRatio',0):.1f}x")

    st.markdown("---")
    st.markdown("### DCF Fair Value Estimate")
    col_s, col_r = st.columns(2)
    with col_s:
        rev_growth = st.slider("Revenue Growth %", -10, 50, 10)
        net_margin = st.slider("Net Margin %", 1, 60, 20)
        wacc       = st.slider("Discount Rate (WACC) %", 5, 20, 10)

    rev      = income[0].get("revenue", 0) if income else 0
    proj_fcf = rev * (net_margin / 100)
    dcf_val  = proj_fcf / (wacc / 100) if wacc > 0 else 0
    shares   = profile.get("mktCap", 1) / profile.get("price", 1)
    fair_val = dcf_val / shares if shares > 0 else 0
    upside   = ((fair_val - profile.get("price",0)) / profile.get("price",1)) * 100

    with col_r:
        st.metric("Estimated Fair Value", f"${fair_val:,.2f}")
        st.metric("Current Price",        f"${profile.get('price',0):,.2f}")
        st.metric("Implied Upside/Downside", f"{upside:+.1f}%")

with tab4:
    st.markdown(f"### Comparing {symbol} vs {', '.join(peers)}")
    all_symbols = [symbol] + peers
    peer_rows = []
    for s in all_symbols:
        r = get_ratios(s)
        m = get_metrics(s)
        p = get_profile(s)
        q = get_quote(s)
        if q:
            p["mktCap"] = q.get("marketCap", p.get("mktCap", 0))
            p["price"]  = q.get("price", p.get("price", 0))
        if r and p:
            peer_rows.append({
                "Symbol":      s,
                "Price":       f"${p.get('price',0):,.2f}",
                "Mkt Cap":     f"${p.get('mktCap',0)/1e9:.1f}B",
                "P/E":         f"{r.get('priceToEarningsRatio',0):.1f}x",
                "Net Margin":  f"{r.get('netProfitMargin',0)*100:.1f}%",
                "ROE":         f"{r.get('returnOnEquityRatio',0)*100:.1f}%",
                "Debt/Equity": f"{r.get('debtToEquityRatio',0):.2f}x",
            })
    if peer_rows:
        st.dataframe(pd.DataFrame(peer_rows), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("### Margin Comparison")
    margin_rows = []
    for s in all_symbols:
        r = get_ratios(s)
        if r:
            margin_rows.append({
                "Symbol":       s,
                "Gross Margin": r.get("grossProfitMargin",0)*100,
                "Net Margin":   r.get("netProfitMargin",0)*100,
                "ROE":          r.get("returnOnEquityRatio",0)*100,
            })
    if margin_rows:
        df_m = pd.DataFrame(margin_rows)
        fig_m = px.bar(df_m.melt(id_vars="Symbol"), x="Symbol", y="value",
                       color="variable", barmode="group",
                       color_discrete_sequence=["#3b82f6","#22c55e","#f59e0b"])
        fig_m.update_layout(paper_bgcolor="#0a0e1a", plot_bgcolor="#0a0e1a",
                            font_color="white", height=350)
        st.plotly_chart(fig_m, use_container_width=True)

with tab5:
    st.markdown("### Risk Analysis")
    flags = []
    de  = ratios.get("debtToEquityRatio", 0)
    cr  = ratios.get("currentRatio", 1)
    npm = ratios.get("netProfitMargin", 0.1) * 100
    fcf = cashflow[0].get("freeCashFlow", 1) if cashflow else 1

    if de > 2:  flags.append(("🔴 High Leverage",           f"Debt/Equity: {de:.2f}x"))
    if cr < 1:  flags.append(("🔴 Low Liquidity",           f"Current Ratio: {cr:.2f}x"))
    if npm < 5: flags.append(("🟡 Thin Margins",            f"Net Margin: {npm:.1f}%"))
    if fcf < 0: flags.append(("🔴 Negative Free Cash Flow", f"FCF: ${fcf/1e9:.2f}B"))

    risk_score = max(0, 100 - len(flags) * 20)
    r_label    = "Low Risk" if risk_score >= 70 else "Moderate Risk" if risk_score >= 40 else "High Risk"

    c1, c2 = st.columns(2)
    with c1:
        st.metric("Risk Score", f"{risk_score}/100", delta=r_label)
    with c2:
        if flags:
            for f, detail in flags:
                st.warning(f"{f} — {detail}")
        else:
            st.success("✅ No major risk flags detected")

    risk_df = pd.DataFrame({
        "Factor":  ["Leverage","Liquidity","Profitability","Cash Flow"],
        "Score":   [max(0, 80-de*15), min(100, cr*40), min(100, npm*3), 80 if fcf > 0 else 20]
    })
    fig_r = px.bar(risk_df, x="Factor", y="Score",
                   color="Score", color_continuous_scale="RdYlGn", range_color=[0,100])
    fig_r.update_layout(paper_bgcolor="#0a0e1a", plot_bgcolor="#0a0e1a",
                        font_color="white", height=300)
    st.plotly_chart(fig_r, use_container_width=True)

with tab6:
    st.markdown("### Scenario Analysis")
    col1, col2 = st.columns(2)
    with col1:
        s_growth = st.slider("Revenue Growth %", -20, 60, 10, key="sg")
        s_margin = st.slider("Net Margin %",       1, 60, 20, key="sm")
        s_wacc   = st.slider("Discount Rate %",    5, 25, 10, key="sw")
        s_years  = st.slider("Projection Years",   3, 10,  5, key="sy")

    rev0      = income[0].get("revenue", 0) if income else 0
    scenarios = {"Bear": 0.65, "Base": 1.0, "Bull": 1.4}
    results   = {}
    for name, mult in scenarios.items():
        g      = (s_growth * mult) / 100
        rev    = rev0 * ((1 + g) ** s_years)
        fcf_p  = rev * (s_margin / 100)
        val    = fcf_p / (s_wacc / 100) if s_wacc > 0 else 0
        shares = profile.get("mktCap",1) / profile.get("price",1)
        results[name] = val / shares if shares > 0 else 0

    with col2:
        for name, fv in results.items():
            cur    = profile.get("price", 0)
            upside = ((fv - cur) / cur * 100) if cur > 0 else 0
            icon   = "🟢" if upside > 0 else "🔴"
            st.metric(f"{name} Case", f"${fv:,.2f}", delta=f"{icon} {upside:+.1f}%")

    fig_s = go.Figure(go.Bar(
        x=list(results.keys()),
        y=list(results.values()),
        marker_color=["#ef4444","#3b82f6","#22c55e"]
    ))
    fig_s.add_hline(y=profile.get("price",0), line_dash="dash",
                    line_color="white", annotation_text="Current Price")
    fig_s.update_layout(paper_bgcolor="#0a0e1a", plot_bgcolor="#0a0e1a",
                        font_color="white", height=350,
                        title="Bear / Base / Bull Fair Value")
    st.plotly_chart(fig_s, use_container_width=True)

with tab7:
    st.markdown("### 🤖 AI Analyst")
    if not AI_KEY:
        st.error("Anthropic API key missing in secrets.toml")
    else:
        client = Anthropic(api_key=AI_KEY)
        context = f"""
        Company: {profile.get('companyName')} ({symbol})
        Price: ${profile.get('price')}
        Market Cap: ${profile.get('mktCap',0)/1e9:.1f}B
        Sector: {profile.get('sector')}
        P/E: {ratios.get('priceToEarningsRatio',0):.1f}x
        EV/EBITDA: {metrics.get('enterpriseValueMultiple',0):.1f}x
        Net Margin: {ratios.get('netProfitMargin',0)*100:.1f}%
        ROE: {ratios.get('returnOnEquityRatio',0)*100:.1f}%
        Debt/Equity: {ratios.get('debtToEquityRatio',0):.2f}x
        Current Ratio: {ratios.get('currentRatio',0):.2f}x
        Apex Score: {score['total']}/100 ({rating})
        """

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("#### Generate Research Note")
            if st.button("📄 Generate AI Report", type="primary"):
                with st.spinner("Analyzing..."):
                    msg = client.messages.create(
                        model="claude-opus-4-5",
                        max_tokens=800,
                        messages=[{"role":"user","content":f"Write a concise institutional equity research note. Include: Investment Summary, Profitability, Growth, Risks, Valuation, Recommendation (BUY/HOLD/RISKY).\n\nData:\n{context}"}]
                    )
                    st.markdown(msg.content[0].text)

        with col_b:
            st.markdown("#### Ask the AI Analyst")
            if "messages" not in st.session_state:
                st.session_state.messages = []
            for m in st.session_state.messages:
                with st.chat_message(m["role"]):
                    st.write(m["content"])
            user_input = st.chat_input("Ask about valuation, risks, growth...")
            if user_input:
                st.session_state.messages.append({"role":"user","content":user_input})
                with st.chat_message("user"):
                    st.write(user_input)
                with st.spinner("Thinking..."):
                    resp = client.messages.create(
                        model="claude-opus-4-5",
                        max_tokens=400,
                        system=f"You are an elite equity analyst. Answer using ONLY this real data: {context}. Be concise and specific.",
                        messages=st.session_state.messages
                    )
                    reply = resp.content[0].text
                    st.session_state.messages.append({"role":"assistant","content":reply})
                    with st.chat_message("assistant"):
                        st.write(reply)

st.markdown("---")
st.caption("◈ Apex Intelligence Platform · Data: Financial Modeling Prep · Not financial advice")