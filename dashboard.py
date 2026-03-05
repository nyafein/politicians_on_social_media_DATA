# TERMINAL: streamlit run dashboard.py

import streamlit as st
import pandas as pd
import plotly.express as px

# ── Config ────────────────────────────────────────────────────────────────────
FILE = "matched.csv" 
import streamlit as st
import pandas as pd
import plotly.express as px


# ── Load ──────────────────────────────────────────────────────────────────────
@st.cache_data
def load():
    df = pd.read_csv(FILE, dtype=str, encoding="utf-8-sig").fillna("")
    df["match_score"]   = pd.to_numeric(df["match_score"], errors="coerce")
    df["Has_Twitter"]   = df["Twitter"].str.strip().ne("").astype(int)
    df["Status"]        = df["Status"].str.strip("[]'\" ").str.split(",").str[0].str.strip()
    df["Gender"]        = df["Gender"].str.strip("[]'\" ").str.split(",").str[0].str.strip().str.capitalize()
    df["Party"]         = df["Party"].str.strip("[]'\" ").str.split(",").str[0].str.strip()
    df["Branch"]        = df["Branch"].str.strip("[]'\" ").str.split(",").str[0].str.strip()
    return df

df = load()

# ── Sidebar filters ───────────────────────────────────────────────────────────
st.sidebar.title("🔍 Filters")

countries = ["All"] + sorted(df["Country"].unique().tolist())
sel_country = st.sidebar.selectbox("Country", countries)

branches = ["All"] + sorted(df["Branch"].dropna().unique().tolist())
sel_branch = st.sidebar.selectbox("Branch", branches)

statuses = ["All"] + sorted(df["Status"].dropna().unique().tolist())
sel_status = st.sidebar.selectbox("Status", statuses)

filtered = df.copy()
if sel_country != "All":
    filtered = filtered[filtered["Country"] == sel_country]
if sel_branch != "All":
    filtered = filtered[filtered["Branch"] == sel_branch]
if sel_status != "All":
    filtered = filtered[filtered["Status"] == sel_status]

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🌐 Politicians Dashboard")
st.caption(f"Showing **{len(filtered):,}** of **{len(df):,}** matched politicians")

# ── KPI row ───────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Politicians", f"{len(filtered):,}")
k2.metric("With Twitter",      f"{filtered['Has_Twitter'].sum():,}")
k3.metric("Twitter Coverage",  f"{filtered['Has_Twitter'].mean()*100:.1f}%")
k4.metric("Avg Match Score",   f"{filtered['match_score'].mean():.1f}")

st.divider()

# ── Row 1: Coverage by Country & Branch  |  Current vs Former ────────────────
c1, c2 = st.columns(2)

with c1:
    st.subheader("Coverage by Country & Branch")
    cov = filtered.groupby(["Country", "Branch"]).size().reset_index(name="Count")
    fig = px.bar(cov, x="Country", y="Count", color="Branch", barmode="group",
                 color_discrete_sequence=px.colors.qualitative.Vivid)
    fig.update_layout(margin=dict(t=20, b=20), legend_title="Branch")
    st.plotly_chart(fig, use_container_width=True)

with c2:
    st.subheader("Current vs Former")
    stat = filtered["Status"].value_counts().reset_index()
    stat.columns = ["Status", "Count"]
    fig = px.pie(stat, names="Status", values="Count",
                 color_discrete_sequence=px.colors.qualitative.Vivid,
                 hole=0.4)
    fig.update_layout(margin=dict(t=20, b=20))
    st.plotly_chart(fig, use_container_width=True)

# ── Row 2: Gender breakdown  |  Twitter coverage by country ──────────────────
c3, c4 = st.columns(2)

with c3:
    st.subheader("Gender Breakdown")
    gen = filtered[filtered["Gender"] != ""].groupby(["Country", "Gender"]).size().reset_index(name="Count")
    fig = px.bar(gen, x="Country", y="Count", color="Gender", barmode="stack",
                 color_discrete_sequence=px.colors.qualitative.Pastel)
    fig.update_layout(margin=dict(t=20, b=20), legend_title="Gender")
    st.plotly_chart(fig, use_container_width=True)

with c4:
    st.subheader("Twitter Coverage by Country")
    twit = filtered.groupby("Country")["Has_Twitter"].mean().reset_index()
    twit.columns = ["Country", "Twitter_%"]
    twit["Twitter_%"] = (twit["Twitter_%"] * 100).round(1)
    fig = px.bar(twit, x="Country", y="Twitter_%",
                 text=twit["Twitter_%"].astype(str) + "%",
                 color="Country",
                 color_discrete_sequence=px.colors.qualitative.Vivid)
    fig.update_traces(textposition="outside")
    fig.update_layout(margin=dict(t=20, b=20), showlegend=False, yaxis_range=[0, 110])
    st.plotly_chart(fig, use_container_width=True)

# ── Row 3: Party breakdown  |  Match score distribution ──────────────────────
c5, c6 = st.columns(2)

with c5:
    st.subheader("Top Parties by Country")
    col_a, col_b = st.columns([2, 1])
    with col_a:
        sel_party_country = st.selectbox(
            "Select Country", 
            sorted(filtered["Country"].dropna().unique().tolist()),
            key="party_country"
        )
    with col_b:
        top_n = st.slider("Top N parties", min_value=2, max_value=10, value=5, key="top_n")

    top = (
        filtered[(filtered["Party"] != "") & (filtered["Country"] == sel_party_country)]
        .groupby("Party").size().reset_index(name="Count")
        .sort_values("Count", ascending=False)
        .head(top_n)
    )
    fig = px.bar(top, x="Party", y="Count",
                 color="Party",
                 color_discrete_sequence=px.colors.qualitative.Vivid)
    fig.update_layout(margin=dict(t=20, b=20), showlegend=False)
    fig.update_xaxes(tickangle=35, title="")
    st.plotly_chart(fig, use_container_width=True)

with c6:
    st.subheader("Match Score Distribution")
    fig = px.histogram(filtered, x="match_score", nbins=20,
                       color_discrete_sequence=["#636EFA"])
    fig.update_layout(margin=dict(t=20, b=20),
                      xaxis_title="Match Score", yaxis_title="Count",
                      xaxis_range=[88, 101])
    fig.add_vline(x=90, line_dash="dash", line_color="red",
                  annotation_text="Threshold (90)", annotation_position="top right")
    st.plotly_chart(fig, use_container_width=True)

# ── Raw data table ────────────────────────────────────────────────────────────
st.divider()
st.subheader("📋 Raw Data")
st.dataframe(filtered, use_container_width=True, height=400)
st.download_button("⬇️ Download filtered CSV", 
                   filtered.to_csv(index=False).encode("utf-8-sig"),
                   "filtered_politicians.csv", "text/csv")