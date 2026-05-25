import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from orchestrator.orchestrator import Orchestrator

# ── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Decision Intelligence Co-Pilot",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Styling — retail operations dashboard ────────────────────────────────────
st.markdown("""
<style>
/* ════════════════════════════════════════════════════════════════════
   GLOBAL — force light-theme text throughout main content.
   Streamlit dark mode sets text to near-white; these rules restore
   dark-on-light readability.
   Targeting only block-level text elements (p, li, label, hN) so
   span/div/strong with inline color styles (status badges, agent
   headers) are NOT overridden — inline color on those elements wins
   via CSS inheritance rather than being clobbered by !important here.
   ════════════════════════════════════════════════════════════════════ */
.main .block-container p,
.main .block-container li,
.main .block-container label,
.main .block-container h1,
.main .block-container h2,
.main .block-container h3,
.main .block-container h4,
.main .block-container h5,
.main .block-container h6 {
    color: #0F1111 !important;
}

/* Captions stay slightly muted */
.main .block-container .stCaption p { color: #565959 !important; }

/* Alert boxes — st.info / st.success / st.warning / st.error.
   Target p and li inside alerts; spans inside keep their own color. */
[data-testid="stAlert"] p,
[data-testid="stAlert"] li,
div[data-baseweb="notification"] p,
div[data-baseweb="notification"] li {
    color: #0F1111 !important;
}

/* Expander summary label */
[data-testid="stExpander"] summary p { color: #0F1111 !important; }

/* Dataframe cell text */
[data-testid="stDataFrame"] p,
[data-testid="stDataFrame"] span { color: #0F1111 !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background-color: #FAFAFA !important;
    border-right: 1px solid #D5D9D9;
}
[data-testid="stSidebar"] * { color: #0F1111 !important; }
[data-testid="stSidebar"] h2 {
    color: #232F3E !important;
    font-size: 16px !important;
    font-weight: 700 !important;
}
[data-testid="stSidebar"] .stCaption p { color: #565959 !important; font-size: 12px !important; }

/* ── Sidebar text area and inputs — white background, dark text ── */
[data-testid="stSidebar"] textarea,
[data-testid="stSidebar"] input[type="text"],
[data-testid="stSidebar"] input {
    background-color: #FFFFFF !important;
    color: #0F1111 !important;
    border: 1px solid #D5D9D9 !important;
    border-radius: 3px !important;
}
[data-testid="stSidebar"] textarea:focus,
[data-testid="stSidebar"] input:focus {
    border-color: #E47911 !important;
    box-shadow: 0 0 0 2px #E4791133 !important;
}
[data-testid="stSidebar"] textarea::placeholder,
[data-testid="stSidebar"] input::placeholder { color: #A0A0A0 !important; }
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stTextArea label p {
    color: #232F3E !important;
    font-size: 13px !important;
    font-weight: 600 !important;
}

/* ── Primary button — orange gradient ── */
.stButton > button[kind="primary"] {
    background: linear-gradient(to bottom, #f5c142 0%, #e59820 100%) !important;
    border: 1px solid #C7812A !important;
    border-radius: 3px !important;
    color: #111111 !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.15) !important;
    letter-spacing: 0.01em !important;
}
.stButton > button[kind="primary"]:hover {
    background: linear-gradient(to bottom, #f0ba2e 0%, #d07b12 100%) !important;
}

/* ── Sidebar secondary buttons (example queries, history) ── */
[data-testid="stSidebar"] .stButton > button {
    background: #FFFFFF !important;
    border: 1px solid #D5D9D9 !important;
    color: #007185 !important;
    text-align: left !important;
    font-size: 12px !important;
    border-radius: 3px !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: #F0F2F2 !important;
    border-color: #A6A6A6 !important;
    color: #C45500 !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: linear-gradient(to bottom, #f5c142 0%, #e59820 100%) !important;
    border: 1px solid #C7812A !important;
    color: #111111 !important;
}

/* ── Agent tag ── */
.agent-tag {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 3px;
    font-size: 12px;
    font-weight: 600;
    margin: 2px;
}

/* ── Section header — panel style ── */
.section-header {
    background: #F0F2F2;
    border-top: 1px solid #D5D9D9;
    border-bottom: 1px solid #D5D9D9;
    padding: 6px 2px;
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: #232F3E !important;
    margin: 16px 0 8px 0;
}

/* ── Recommendation box ── */
.rec-box {
    background: #EAF4FB;
    border: 1px solid #A8CBE8;
    border-left: 4px solid #007185;
    padding: 16px 20px;
    border-radius: 0 4px 4px 0;
    margin: 8px 0;
    font-size: 15px;
    line-height: 1.65;
    color: #0F1111 !important;
}

/* ── Metric card ── */
.m-card {
    background: #FFFFFF;
    border: 1px solid #D5D9D9;
    border-radius: 4px;
    padding: 14px 10px;
    text-align: center;
    margin-bottom: 8px;
}
.m-label {
    font-size: 11px;
    color: #565959 !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 6px;
}
.m-value {
    font-size: 20px;
    font-weight: 700;
    color: #0F1111 !important;
    word-break: break-word;
}
.m-value-sm {
    font-size: 15px;
    font-weight: 700;
    color: #0F1111 !important;
    word-break: break-word;
}

/* ── Landing page info card ── */
.info-card {
    background: #FFFFFF;
    border: 1px solid #D5D9D9;
    border-radius: 4px;
    padding: 0;
    margin-bottom: 12px;
    box-shadow: 0 1px 3px rgba(35,47,62,0.05);
}
.info-card-header {
    background: #F0F2F2;
    border-bottom: 1px solid #D5D9D9;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 700;
    color: #232F3E !important;
    border-radius: 4px 4px 0 0;
}
.info-card-body { padding: 12px 16px; }
.info-card-body li { color: #0F1111 !important; font-size: 13px; margin-bottom: 4px; }
.info-card-body a { color: #007185; }

/* ── Expander ── */
[data-testid="stExpander"] {
    border: 1px solid #D5D9D9 !important;
    border-radius: 4px !important;
    background: white !important;
}

/* ── Divider ── */
hr { border-color: #D5D9D9 !important; margin: 10px 0 !important; }

/* ── Dataframe ── */
[data-testid="stDataFrame"] { border: 1px solid #D5D9D9; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)

# ── Constants ────────────────────────────────────────────────────────────────
EXAMPLE_QUERIES = [
    "What are customers saying about our products overall?",
    "How many customers complained about petite sizing being unavailable?",
    "How many options do we have for black tops?",
    "Do we have casual tops available across multiple colours?",
    "Give me an overall summary of our product catalog by category.",
    "What is the optimal price for article 0108775015?",
    "What do customers think about and what should we charge for article 0108775015?",
    "Which products are at risk of stockout and need urgent replenishment?",
    "What is the replenishment status for article 0108775015?",
    "Which products should we consider running a promotion or price discount on?",
    "Should we run a campaign or discount for article 0108775015?"
]

AGENT_COLORS = {
    "customer_voice":        "#007185",
    "pricing_profit":        "#E47911",
    "product_discovery":     "#067D62",
    "inventory_supply":      "#C40000",
    "campaign_intelligence": "#5C5C99"
}

AGENT_LABELS = {
    "customer_voice":        "Customer Voice",
    "pricing_profit":        "Pricing & Profit",
    "product_discovery":     "Product Discovery",
    "inventory_supply":      "Inventory & Supply",
    "campaign_intelligence": "Campaign Intelligence"
}

AGENT_ICONS = {
    "customer_voice":        "💬",
    "pricing_profit":        "💰",
    "product_discovery":     "🔍",
    "inventory_supply":      "📦",
    "campaign_intelligence": "📣"
}

STATUS_COLORS = {
    "CRITICAL":    "#C40000", "AT_RISK":  "#E47911", "HEALTHY":   "#007600",
    "PROMOTE_NOW": "#C40000", "MONITOR":  "#E47911", "HOLD":      "#007600",
    "DECLINING":   "#C40000", "STABLE":   "#E47911", "GROWING":   "#007600",
    "HIGH":        "#C40000", "MEDIUM":   "#E47911", "LOW":       "#007600"
}


# ── Orchestrator (loaded once, cached across reruns) ─────────────────────────
@st.cache_resource(show_spinner="Loading agents and data sources...")
def load_orchestrator():
    return Orchestrator()


# ── Session state ────────────────────────────────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = []
if "current" not in st.session_state:
    st.session_state.current = None
if "auto_query" not in st.session_state:
    st.session_state.auto_query = ""


# ── Helpers ──────────────────────────────────────────────────────────────────
def status_badge(label):
    color = STATUS_COLORS.get(str(label).upper(), "#565959")
    st.markdown(
        f'<span style="background:{color}18; color:{color}; '
        f'border:1.5px solid {color}88; padding:4px 14px; border-radius:3px; '
        f'font-size:13px; font-weight:700; letter-spacing:0.03em">{label}</span>',
        unsafe_allow_html=True
    )


def metric_card(label, value):
    cls = "m-value" if len(str(value)) <= 10 else "m-value-sm"
    st.markdown(
        f'<div class="m-card">'
        f'<div class="m-label">{label}</div>'
        f'<div class="{cls}">{value}</div>'
        f'</div>',
        unsafe_allow_html=True
    )


def _fmt_price(val):
    try:
        return f"{float(val):.4f}"
    except (TypeError, ValueError):
        return str(val) if val else "?"


def section_header(text):
    st.markdown(f'<p class="section-header">{text}</p>', unsafe_allow_html=True)


# ── Render: Customer Voice ───────────────────────────────────────────────────
def render_customer_voice(result):
    if not result:
        st.warning("No customer voice data returned.")
        return

    if "direct_answer" in result:
        col1, col2 = st.columns([1, 2])
        with col1:
            metric_card("Reviews Found",
                        result.get("review_count", result.get("relevant_review_count", "?")))
            st.markdown("**Sentiment**")
            status_badge(result.get("sentiment", "?").upper())
        with col2:
            section_header("Answer")
            st.info(result.get("direct_answer", ""))

        evidence = result.get("supporting_evidence", [])
        if evidence:
            section_header("Supporting Evidence")
            for quote in evidence[:3]:
                st.markdown(f"> {quote}")

        if result.get("recommendation"):
            st.success(f"**Recommendation:** {result['recommendation']}")

    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            metric_card("Reviews Analyzed", result.get("total_reviews", "?"))
        with col2:
            metric_card("Avg Sentiment Score", result.get("avg_sentiment_score", "?"))
        with col3:
            breakdown = result.get("sentiment_breakdown", {})
            if breakdown:
                dominant = max(breakdown, key=lambda k: breakdown.get(k, 0))
                metric_card("Dominant Sentiment", dominant.title())

        themes = result.get("top_themes", [])
        if themes:
            df = pd.DataFrame({
                "Theme": themes,
                "Weight": list(range(len(themes), 0, -1))
            })
            fig = px.bar(df, x="Weight", y="Theme", orientation="h",
                         title="Top Customer Themes",
                         color_discrete_sequence=[AGENT_COLORS["customer_voice"]])
            fig.update_layout(height=250, margin=dict(l=0, r=0, t=30, b=0),
                              showlegend=False, xaxis_title="", yaxis_title="",
                              plot_bgcolor="white", paper_bgcolor="white",
                              font=dict(color="#0F1111"))
            fig.update_xaxes(showgrid=True, gridcolor="#F0F2F2")
            st.plotly_chart(fig, use_container_width=True)

        col_a, col_b = st.columns(2)
        with col_a:
            negatives = result.get("top_negatives", [])
            if negatives:
                section_header("Top Negatives")
                for n in negatives[:4]:
                    st.markdown(f"- {n}")
        with col_b:
            needs = result.get("top_unmet_needs", [])
            if needs:
                section_header("Unmet Needs")
                for n in needs[:4]:
                    st.markdown(f"- {n}")

        if result.get("executive_summary"):
            st.info(result["executive_summary"])


# ── Render: Pricing & Profit ─────────────────────────────────────────────────
def render_pricing(result):
    if not result:
        st.warning("No pricing data returned.")
        return

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("Recommended Price", _fmt_price(result.get("recommended_price")))
    with col2:
        metric_card("Best Current Price", _fmt_price(result.get("current_best_price")))
    with col3:
        metric_card("Elasticity", result.get("price_elasticity", "?").title())
    with col4:
        metric_card("Confidence", result.get("confidence", "?").title())

    scenarios = result.get("revenue_scenarios", [])
    if scenarios:
        df = pd.DataFrame(scenarios)
        if "projected_revenue" in df.columns and "label" in df.columns:
            if "price" in df.columns:
                df["scenario"] = df.apply(
                    lambda r: f"{r['label'].title()}\n(price: {float(r['price']):.4f})", axis=1
                )
            else:
                df["scenario"] = df["label"].str.title()

            fig = px.bar(
                df, x="scenario", y="projected_revenue",
                title="Revenue Scenarios by Price Point",
                color="scenario",
                color_discrete_sequence=["#007185", AGENT_COLORS["pricing_profit"], "#067D62"],
                text=df["projected_revenue"].apply(lambda v: f"{float(v):.4f}"),
                hover_data={c: True for c in ["price", "projected_units", "projected_revenue"]
                            if c in df.columns}
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(
                height=320, margin=dict(l=0, r=0, t=40, b=0),
                showlegend=False,
                xaxis_title="Scenario (normalized price)",
                yaxis_title="Projected Revenue",
                plot_bgcolor="white", paper_bgcolor="white",
                font=dict(color="#0F1111")
            )
            fig.update_yaxes(showgrid=True, gridcolor="#F0F2F2")
            st.plotly_chart(fig, use_container_width=True)

        display_cols = [c for c in ["label", "price", "projected_units", "projected_revenue"]
                        if c in df.columns]
        if display_cols:
            fmt_df = df[display_cols].copy()
            for col in ["price", "projected_revenue"]:
                if col in fmt_df.columns:
                    fmt_df[col] = fmt_df[col].apply(lambda v: f"{float(v):.4f}")
            fmt_df.columns = [c.replace("_", " ").title() for c in fmt_df.columns]
            st.dataframe(fmt_df, hide_index=True, use_container_width=True)

    if result.get("recommendation_rationale"):
        st.info(f"**Rationale:** {result['recommendation_rationale']}")

    if result.get("elasticity_explanation"):
        st.caption(result["elasticity_explanation"])


# ── Render: Product Discovery ────────────────────────────────────────────────
def render_product_discovery(result):
    if not result:
        st.warning("No product discovery data returned.")
        return

    if "direct_answer" in result:
        col1, col2 = st.columns([1, 2])
        with col1:
            metric_card("Matching Products", result.get("total_matches", "?"))
        with col2:
            st.info(result.get("direct_answer", ""))

        col_a, col_b = st.columns(2)
        with col_a:
            colours = result.get("colour_variety", [])
            if colours:
                section_header("Colours Found")
                st.markdown("  ".join([f"`{c}`" for c in colours]))
        with col_b:
            styles = result.get("style_variety", [])
            if styles:
                section_header("Styles Found")
                st.markdown("  ".join([f"`{s}`" for s in styles]))

        if result.get("coverage_assessment"):
            st.success(result["coverage_assessment"])
        if result.get("gap_identified"):
            st.warning(f"**Gap:** {result['gap_identified']}")

    else:
        col1, col2 = st.columns([1, 3])
        with col1:
            metric_card("Products Sampled", result.get("total_products_sampled", "?"))

        breakdown = result.get("category_breakdown", [])
        if breakdown:
            df = pd.DataFrame(breakdown)
            if "category" in df.columns and "product_count" in df.columns:
                fig = px.bar(df, x="product_count", y="category", orientation="h",
                             title="Products by Category",
                             color_discrete_sequence=[AGENT_COLORS["product_discovery"]])
                fig.update_layout(height=300, margin=dict(l=0, r=0, t=30, b=0),
                                  showlegend=False, xaxis_title="Count", yaxis_title="",
                                  plot_bgcolor="white", paper_bgcolor="white",
                                  font=dict(color="#0F1111"))
                fig.update_xaxes(showgrid=True, gridcolor="#F0F2F2")
                st.plotly_chart(fig, use_container_width=True)

        col_a, col_b = st.columns(2)
        with col_a:
            strengths = result.get("catalog_strengths", [])
            if strengths:
                section_header("Catalog Strengths")
                for s in strengths:
                    st.markdown(f"- {s}")
        with col_b:
            gaps = result.get("catalog_gaps", [])
            if gaps:
                section_header("Catalog Gaps")
                for g in gaps:
                    st.markdown(f"- {g}")

        if result.get("executive_summary"):
            st.info(result["executive_summary"])


# ── Render: Inventory & Supply ───────────────────────────────────────────────
def render_inventory(result):
    if not result:
        st.warning("No inventory data returned.")
        return

    if "recommended_order_quantity" in result:
        col1, col2, col3 = st.columns(3)
        with col1:
            metric_card("Days Until Stockout", result.get("days_until_stockout", "?"))
        with col2:
            metric_card("Order Quantity",
                        f"{result.get('recommended_order_quantity', '?')} units")
        with col3:
            metric_card("Order By", result.get("recommended_order_date", "?"))

        st.markdown("**Replenishment Status**")
        status = result.get("replenishment_status", "?")
        status_badge(status)

        if result.get("rationale"):
            st.info(f"**Rationale:** {result['rationale']}")
        if result.get("risk_factors"):
            section_header("Risk Factors")
            for r in result["risk_factors"]:
                st.markdown(f"- {r}")

    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            metric_card("At-Risk Articles", result.get("total_at_risk", "?"))
        with col2:
            metric_card("Critical", result.get("critical_count", "?"))
        with col3:
            metric_card("Stockout This Week", result.get("projected_stockout_this_week", "?"))

        priorities = result.get("top_priority_articles", [])
        if priorities:
            section_header("Top Priority Articles")
            df = pd.DataFrame({"Priority Article IDs": priorities})
            st.dataframe(df, hide_index=True, use_container_width=True)

        warehouse = result.get("warehouse_breakdown", [])
        if warehouse:
            df_w = pd.DataFrame(warehouse)
            if "warehouse" in df_w.columns and "at_risk_count" in df_w.columns:
                fig = px.bar(df_w, x="warehouse", y="at_risk_count",
                             title="At-Risk Articles by Warehouse",
                             color_discrete_sequence=[AGENT_COLORS["inventory_supply"]])
                fig.update_layout(height=250, margin=dict(l=0, r=0, t=30, b=0),
                                  showlegend=False, plot_bgcolor="white",
                                  paper_bgcolor="white", font=dict(color="#0F1111"))
                fig.update_yaxes(showgrid=True, gridcolor="#F0F2F2")
                st.plotly_chart(fig, use_container_width=True)

        if result.get("executive_summary"):
            st.info(result["executive_summary"])

        actions = result.get("immediate_actions", [])
        if actions:
            section_header("Immediate Actions")
            for a in actions:
                st.markdown(f"- {a}")


# ── Render: Campaign Intelligence ────────────────────────────────────────────
def render_campaign(result):
    if not result:
        st.warning("No campaign data returned.")
        return

    if "promotion_recommendation" in result:
        col1, col2, col3 = st.columns(3)
        with col1:
            metric_card("Suggested Discount",
                        f"{result.get('suggested_discount_pct', 0)}%")
        with col2:
            metric_card("Demand Change",
                        f"{result.get('demand_change_pct', 0)}%")
        with col3:
            metric_card("Demand Trend", result.get("demand_trend", "?"))

        st.markdown("**Promotion Recommendation**")
        rec = result.get("promotion_recommendation", "?")
        status_badge(rec)
        st.markdown(f"`{result.get('campaign_type', '?')}`")

        if result.get("campaign_timing"):
            st.markdown(f"**Timing:** {result['campaign_timing']}")
        if result.get("rationale"):
            st.info(f"**Rationale:** {result['rationale']}")
        if result.get("risk_of_inaction"):
            st.warning(f"**Risk of inaction:** {result['risk_of_inaction']}")

    else:
        col1, col2 = st.columns(2)
        with col1:
            metric_card("Total Candidates", result.get("total_candidates", "?"))
        with col2:
            metric_card("High Urgency", result.get("high_urgency_count", "?"))

        candidates = result.get("top_promotion_candidates", [])
        if candidates:
            df = pd.DataFrame(candidates)
            if "article_id" in df.columns and "demand_change_pct" in df.columns:
                df["demand_change_pct"] = pd.to_numeric(df["demand_change_pct"],
                                                        errors="coerce")
                fig = px.bar(df.head(10), x="article_id", y="demand_change_pct",
                             title="Demand Change % — Top Promotion Candidates",
                             color="demand_change_pct",
                             color_continuous_scale=["#C40000", "#E47911", "#007600"])
                fig.update_layout(height=300, margin=dict(l=0, r=0, t=30, b=0),
                                  showlegend=False, xaxis_title="Article ID",
                                  yaxis_title="Demand Change %",
                                  plot_bgcolor="white", paper_bgcolor="white",
                                  font=dict(color="#0F1111"))
                fig.add_hline(y=0, line_dash="dash", line_color="#D5D9D9")
                st.plotly_chart(fig, use_container_width=True)

            section_header("Candidate Details")
            display_cols = [c for c in ["article_id", "demand_change_pct",
                                        "recommended_discount_pct", "urgency"]
                            if c in df.columns]
            st.dataframe(df[display_cols], hide_index=True, use_container_width=True)

        if result.get("executive_summary"):
            st.info(result["executive_summary"])

        actions = result.get("immediate_actions", [])
        if actions:
            section_header("Immediate Actions")
            for a in actions:
                st.markdown(f"- {a}")


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 DI Co-Pilot")
    st.caption("Decision Intelligence · Retail Operations")
    st.divider()

    query_input = st.text_area(
        "Ask a business question",
        value=st.session_state.auto_query,
        placeholder="e.g. Which products need urgent replenishment?",
        height=110,
        key="query_area"
    )

    run_clicked = st.button("▶  Run Query", use_container_width=True, type="primary")

    with st.expander("Try an example query"):
        for ex in EXAMPLE_QUERIES:
            label = ex[:52] + "…" if len(ex) > 52 else ex
            if st.button(label, key=f"ex_{ex[:25]}", use_container_width=True):
                st.session_state.auto_query = ex
                st.rerun()

    if st.session_state.history:
        st.divider()
        st.caption(f"Recent queries ({len(st.session_state.history)})")
        for i, entry in enumerate(reversed(st.session_state.history[-8:])):
            agents  = ", ".join(entry["intent"].get("agents", []))
            latency = entry.get("total_latency_sec", "?")
            label   = entry["query"][:42] + "…" if len(entry["query"]) > 42 else entry["query"]
            if st.button(label, key=f"hist_{i}",
                         help=f"Agents: {agents} | {latency}s",
                         use_container_width=True):
                st.session_state.current = entry
                st.rerun()

    st.divider()
    with st.expander("Query logs", expanded=False):
        from shared.logger import AgentLogger
        logs = AgentLogger().read_recent(n=10)
        if not logs:
            st.caption("No logs yet.")
        else:
            for entry in logs:
                ts      = entry.get("timestamp", "")[:19].replace("T", " ")
                agents  = ", ".join(entry.get("agents_called", []))
                latency = entry.get("total_latency_sec", "?")
                ok      = "✓" if entry.get("success") else "✗"
                st.caption(f"{ok} {ts}  |  {latency}s  |  {agents}")
                st.caption(f"  ↳ {entry.get('query', '')[:60]}")


# ── Main: top banner ─────────────────────────────────────────────────────────
st.markdown("""
<div style="background:#232F3E; padding:14px 24px; margin:-4rem -4rem 2rem -4rem;
     border-bottom:3px solid #FF9900;">
  <span style="color:#FF9900; font-size:19px; font-weight:700; letter-spacing:-0.2px">
    📊 Decision Intelligence Co-Pilot
  </span>
  <span style="color:#98A8B0; font-size:13px; margin-left:18px; font-weight:400">
    Retail Operations &nbsp;·&nbsp; Powered by Claude
  </span>
</div>
""", unsafe_allow_html=True)

# ── Main: run query ───────────────────────────────────────────────────────────
orchestrator = load_orchestrator()

query_to_run = ""
if run_clicked and query_input.strip():
    query_to_run = query_input.strip()
elif st.session_state.auto_query and not run_clicked:
    query_to_run = st.session_state.auto_query
    st.session_state.auto_query = ""

if query_to_run:
    with st.spinner(f"Running agents for: *{query_to_run}*"):
        result = orchestrator.run(query_to_run, stream_synthesis=True)
    st.session_state.history.append(result)
    st.session_state.current = result
    st.rerun()


# ── Main: dashboard ───────────────────────────────────────────────────────────
current = st.session_state.current

if current is None:
    # ── Landing state ──
    st.markdown(
        "<p style='color:#565959; font-size:15px; margin-bottom:1.5rem'>"
        "Type a business question in the sidebar — the Co-Pilot routes it to the right "
        "specialist agents and synthesizes a unified recommendation.</p>",
        unsafe_allow_html=True
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        agents_html = "".join(
            f'<div style="display:flex; align-items:center; gap:8px; margin-bottom:8px">'
            f'<span style="background:{color}18; color:{color}; border:1.5px solid {color}55; '
            f'padding:3px 10px; border-radius:3px; font-size:12px; font-weight:700">'
            f'{AGENT_ICONS[k]} {label}</span></div>'
            for k, label in AGENT_LABELS.items()
            for color in [AGENT_COLORS[k]]
        )
        st.markdown(
            f'<div class="info-card">'
            f'<div class="info-card-header">Available Agents</div>'
            f'<div class="info-card-body">{agents_html}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
            '<div class="info-card">'
            '<div class="info-card-header">Single-Agent Queries</div>'
            '<div class="info-card-body"><ul style="padding-left:16px; margin:0">'
            '<li>Which products are at risk of stockout?</li>'
            '<li>What are customers saying overall?</li>'
            '<li>How many black tops do we stock?</li>'
            '<li>What is the optimal price for article X?</li>'
            '<li>Which products should we promote?</li>'
            '</ul></div></div>',
            unsafe_allow_html=True
        )

    with col3:
        st.markdown(
            '<div class="info-card">'
            '<div class="info-card-header">Multi-Agent Queries</div>'
            '<div class="info-card-body"><ul style="padding-left:16px; margin:0">'
            '<li>What do customers think AND what price for article X?</li>'
            '<li>Should we discount article X? → Campaign + Pricing</li>'
            '<li>Routes to multiple agents in parallel</li>'
            '<li>Synthesizes a single unified recommendation</li>'
            '</ul></div></div>',
            unsafe_allow_html=True
        )

else:
    intent        = current.get("intent", {})
    agent_results = current.get("agent_results", {})
    formatted     = current.get("formatted", "")
    agents_called = intent.get("agents", [])

    # ── Query header ──
    st.markdown(
        f'<h3 style="color:#0F1111; font-size:20px; margin-bottom:6px">'
        f'{current["query"]}</h3>',
        unsafe_allow_html=True
    )

    # Agent tags + latency
    tag_html = ""
    for agent in agents_called:
        color = AGENT_COLORS.get(agent, "#888")
        label = AGENT_LABELS.get(agent, agent)
        icon  = AGENT_ICONS.get(agent, "")
        tag_html += (
            f'<span class="agent-tag" style="background:{color}18; color:{color}; '
            f'border:1.5px solid {color}55">{icon} {label}</span> '
        )
    latency_sec = current.get("total_latency_sec")
    if latency_sec:
        tag_html += (
            f'<span style="font-size:11px; color:#565959; margin-left:8px; '
            f'background:#F0F2F2; border:1px solid #D5D9D9; padding:3px 8px; '
            f'border-radius:3px">⏱ {latency_sec}s</span>'
        )
    st.markdown(tag_html, unsafe_allow_html=True)

    agent_timings = current.get("agent_timings", {})
    if agent_timings:
        timing_parts = [f"{AGENT_LABELS.get(k, k)}: {v}s" for k, v in agent_timings.items()]
        st.caption("  ·  ".join(timing_parts))

    with st.expander("Routing reasoning", expanded=False):
        st.caption(intent.get("reasoning", "No reasoning available."))

    st.divider()

    # ── Recommendation ──
    section_header("Recommendation")

    active_results_check = {k: v for k, v in agent_results.items() if v is not None}
    is_multi_agent = len(active_results_check) > 1

    with st.container(border=True):
        if is_multi_agent and not formatted:
            streamed_text = st.write_stream(
                orchestrator.stream_synthesis(current["query"], active_results_check)
            )
            current["formatted"] = streamed_text
        else:
            st.markdown(
                f'<div class="rec-box">{formatted}</div>',
                unsafe_allow_html=True
            )

    if not agent_results:
        st.stop()

    # ── Agent insights ──
    RENDER = {
        "customer_voice":        render_customer_voice,
        "pricing_profit":        render_pricing,
        "product_discovery":     render_product_discovery,
        "inventory_supply":      render_inventory,
        "campaign_intelligence": render_campaign,
    }

    section_header("Agent Insights")

    active_results = active_results_check

    if len(active_results) == 1:
        agent_name, result = next(iter(active_results.items()))
        color = AGENT_COLORS.get(agent_name, "#888")
        label = AGENT_LABELS.get(agent_name, agent_name)
        icon  = AGENT_ICONS.get(agent_name, "")
        with st.container(border=True):
            st.markdown(
                f'<div style="background:{color}0D; border-left:4px solid {color}; '
                f'padding:8px 16px; margin-bottom:14px; border-radius:0 3px 0 0">'
                f'<strong style="color:{color}; font-size:14px">{icon} {label}</strong>'
                f'</div>',
                unsafe_allow_html=True
            )
            RENDER[agent_name](result)

    else:
        cols = st.columns(len(active_results))
        for col, (agent_name, result) in zip(cols, active_results.items()):
            color = AGENT_COLORS.get(agent_name, "#888")
            label = AGENT_LABELS.get(agent_name, agent_name)
            icon  = AGENT_ICONS.get(agent_name, "")
            with col:
                with st.container(border=True):
                    st.markdown(
                        f'<div style="background:{color}0D; border-left:4px solid {color}; '
                        f'padding:8px 14px; margin-bottom:12px; border-radius:0 3px 0 0">'
                        f'<strong style="color:{color}; font-size:13px">{icon} {label}</strong>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
                    RENDER[agent_name](result)
