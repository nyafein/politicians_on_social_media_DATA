# TERMINAL: streamlit run dashboard.py

import streamlit as st
import pandas as pd
import plotly.express as px
from langdetect import detect, LangDetectException

META_FILE  = "master_politicians.csv"   # canonical metadata — do not modify
POSTS_FILE = "existing_politician_posts.csv"

# ── Load metadata ─────────────────────────────────────────────────────────────
@st.cache_data
def load():
    df = pd.read_csv(META_FILE, dtype=str, encoding="utf-8-sig").fillna("")
    df["Has_Twitter"]  = df["Twitter"].str.strip().ne("").astype(int)
    df["Status"]       = df["Status"].str.strip("[]'\" ").str.split(",").str[0].str.strip()
    df["Gender"]       = df["Gender"].str.strip("[]'\" ").str.split(",").str[0].str.strip().str.capitalize()
    df["Party"]        = df["Party"].str.strip("[]'\" ").str.split(",").str[0].str.strip()
    df["Branch"]       = df["Branch"].str.strip("[]'\" ").str.split(",").str[0].str.strip()
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
k1, k2, k3 = st.columns(3)
k1.metric("Total Politicians", f"{len(filtered):,}")
k2.metric("With Twitter",      f"{filtered['Has_Twitter'].sum():,}")
k3.metric("Twitter Coverage",  f"{filtered['Has_Twitter'].mean()*100:.1f}%")

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

# ── Row 3: Party breakdown ────────────────────────────────────────────────────
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
fig = px.bar(top, x="Party", y="Count", color="Party",
             color_discrete_sequence=px.colors.qualitative.Vivid)
fig.update_layout(margin=dict(t=20, b=20), showlegend=False)
fig.update_xaxes(tickangle=35, title="")
st.plotly_chart(fig, use_container_width=True)

# ── Raw data table ────────────────────────────────────────────────────────────
st.divider()
st.subheader("📋 Raw Data")
st.dataframe(filtered, use_container_width=True, height=400)
st.download_button("⬇️ Download filtered CSV",
                   filtered.to_csv(index=False).encode("utf-8-sig"),
                   "filtered_politicians.csv", "text/csv")

# ── POSTS ANALYSIS SECTION ────────────────────────────────────────────────────
@st.cache_data
def load_posts():
    meta = pd.read_csv(META_FILE, dtype=str, encoding="utf-8-sig").fillna("")
    posts = pd.read_csv(POSTS_FILE, dtype=str, encoding="utf-8-sig").fillna("")

    # Build best available handle from metadata:
    # use final_twitter if populated, else fall back to Twitter
    meta["handle_key"] = meta["final_twitter"].str.strip()
    mask_empty = meta["handle_key"] == ""
    meta.loc[mask_empty, "handle_key"] = meta.loc[mask_empty, "Twitter"].str.strip()
    meta["handle_key"] = meta["handle_key"].str.lower()

    handle_country = (
        meta[meta["handle_key"] != ""][["handle_key", "Country"]]
        .drop_duplicates(subset="handle_key")
    )

    # Join country onto posts
    posts["handle_key"] = posts["handle"].str.lower().str.strip()
    posts = posts.merge(handle_country, on="handle_key", how="left")
    posts["Country"] = posts["Country"].fillna("Unknown")

    # Parse date
    posts["date_posted"] = pd.to_datetime(posts["date_posted"], errors="coerce", utc=True)
    posts["year_month"]  = posts["date_posted"].dt.to_period("M").astype(str)

    # Detect language
    def safe_detect(text):
        try:
            return detect(text) if len(text.strip()) > 10 else "unknown"
        except LangDetectException:
            return "unknown"
    posts["lang"] = posts["description"].apply(safe_detect)
    return posts

st.divider()
st.header("📅 Posts Analysis")
st.caption("Source: existing_politician_posts.csv")

posts_df = load_posts()

# Date range info
min_d = posts_df["date_posted"].min()
max_d = posts_df["date_posted"].max()
n_unknown = (posts_df["Country"] == "Unknown").sum()
st.caption(
    f"Date range: **{min_d.date()}** → **{max_d.date()}** | "
    f"Total posts: **{len(posts_df):,}** | "
    f"Unmatched (no country): **{n_unknown:,}** ({n_unknown/len(posts_df)*100:.1f}%)"
)

# ── Temporal Distribution ─────────────────────────────────────────────────────
st.subheader("Posts Over Time")

country_opts = ["All"] + sorted(posts_df["Country"].dropna().unique().tolist())
sel_post_country = st.selectbox("Filter by country", country_opts, key="post_country")

temp_df = posts_df if sel_post_country == "All" else posts_df[posts_df["Country"] == sel_post_country]

monthly = (
    temp_df.dropna(subset=["date_posted"])
    .groupby(["year_month", "Country"])
    .size().reset_index(name="Posts")
    .sort_values("year_month")
)

fig_time = px.bar(
    monthly, x="year_month", y="Posts", color="Country",
    barmode="stack",
    color_discrete_sequence=px.colors.qualitative.Vivid,
    labels={"year_month": "Month", "Posts": "Post Count"},
)
fig_time.update_layout(margin=dict(t=20, b=60), xaxis_tickangle=45, legend_title="Country")
fig_time.update_xaxes(title="")
st.plotly_chart(fig_time, use_container_width=True)

# ── Language Distribution ─────────────────────────────────────────────────────
st.subheader("Language Distribution")

lang_country_opts = ["All"] + sorted(
    posts_df[posts_df["Country"] != "Unknown"]["Country"].unique().tolist()
)
sel_lang_country = st.selectbox("Filter by country", lang_country_opts, key="lang_country")

lang_filtered = posts_df if sel_lang_country == "All" else posts_df[posts_df["Country"] == sel_lang_country]

lc1, lc2 = st.columns(2)

with lc1:
    st.markdown(f"**Overall{' — ' + sel_lang_country if sel_lang_country != 'All' else ''}**")
    lang_overall = lang_filtered["lang"].value_counts().reset_index()
    lang_overall.columns = ["Language", "Count"]
    fig_lang = px.bar(
        lang_overall.head(15), x="Language", y="Count",
        color="Language",
        color_discrete_sequence=px.colors.qualitative.Vivid
    )
    fig_lang.update_layout(margin=dict(t=20, b=20), showlegend=False)
    st.plotly_chart(fig_lang, use_container_width=True)

with lc2:
    st.markdown("**By Country**")
    lang_country = (
        lang_filtered[lang_filtered["Country"] != "Unknown"]
        .groupby(["Country", "lang"])
        .size().reset_index(name="Count")
    )
    fig_lc = px.bar(
        lang_country, x="Country", y="Count", color="lang",
        barmode="stack",
        color_discrete_sequence=px.colors.qualitative.Pastel,
        labels={"lang": "Language"}
    )
    fig_lc.update_layout(margin=dict(t=20, b=20), legend_title="Language")
    st.plotly_chart(fig_lc, use_container_width=True)

# ── Cross-language communication flag ─────────────────────────────────────────
st.subheader("🌐 Cross-Language Posts")
st.caption("Posts where detected language doesn't match the expected language for that country.")

# Note: master_politicians uses full country names
EXPECTED = {
    "United States": "en",
    "Germany": "de",
    "Italy": "it",
    "Poland": "pl"
}
posts_df["expected_lang"] = posts_df["Country"].map(EXPECTED)
cross = posts_df[
    (posts_df["expected_lang"].notna()) &
    (posts_df["lang"] != posts_df["expected_lang"]) &
    (posts_df["lang"] != "unknown")
].copy()

cross_summary = (
    cross.groupby(["Country", "lang"])
    .size().reset_index(name="Count")
    .sort_values("Count", ascending=False)
)

st.dataframe(cross_summary, use_container_width=True, height=250)
st.caption(f"**{len(cross):,}** posts ({len(cross)/len(posts_df)*100:.1f}%) appear to be in a non-native language for that politician's country.")

# ── Random Tweet Sampler ──────────────────────────────────────────────────────
st.subheader("🎲 Random Tweet Sampler")
st.caption("Draw a random post from each country as a qualitative sanity check.")

if st.button("🔀 Draw new sample"):
    st.session_state["sample_seed"] = pd.Timestamp.now().microsecond

seed = st.session_state.get("sample_seed", 42)

sample_countries = [c for c in ["United States", "Germany", "Italy", "Poland"]
                    if c in posts_df["Country"].values]

for country in sample_countries:
    subset = posts_df[posts_df["Country"] == country].dropna(subset=["description"])
    subset = subset[subset["description"].str.strip() != ""]
    if subset.empty:
        continue
    row = subset.sample(1, random_state=seed).iloc[0]
    with st.expander(f"🌍 {country} — @{row.get('handle', 'unknown')} ({row.get('name', '')})", expanded=True):
        st.write(row["description"])
        col1, col2, col3 = st.columns(3)
        col1.caption(f"📅 {str(row['date_posted'])[:10]}")
        col2.caption(f"🌐 Detected lang: `{row.get('lang', 'unknown')}`")
        col3.caption(f"❤️ Likes: {row.get('likes', 'N/A')}")