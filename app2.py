import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io
import tempfile
from pathlib import Path
from datetime import date

st.set_page_config(
    page_title="Loan Progress Report",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; }

    /* Tab bar — no wrapping */
    div[data-testid="stTabs"] { width: 100%; }
    div[data-testid="stTabs"] > div:first-child {
        overflow-x: auto;
        white-space: nowrap;
        flex-wrap: nowrap !important;
    }
    div[data-testid="stTabs"] button {
        font-size: 13px !important;
        font-weight: 500;
        padding: 8px 16px !important;
        white-space: nowrap;
    }

    /* KPI cards */
    .kpi-card {
        background: #f8f9fb;
        border-radius: 10px;
        padding: 14px 18px;
        border-left: 4px solid #1976D2;
        margin-bottom: 4px;
    }
    .kpi-card.green  { border-left-color: #2e7d32; }
    .kpi-card.orange { border-left-color: #e65100; }
    .kpi-card.blue   { border-left-color: #1565c0; }
    .kpi-card.purple { border-left-color: #6a1b9a; }
    .kpi-label { font-size: 11px; color: #666; text-transform: uppercase; letter-spacing:.05em; }
    .kpi-val   { font-size: 24px; font-weight: 700; color: #1a1a1a; line-height: 1.2; }
    .kpi-sub   { font-size: 11px; color: #888; margin-top: 3px; }

    .section-hdr {
        font-size: 14px; font-weight: 600; color: #1a1a1a;
        border-bottom: 2px solid #1976D2;
        padding-bottom: 5px; margin: 14px 0 12px 0;
    }
    .info-box {
        background: #e3f2fd; border-radius: 8px;
        padding: 10px 14px; font-size: 13px; color: #1565c0;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────
def fmt_cr(val):
    if pd.isna(val) or val == 0:
        return "0"
    cr = val / 1e7
    if cr >= 1000:
        return f"Rs.{cr/1000:,.1f}K Cr"
    return f"Rs.{cr:,.2f} Cr"

def fmt_num(val):
    if pd.isna(val):
        return "0"
    return f"{int(val):,}"

def get_hierarchy_label(bank_type):
    bt = str(bank_type).upper()
    if any(x in bt for x in ["DCCB", "SCCB"]):
        return "DCCB/SCCB"
    elif "RRB" in bt:
        return "RRB"
    return "OTHER"

@st.cache_data(show_spinner=False)
def load_bank_details(file_bytes):
    df = pd.read_csv(io.BytesIO(file_bytes), encoding="utf-8", on_bad_lines="error")
    df.columns = df.columns.str.strip()
    return df

@st.cache_data(show_spinner=False)
def load_mis(file_bytes):
    df = pd.read_csv(io.BytesIO(file_bytes), encoding="utf-8", on_bad_lines="error")
    df.columns = df.columns.str.strip()

    date_cols = ["In-Principle Date", "Sanction Date", "Disbursement Date",
                 "Status Date", "Sanction Created Date", "Disbursement Created Date", "Closed Date"]
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(
                df[col].astype(str).str.strip(),
                errors="coerce",
                dayfirst=False,
            )

    numeric_cols = ["Total Loan Amount", "Sanction Amount", "Disbursement Amount"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(r'[^\d.]', '', regex=True),
                errors='coerce'
            ).fillna(0)
    return df

# ── Shared and bundled default datasets ─────────────────────────────────────────
PERSISTENT_DATA_DIR = Path(tempfile.gettempdir()) / "ekcc_dashboard_data"
PERSISTENT_DATA_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_BANK_PATH = PERSISTENT_DATA_DIR / "default_bank_details.csv"
DEFAULT_MIS_PATH = PERSISTENT_DATA_DIR / "default_mis_data.csv"

def persist_default_dataset(bank_bytes, mis_bytes):
    DEFAULT_BANK_PATH.write_bytes(bank_bytes)
    DEFAULT_MIS_PATH.write_bytes(mis_bytes)

@st.cache_data(show_spinner=False)
def load_persisted_datasets():
    if DEFAULT_BANK_PATH.exists() and DEFAULT_MIS_PATH.exists():
        bank_df = load_bank_details(DEFAULT_BANK_PATH.read_bytes())
        mis_df = load_mis(DEFAULT_MIS_PATH.read_bytes())
        return bank_df, mis_df
    return None, None

@st.cache_data(show_spinner=False)
def load_default_datasets():
    persisted = load_persisted_datasets()
    if persisted != (None, None):
        return persisted
    base = Path(__file__).parent
    bank_path = base / "sample_bank_details.csv"
    mis_path = base / "sample_mis_data.csv"
    if not bank_path.exists() or not mis_path.exists():
        return None, None
    bank_df = load_bank_details(bank_path.read_bytes())
    mis_df = load_mis(mis_path.read_bytes())
    return bank_df, mis_df

# ── Session state ─────────────────────────────────────────────────────────────
if "bank_df" not in st.session_state:
    st.session_state.bank_df = None
if "mis_df" not in st.session_state:
    st.session_state.mis_df = None

# ── Sidebar — UPLOAD ONLY ─────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Upload Data Files")
    st.markdown("Upload your own Bank and MIS CSV files, or leave both blank to use the bundled sample dataset.")
    bank_file = st.file_uploader("Bank User Details (CSV)", type=["csv"], key="bank_upload")
    mis_file  = st.file_uploader("MIS Loan Data (CSV)",     type=["csv"], key="mis_upload")
    save_default = st.checkbox("Save this upload as the shared default dataset for all visitors", key="save_default")

    if bank_file:
        if (st.session_state.get("bank_uploaded_name") != bank_file.name or
            st.session_state.get("bank_uploaded_size") != getattr(bank_file, "size", None)):
            st.session_state.bank_df = load_bank_details(bank_file.read())
            st.session_state.bank_uploaded_name = bank_file.name
            st.session_state.bank_uploaded_size = getattr(bank_file, "size", None)
        st.success(f"Bank details: {len(st.session_state.bank_df):,} rows")

    if mis_file:
        if (st.session_state.get("mis_uploaded_name") != mis_file.name or
            st.session_state.get("mis_uploaded_size") != getattr(mis_file, "size", None)):
            # Clear Streamlit cache to force fresh data load
            st.cache_data.clear()
            try:
                mis_bytes = mis_file.read()
                st.session_state.mis_df = load_mis(mis_bytes)
                st.session_state.mis_uploaded_name = mis_file.name
                st.session_state.mis_uploaded_size = getattr(mis_file, "size", None)
                st.session_state.upload_timestamp = pd.Timestamp.now()
                for key in ["gf_from", "gf_to", "gf_month", "gf_state", "gf_btype", "gf_bank", "t2_state", "zero_bank_filter", "drill_bank", "drill_region"]:
                    st.session_state.pop(key, None)
                if save_default and bank_file is not None and st.session_state.bank_df is not None:
                    persist_default_dataset(st.session_state.bank_df.to_csv(index=False).encode("utf-8"), mis_bytes)
                    st.success("Saved the uploaded files as the shared default dataset for this deployment.")
                st.success(f"✓ MIS file loaded fresh at {st.session_state.upload_timestamp.strftime('%H:%M:%S')}: {len(st.session_state.mis_df):,} rows")
            except Exception as e:
                st.error(f"Error loading MIS file: {str(e)}. Please check the CSV format and ensure no bad lines.")
                st.session_state.mis_df = None
        else:
            ts = getattr(st.session_state, 'upload_timestamp', 'unknown')
            st.info(f"Using cached file (loaded at {ts}): {len(st.session_state.mis_df):,} rows. Upload a different file to reload.")

bank_df = st.session_state.bank_df
mis_df  = st.session_state.mis_df

if bank_df is None and mis_df is None:
    default_bank_df, default_mis_df = load_default_datasets()
    if default_bank_df is not None and default_mis_df is not None:
        bank_df = default_bank_df
        mis_df = default_mis_df
        st.session_state.bank_df = bank_df
        st.session_state.mis_df = mis_df
        st.info("Loaded bundled sample dataset. Upload your own CSVs in the sidebar to replace it.")

# ── UPLOAD SCREEN ─────────────────────────────────────────────────────────────
if bank_df is None or mis_df is None:
    st.markdown("## Loan Progress Report Dashboard")
    st.markdown("""
    <div class='info-box'>
    Open the sidebar (arrow top-left) and upload both CSV files to get started.<br><br>
    <b>File 1:</b> Bank User Details &nbsp;&nbsp; <b>File 2:</b> MIS (Loan Data)
    </div>
    """, unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Bank User Details columns")
        st.code("BankId, BankName, EntityName, EntityCode\nHirarchyName, BankType, State, City\nEmailId, MobileNo, EmployeeName, AccessRight")
    with col2:
        st.markdown("#### MIS key columns")
        st.code("Loan Number, Product Type, Bank Type\nBank Name, Parent Office, Branch Name\nPACS Name, State, Total Loan Amount\nIn-Principle Date, Sanction Amount\nSanction Date, Disbursement Amount\nDisbursement Date")
    st.stop()

# ── GLOBAL FILTER BAR (above tabs, no sidebar) ────────────────────────────────
min_date = mis_df["In-Principle Date"].dropna().min()
max_date = mis_df["In-Principle Date"].dropna().max()
if pd.isna(min_date): min_date = date(2020, 1, 1)
if pd.isna(max_date): max_date = date.today()
min_date = min_date.date() if hasattr(min_date, "date") else min_date
max_date = max_date.date() if hasattr(max_date, "date") else max_date

months_avail = sorted(mis_df["In-Principle Date"].dropna().dt.to_period("M").unique())
month_labels = ["All"] + [str(m) for m in months_avail]
states_avail = ["All"] + sorted(mis_df["State"].dropna().unique().tolist())
btypes_avail = ["All"] + sorted(mis_df["Bank Type"].dropna().unique().tolist())
bnames_avail = ["All"] + sorted(bank_df["BankName"].dropna().unique().tolist())

st.markdown("### Loan Progress Report")
fc1, fc2, fc3, fc4, fc5, fc6 = st.columns([1.3, 1.3, 1.2, 1.8, 1.6, 2.0])
with fc1:
    d_from = st.date_input("From Date", value=min_date, key="gf_from",
                            min_value=min_date, max_value=max_date)
with fc2:
    d_to   = st.date_input("To Date",   value=max_date, key="gf_to",
                            min_value=min_date, max_value=max_date)
with fc3:
    sel_month = st.selectbox("Month", month_labels, key="gf_month")
with fc4:
    sel_state = st.selectbox("State", states_avail, key="gf_state")
with fc5:
    sel_btype = st.selectbox("Bank Type", btypes_avail, key="gf_btype")
with fc6:
    sel_bank  = st.selectbox("Bank Name", bnames_avail, key="gf_bank")

st.markdown("<hr style='margin:6px 0 10px 0;border-color:#e2e8f0'>", unsafe_allow_html=True)

# ── Apply global filters ───────────────────────────────────────────────────────
fmis = mis_df.copy()

fmis = fmis[
    (fmis["In-Principle Date"].isna()) |
    ((fmis["In-Principle Date"].dt.date >= d_from) &
     (fmis["In-Principle Date"].dt.date <= d_to))
]
if sel_month != "All":
    fmis = fmis[fmis["In-Principle Date"].dt.to_period("M").astype(str) == sel_month]
if sel_state != "All":
    fmis = fmis[fmis["State"] == sel_state]
if sel_btype != "All":
    fmis = fmis[fmis["Bank Type"] == sel_btype]
if sel_bank != "All":
    fmis = fmis[fmis["Bank Name"] == sel_bank]

# ── TABS ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "  Overview  ",
    "  State-wise Summary  ",
    "  Zero Loan Report  ",
    "  Bank-wise Drill-down  ",
    "  Monthly Progress Report  ",
])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    # In-Principle count = total rows (every MIS row = 1 in-principle loan), amount = sum of all Total Loan Amount
    inprinciple_count = len(mis_df)
    inprinciple_amt   = mis_df["Total Loan Amount"].sum()
    sanction_count    = mis_df["Sanction Date"].notna().sum()
    sanction_amt      = mis_df.loc[mis_df["Sanction Date"].notna(), "Sanction Amount"].sum()
    disb_count        = mis_df["Disbursement Date"].notna().sum()
    disb_amt          = mis_df.loc[mis_df["Disbursement Date"].notna(), "Disbursement Amount"].sum()
    conv              = (sanction_count / inprinciple_count * 100) if inprinciple_count > 0 else 0

    st.markdown('<div class="section-hdr">Overall KPIs</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div class='kpi-card blue'>
            <div class='kpi-label'>In-Principle (Total Loans)</div>
            <div class='kpi-val'>{fmt_num(inprinciple_count)}</div>
            <div class='kpi-sub'>Total Loan Amount: {fmt_cr(inprinciple_amt)}</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class='kpi-card orange'>
            <div class='kpi-label'>Sanctioned</div>
            <div class='kpi-val'>{fmt_num(sanction_count)}</div>
            <div class='kpi-sub'>{fmt_cr(sanction_amt)}</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class='kpi-card green'>
            <div class='kpi-label'>Disbursed</div>
            <div class='kpi-val'>{fmt_num(disb_count)}</div>
            <div class='kpi-sub'>{fmt_cr(disb_amt)}</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class='kpi-card purple'>
            <div class='kpi-label'>Sanction Conversion</div>
            <div class='kpi-val'>{conv:.1f}%</div>
            <div class='kpi-sub'>In-Principle to Sanctioned</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("")

    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown('<div class="section-hdr">Loan Pipeline Funnel</div>', unsafe_allow_html=True)
        fig_funnel = go.Figure(go.Funnel(
            y=["In-Principle", "Sanctioned", "Disbursed"],
            x=[inprinciple_count, sanction_count, disb_count],
            textinfo="value+percent initial",
            marker=dict(color=["#1565c0", "#e65100", "#2e7d32"]),
            connector=dict(line=dict(color="#ccc", width=1))
        ))
        fig_funnel.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=280)
        st.plotly_chart(fig_funnel, use_container_width=True)

    with col_right:
        st.markdown('<div class="section-hdr">Product Type Breakdown</div>', unsafe_allow_html=True)
        if "Product Type" in fmis.columns:
            pt = fmis.groupby("Product Type").size().reset_index(name="Count")
            pt = pt.sort_values("Count", ascending=True)
            fig_pt = px.bar(pt, x="Count", y="Product Type", orientation="h",
                            color="Count", color_continuous_scale="Blues")
            fig_pt.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=280,
                                 coloraxis_showscale=False, yaxis_title="")
            st.plotly_chart(fig_pt, use_container_width=True)

    st.markdown('<div class="section-hdr">Monthly Loan Trend</div>', unsafe_allow_html=True)
    trend = fmis[fmis["In-Principle Date"].notna()].copy()
    trend["Month"] = trend["In-Principle Date"].dt.to_period("M").astype(str)
    monthly = trend.groupby("Month").agg(
        InPrinciple=("In-Principle Date", "count"),
        Sanctioned =("Sanction Date", "count"),
        Disbursed  =("Disbursement Date", "count"),
    ).reset_index().sort_values("Month")

    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(x=monthly["Month"], y=monthly["InPrinciple"],
                                   name="In-Principle", mode="lines+markers",
                                   line=dict(color="#1565c0", width=2)))
    fig_trend.add_trace(go.Scatter(x=monthly["Month"], y=monthly["Sanctioned"],
                                   name="Sanctioned", mode="lines+markers",
                                   line=dict(color="#e65100", width=2)))
    fig_trend.add_trace(go.Scatter(x=monthly["Month"], y=monthly["Disbursed"],
                                   name="Disbursed", mode="lines+markers",
                                   line=dict(color="#2e7d32", width=2)))
    fig_trend.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=260,
                            legend=dict(orientation="h", y=1.12),
                            xaxis_title="", yaxis_title="Count")
    st.plotly_chart(fig_trend, use_container_width=True)

    st.markdown('<div class="section-hdr">Bank Type Comparison</div>', unsafe_allow_html=True)
    if "Bank Type" in fmis.columns:
        btc = fmis.groupby("Bank Type").agg(
            InPrinciple=("In-Principle Date", "count"),
            Sanctioned =("Sanction Date",  "count"),
            Disbursed  =("Disbursement Date", "count"),
        ).reset_index()
        fig_bt = go.Figure()
        fig_bt.add_trace(go.Bar(x=btc["Bank Type"], y=btc["InPrinciple"],
                                name="In-Principle", marker_color="#1565c0"))
        fig_bt.add_trace(go.Bar(x=btc["Bank Type"], y=btc["Sanctioned"],
                                name="Sanctioned", marker_color="#e65100"))
        fig_bt.add_trace(go.Bar(x=btc["Bank Type"], y=btc["Disbursed"],
                                name="Disbursed", marker_color="#2e7d32"))
        fig_bt.update_layout(barmode="group", height=260,
                             margin=dict(l=10, r=10, t=10, b=10),
                             legend=dict(orientation="h", y=1.12),
                             xaxis_title="", yaxis_title="Count")
        st.plotly_chart(fig_bt, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — STATE-WISE SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown('<div class="section-hdr">State x Bank Type x Bank Name Summary</div>',
                unsafe_allow_html=True)

    # In-Principle Count = count of rows (each row = 1 loan)
    summary = fmis.groupby(["State", "Bank Type", "Bank Name"]).agg(
        InPrinciple_Count  =("In-Principle Date",  "count"),
        Total_Loan_Amount  =("Total Loan Amount",   "sum"),
        Sanction_Count     =("Sanction Date",       "count"),
        Sanction_Amount    =("Sanction Amount",     "sum"),
        Disbursement_Count =("Disbursement Date",   "count"),
        Disbursement_Amount=("Disbursement Amount", "sum"),
    ).reset_index()

    summary["Total Loan Amt (Cr)"] = (summary["Total_Loan_Amount"]    / 1e7).round(2)
    summary["Sanction Amt (Cr)"]   = (summary["Sanction_Amount"]      / 1e7).round(2)
    summary["Disburse Amt (Cr)"]   = (summary["Disbursement_Amount"]  / 1e7).round(2)

    disp = summary.rename(columns={
        "InPrinciple_Count":   "In-Principle (Count)",
        "Sanction_Count":      "Sanction (Count)",
        "Disbursement_Count":  "Disbursement (Count)",
    })[[
        "State", "Bank Type", "Bank Name",
        "In-Principle (Count)", "Total Loan Amt (Cr)",
        "Sanction (Count)", "Sanction Amt (Cr)",
        "Disbursement (Count)", "Disburse Amt (Cr)",
    ]]

    t2_states = ["All"] + sorted(disp["State"].dropna().unique().tolist())
    sel_t2_state = st.selectbox("Filter by State", t2_states, key="t2_state")
    if sel_t2_state != "All":
        disp = disp[disp["State"] == sel_t2_state]

    st.dataframe(
        disp.style.background_gradient(
            subset=["In-Principle (Count)", "Sanction (Count)", "Disbursement (Count)"],
            cmap="Blues"
        ),
        use_container_width=True, height=420
    )
    c_dl, _ = st.columns([1, 5])
    with c_dl:
        st.download_button("Download CSV",
                           disp.to_csv(index=False).encode("utf-8"),
                           "state_wise_summary.csv", "text/csv")

    st.markdown('<div class="section-hdr">State-wise In-Principle Count (Top 20)</div>',
                unsafe_allow_html=True)
    sg = fmis[fmis["In-Principle Date"].notna()].groupby("State").size().reset_index(name="Count")
    sg = sg.sort_values("Count", ascending=False).head(20)
    fig_sg = px.bar(sg, x="State", y="Count", color="Count",
                    color_continuous_scale="Blues")
    fig_sg.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10),
                         coloraxis_showscale=False, xaxis_tickangle=-30)
    st.plotly_chart(fig_sg, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — ZERO LOAN REPORT
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown('<div class="section-hdr">Zero Loan Report</div>', unsafe_allow_html=True)
    st.markdown("""<div class='info-box'>
    Compares <b>Bank User Details</b> (all onboarded banks/branches) against <b>MIS</b> (loans received).
    Only <b>Branch-level</b> entities are checked for zero loans (not PACS or Region).
    </div>""", unsafe_allow_html=True)

    # ── Data prep (always from full bank_df and full mis_df for onboarding counts) ──
    branch_rows = bank_df[bank_df["HirarchyName"].str.lower().str.contains("branch", na=False)].copy()

    all_banks  = set(bank_df["BankName"].dropna().unique())
    mis_banks  = set(fmis["Bank Name"].dropna().unique())
    zero_banks = all_banks - mis_banks

    # Prepare full branch list
    all_branches = branch_rows[["BankName", "BankType", "EntityName", "State"]].copy()
    all_branches.columns = ["Bank Name", "Bank Type", "Branch Name", "State"]
    all_branches = all_branches.dropna(subset=["Branch Name"])
    all_branches["Branch Name"] = all_branches["Branch Name"].str.strip()

    mis_branch_names = set()
    if "Branch Name" in fmis.columns:
        mis_branch_names.update(fmis["Branch Name"].dropna().str.strip().unique())
    if "Parent Office" in fmis.columns:
        mis_branch_names.update(fmis["Parent Office"].dropna().str.strip().unique())

    all_branches["Has Loan"] = all_branches["Branch Name"].isin(mis_branch_names)
    zero_branches_all = all_branches[~all_branches["Has Loan"]].drop(columns=["Has Loan"])

    # ── SECTION A: Bank-level zero ───────────────────────────────────────────
    st.markdown("#### Banks with Zero Loans")
    kc1, kc2, kc3 = st.columns(3)
    kc1.metric("Total Banks Onboarded",  len(all_banks))
    kc2.metric("Banks with Loans",       len(mis_banks))
    kc3.metric("Banks with ZERO Loans",  len(zero_banks))

    if zero_banks:
        zb_df = bank_df[bank_df["BankName"].isin(zero_banks)][
            ["BankName", "BankType", "State"]
        ].drop_duplicates().rename(columns={"BankName": "Bank Name", "BankType": "Bank Type"})
        st.dataframe(zb_df.reset_index(drop=True), use_container_width=True)
        st.download_button("Download Zero-Loan Banks",
                           zb_df.to_csv(index=False).encode("utf-8"),
                           "zero_banks.csv", "text/csv")
    else:
        st.success("All onboarded banks have at least one loan in MIS.")

    st.markdown("---")

    # ── SECTION B: Branch-level zero — FIX 4 ────────────────────────────────
    st.markdown("#### Branches with Zero Loans")
    st.caption("Select a bank to see its specific zero-loan branches. Metrics update to that bank's scope.")

    zb_filter_banks = ["All"] + sorted(all_branches["Bank Name"].dropna().unique().tolist())
    sel_zb_bank = st.selectbox("Filter by Bank", zb_filter_banks, key="zero_bank_filter")

    if sel_zb_bank == "All":
        branches_scope = all_branches
        zero_branches  = zero_branches_all
    else:
        # FIX 4: Total count = branches of THAT bank only
        branches_scope = all_branches[all_branches["Bank Name"] == sel_zb_bank]
        zero_branches  = zero_branches_all[zero_branches_all["Bank Name"] == sel_zb_bank]

    total_in_scope    = len(branches_scope)
    zero_branch_count = len(zero_branches)
    pct = zero_branch_count / total_in_scope * 100 if total_in_scope > 0 else 0

    zc1, zc2, zc3 = st.columns(3)
    zc1.metric("Total Branches (this scope)", total_in_scope)
    zc2.metric("Zero-Loan Branches",          zero_branch_count)
    zc3.metric("Zero Loan %",                 f"{pct:.1f}%")

    if not zero_branches.empty:
        st.dataframe(zero_branches.reset_index(drop=True), use_container_width=True, height=360)
        st.download_button("Download Zero-Loan Branches",
                           zero_branches.to_csv(index=False).encode("utf-8"),
                           "zero_branches.csv", "text/csv")

        if sel_zb_bank == "All":
            st.markdown('<div class="section-hdr">Top Banks by Zero-Loan Branches</div>',
                        unsafe_allow_html=True)
            top_zb = zero_branches.groupby("Bank Name").size().reset_index(name="Zero Branches")
            top_zb = top_zb.sort_values("Zero Branches", ascending=False).head(20)
            fig_zb = px.bar(top_zb, x="Bank Name", y="Zero Branches",
                            color="Zero Branches", color_continuous_scale="Reds")
            fig_zb.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10),
                                 coloraxis_showscale=False, xaxis_tickangle=-30)
            st.plotly_chart(fig_zb, use_container_width=True)
    else:
        st.success("All branches in this scope have at least one loan in MIS.")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — BANK-WISE DRILL-DOWN  (FIX 5: zero-loan section added)
# ═══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown('<div class="section-hdr">Bank-wise Drill-down</div>', unsafe_allow_html=True)

    all_bank_names = sorted(fmis["Bank Name"].dropna().unique().tolist())
    if not all_bank_names:
        st.warning("No banks found in filtered MIS data.")
        st.stop()

    sel_drill_bank = st.selectbox("Select a Bank", all_bank_names, key="drill_bank")
    bank_mis = fmis[fmis["Bank Name"] == sel_drill_bank].copy()
    detected_bt    = bank_mis["Bank Type"].mode()[0] if not bank_mis.empty else ""
    hierarchy_type = get_hierarchy_label(detected_bt)

    # Bank KPIs
    bk1, bk2, bk3, bk4 = st.columns(4)
    with bk1:
        st.markdown(f"""<div class='kpi-card blue'>
            <div class='kpi-label'>In-Principle (Total Loans)</div>
            <div class='kpi-val'>{fmt_num(bank_mis["In-Principle Date"].notna().sum())}</div>
            <div class='kpi-sub'>Total Loan Amt: {fmt_cr(bank_mis.loc[bank_mis["In-Principle Date"].notna(), "Total Loan Amount"].sum())}</div>
        </div>""", unsafe_allow_html=True)
    with bk2:
        st.markdown(f"""<div class='kpi-card orange'>
            <div class='kpi-label'>Sanctioned</div>
            <div class='kpi-val'>{fmt_num(bank_mis["Sanction Date"].notna().sum())}</div>
            <div class='kpi-sub'>{fmt_cr(bank_mis["Sanction Amount"].sum())}</div>
        </div>""", unsafe_allow_html=True)
    with bk3:
        st.markdown(f"""<div class='kpi-card green'>
            <div class='kpi-label'>Disbursed</div>
            <div class='kpi-val'>{fmt_num(bank_mis["Disbursement Date"].notna().sum())}</div>
            <div class='kpi-sub'>{fmt_cr(bank_mis["Disbursement Amount"].sum())}</div>
        </div>""", unsafe_allow_html=True)
    with bk4:
        st.markdown(f"""<div class='kpi-card purple'>
            <div class='kpi-label'>Bank Type</div>
            <div class='kpi-val'>{detected_bt}</div>
            <div class='kpi-sub'>Hierarchy: {hierarchy_type}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("")

    # FIX 5: Zero-loan branches for this bank
    with st.expander("Zero-Loan Branches in this Bank", expanded=False):
        bank_branches_ud = bank_df[
            (bank_df["BankName"] == sel_drill_bank) &
            (bank_df["HirarchyName"].str.lower().str.contains("branch", na=False))
        ][["EntityName", "State"]].copy()
        bank_branches_ud.columns = ["Branch Name", "State"]
        bank_branches_ud["Branch Name"] = bank_branches_ud["Branch Name"].str.strip()

        mis_bnames_bank = set()
        if "Branch Name" in bank_mis.columns:
            mis_bnames_bank.update(bank_mis["Branch Name"].dropna().str.strip().unique())
        if "Parent Office" in bank_mis.columns:
            mis_bnames_bank.update(bank_mis["Parent Office"].dropna().str.strip().unique())

        bank_branches_ud["Has Loan"] = bank_branches_ud["Branch Name"].isin(mis_bnames_bank)
        zero_b = bank_branches_ud[~bank_branches_ud["Has Loan"]].drop(columns=["Has Loan"])

        total_b = len(bank_branches_ud)
        zero_b_count = len(zero_b)
        pct_b = zero_b_count / total_b * 100 if total_b > 0 else 0

        zb1, zb2, zb3 = st.columns(3)
        zb1.metric("Branches Onboarded",  total_b)
        zb2.metric("Zero-Loan Branches",  zero_b_count)
        zb3.metric("Zero %",              f"{pct_b:.1f}%")

        if not zero_b.empty:
            st.dataframe(zero_b.reset_index(drop=True), use_container_width=True, height=240)
            st.download_button(f"Download Zero Branches for {sel_drill_bank}",
                               zero_b.to_csv(index=False).encode("utf-8"),
                               f"zero_branches_{sel_drill_bank}.csv", "text/csv")
        else:
            st.success("All branches of this bank have loans in MIS.")

    st.markdown("")

    # Hierarchy loan tables
    if hierarchy_type == "DCCB/SCCB":
        st.markdown(f"#### Branch-level Summary &nbsp;<small style='color:#888'>({detected_bt} — Parent Office = Branch)</small>",
                    unsafe_allow_html=True)
        branch_grp = bank_mis.groupby("Parent Office").agg(
            InPrinciple    =("In-Principle Date", "count"),
            Total_Loan_Amt =("Total Loan Amount",  "sum"),
            Sanctioned     =("Sanction Date",      "count"),
            Sanction_Amt   =("Sanction Amount",    "sum"),
            Disbursed      =("Disbursement Created Date",  "count"),
            Disb_Amt       =("Disbursement Amount","sum"),
        ).reset_index().rename(columns={"Parent Office": "Branch"})
        branch_grp["Loan Amt (Cr)"]    = (branch_grp["Total_Loan_Amt"] / 1e7).round(2)
        branch_grp["Sanction Amt (Cr)"]= (branch_grp["Sanction_Amt"]   / 1e7).round(2)
        branch_grp["Disb Amt (Cr)"]    = (branch_grp["Disb_Amt"]       / 1e7).round(2)
        st.dataframe(
            branch_grp[["Branch", "InPrinciple", "Loan Amt (Cr)",
                         "Sanctioned", "Sanction Amt (Cr)",
                         "Disbursed", "Disb Amt (Cr)"]
            ].sort_values("InPrinciple", ascending=False).reset_index(drop=True),
            use_container_width=True, height=340
        )

        st.markdown("#### PACS-level Detail")
        pacs_data = bank_mis[
            bank_mis["PACS Name"].notna() &
            (bank_mis["PACS Name"].str.strip().str.lower().isin(["", "nan"]) == False)
        ]
        if not pacs_data.empty:
            pacs_grp = pacs_data.groupby(["Parent Office", "PACS Name"]).agg(
                InPrinciple=("In-Principle Date",       "count"),
                Sanctioned =("Sanction Date",     "count"),
                Disbursed  =("Disbursement Created Date", "count"),
                Loan_Amt   =("Total Loan Amount", "sum"),
            ).reset_index().rename(columns={"Parent Office": "Branch", "PACS Name": "PACS"})
            pacs_grp["Loan Amt (Cr)"] = (pacs_grp["Loan_Amt"] / 1e7).round(2)
            st.dataframe(
                pacs_grp[["Branch", "PACS", "InPrinciple", "Sanctioned", "Disbursed", "Loan Amt (Cr)"]
                ].sort_values("InPrinciple", ascending=False).reset_index(drop=True),
                use_container_width=True, height=300
            )
        else:
            st.info("No PACS-level loans found for this bank in current filter.")

    else:  # RRB
        st.markdown(f"#### Region-level Summary &nbsp;<small style='color:#888'>(RRB — Parent Office = Region)</small>",
                    unsafe_allow_html=True)
        region_grp = bank_mis.groupby("Parent Office").agg(
            InPrinciple    =("In-Principle Date", "count"),
            Total_Loan_Amt =("Total Loan Amount",  "sum"),
            Sanctioned     =("Sanction Date",      "count"),
            Sanction_Amt   =("Sanction Amount",    "sum"),
            Disbursed      =("Disbursement Created Date",  "count"),
            Disb_Amt       =("Disbursement Amount","sum"),
        ).reset_index().rename(columns={"Parent Office": "Region"})
        region_grp["Loan Amt (Cr)"]    = (region_grp["Total_Loan_Amt"] / 1e7).round(2)
        region_grp["Sanction Amt (Cr)"]= (region_grp["Sanction_Amt"]   / 1e7).round(2)
        region_grp["Disb Amt (Cr)"]    = (region_grp["Disb_Amt"]       / 1e7).round(2)
        st.dataframe(
            region_grp[["Region", "InPrinciple", "Loan Amt (Cr)",
                         "Sanctioned", "Sanction Amt (Cr)",
                         "Disbursed", "Disb Amt (Cr)"]
            ].sort_values("InPrinciple", ascending=False).reset_index(drop=True),
            use_container_width=True, height=280
        )

        st.markdown("#### Branch-level Detail")
        regions_list = ["All"] + sorted(bank_mis["Parent Office"].dropna().unique().tolist())
        sel_region = st.selectbox("Select Region", regions_list, key="drill_region")
        bd = bank_mis if sel_region == "All" else bank_mis[bank_mis["Parent Office"] == sel_region]
        branch_grp2 = bd.groupby(["Parent Office", "Branch Name"]).agg(
            InPrinciple=("In-Principle Date",       "count"),
            Sanctioned =("Sanction Date",     "count"),
            Disbursed  =("Disbursement Created Date", "count"),
            Loan_Amt   =("Total Loan Amount", "sum"),
        ).reset_index().rename(columns={"Parent Office": "Region", "Branch Name": "Branch"})
        branch_grp2["Loan Amt (Cr)"] = (branch_grp2["Loan_Amt"] / 1e7).round(2)
        st.dataframe(
            branch_grp2[["Region", "Branch", "InPrinciple", "Sanctioned", "Disbursed", "Loan Amt (Cr)"]
            ].sort_values("InPrinciple", ascending=False).reset_index(drop=True),
            use_container_width=True, height=300
        )

    # Funnel + Product pie
    st.markdown('<div class="section-hdr">Bank Pipeline and Product Mix</div>', unsafe_allow_html=True)
    cf, cp = st.columns(2)
    with cf:
        fig_bf = go.Figure(go.Funnel(
            y=["In-Principle", "Sanctioned", "Disbursed"],
            x=[bank_mis["In-Principle Date"].notna().sum(),
               bank_mis["Sanction Date"].notna().sum(),
               bank_mis["Disbursement Created Date"].notna().sum()],
            textinfo="value+percent initial",
            marker=dict(color=["#1565c0", "#e65100", "#2e7d32"])
        ))
        fig_bf.update_layout(height=250, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_bf, use_container_width=True)
    with cp:
        if "Product Type" in bank_mis.columns:
            pt2 = bank_mis.groupby("Product Type").size().reset_index(name="Count")
            fig_pie = px.pie(pt2, names="Product Type", values="Count",
                             color_discrete_sequence=px.colors.qualitative.Set2, hole=0.35)
            fig_pie.update_layout(height=250, margin=dict(l=10, r=10, t=10, b=10),
                                  legend=dict(orientation="h", y=-0.2))
            st.plotly_chart(fig_pie, use_container_width=True)

    st.download_button(f"Download MIS data for {sel_drill_bank}",
                       bank_mis.to_csv(index=False).encode("utf-8"),
                       f"{sel_drill_bank}_mis.csv", "text/csv")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 5 — MONTHLY PROGRESS REPORT (Word Download)
# ═══════════════════════════════════════════════════════════════════════════════
import json, subprocess, tempfile, calendar
from pathlib import Path

def last_day(year, month):
    return date(year, month, calendar.monthrange(year, month)[1])

def month_label(year, month):
    return date(year, month, 1).strftime("%B %Y")   # "March 2026"

def month_end_label(year, month):
    d = last_day(year, month)
    return f"{d.day} {d.strftime('%B %Y')}"  # cross-platform

def snapshot(df, year, month):
    """Cumulative stats for all records where In-Principle Date <= end of given month."""
    eom = pd.Timestamp(last_day(year, month))

    # In-Principle snapshot: all rows where IP date <= eom  (or IP date is null — excluded from cumulative)
    ip_df  = df[df["In-Principle Date"].notna() & (df["In-Principle Date"] <= eom)]
    san_df = df[df["Sanction Date"].notna()      & (df["Sanction Date"]      <= eom)]
    dis_df = df[df["Disbursement Created Date"].notna()  & (df["Disbursement Created Date"]  <= eom)]

    return {
        "ip_count":       int(len(ip_df)),
        "ip_amt":         float(ip_df["Total Loan Amount"].sum()),
        "sanction_count": int(san_df["Sanction Date"].notna().sum()),
        "sanction_amt":   float(san_df["Sanction Amount"].sum()),
        "disb_count":     int(dis_df["Disbursement Created Date"].notna().sum()),
        "disb_amt":       float(dis_df["Disbursement Amount"].sum()),
        "active_states":  int(ip_df["State"].nunique()),
        "active_banks":   int(ip_df["Bank Name"].nunique()),
        "zero_banks":     int(len(set(bank_df["BankName"].dropna().unique()) - set(ip_df["Bank Name"].dropna().unique()))),
    }

def top_states(df, bank_df_ref, y1, m1, y2, m2, n=10):
    eom1 = pd.Timestamp(last_day(y1, m1))
    eom2 = pd.Timestamp(last_day(y2, m2))
    ip1  = df[df["In-Principle Date"].notna() & (df["In-Principle Date"] <= eom1)]
    ip2  = df[df["In-Principle Date"].notna() & (df["In-Principle Date"] <= eom2)]

    s1 = ip1.groupby("State").agg(count=("Loan Number","count"), amt=("Total Loan Amount","sum")).reset_index()
    s2 = ip2.groupby("State").agg(count=("Loan Number","count"), amt=("Total Loan Amount","sum")).reset_index()
    merged = s2.merge(s1, on="State", how="left", suffixes=("_m2","_m1"))
    merged = merged.sort_values("count_m2", ascending=False).head(n)
    merged = merged.reset_index(drop=True)
    out = []
    for i, (_, row) in enumerate(merged.iterrows(), 1):
        out.append({
            "rank":     i,
            "state":    str(row["State"]),
            "m1_count": int(row["count_m1"]) if pd.notna(row.get("count_m1")) else 0,
            "m2_count": int(row["count_m2"]),
            "m2_amt":   float(row["amt_m2"]),
        })
    return out

def top_banks(df, bank_df_ref, y1, m1, y2, m2, n=15):
    eom1 = pd.Timestamp(last_day(y1, m1))
    eom2 = pd.Timestamp(last_day(y2, m2))
    ip1  = df[df["In-Principle Date"].notna() & (df["In-Principle Date"] <= eom1)]
    ip2  = df[df["In-Principle Date"].notna() & (df["In-Principle Date"] <= eom2)]

    b1 = ip1.groupby("Bank Name").agg(count=("Loan Number","count")).reset_index()
    b2 = ip2.groupby("Bank Name").agg(count=("Loan Number","count")).reset_index()

    # Get bank type and state from bank_df_ref
    bank_meta = bank_df_ref[["BankName","BankType","State"]].drop_duplicates("BankName")

    merged = b2.merge(b1, on="Bank Name", how="left", suffixes=("_m2","_m1"))
    merged = merged.merge(bank_meta, left_on="Bank Name", right_on="BankName", how="left")
    merged = merged.sort_values("count_m2", ascending=False).head(n)
    merged = merged.reset_index(drop=True)

    out = []
    for i, (_, row) in enumerate(merged.iterrows(), 1):
        m1c = int(row["count_m1"]) if pd.notna(row.get("count_m1")) else 0
        out.append({
            "rank":     i,
            "type":     str(row["BankType"]) if pd.notna(row.get("BankType")) else "",
            "name":     str(row["Bank Name"]) if pd.notna(row.get("Bank Name")) else "",
            "state":    str(row["State"]) if pd.notna(row.get("State")) else "",
            "m1_count": m1c,
            "m2_count": int(row["count_m2"]),
            "tag":      "New" if m1c == 0 else "",
        })
    return out

def band_distribution(df, y1, m1, y2, m2):
    eom1 = pd.Timestamp(last_day(y1, m1))
    eom2 = pd.Timestamp(last_day(y2, m2))

    ip1 = df[df["In-Principle Date"].notna() & (df["In-Principle Date"] <= eom1)]
    ip2 = df[df["In-Principle Date"].notna() & (df["In-Principle Date"] <= eom2)]

    b1 = ip1.groupby("Bank Name").agg(count=("Loan Number","count"))
    b2 = ip2.groupby("Bank Name").agg(count=("Loan Number","count"))

    def assign_band(c):
        if c >= 10000: return "10,000 or more"
        elif c >= 5000: return "5,000 – 10,000"
        elif c >= 1000: return "1,000 – 5,000"
        elif c >= 100:  return "100 – 1,000"
        else:           return "Less than 100"

    band_order = ["10,000 or more","5,000 – 10,000","1,000 – 5,000","100 – 1,000","Less than 100"]

    b1["band"] = b1["count"].apply(assign_band)
    b2["band"] = b2["count"].apply(assign_band)
    cnt1 = b1.groupby("band")["count"].count().reindex(band_order, fill_value=0)
    cnt2 = b2.groupby("band")["count"].count().reindex(band_order, fill_value=0)

    out = []
    for band in band_order:
        c1, c2 = int(cnt1.get(band, 0)), int(cnt2.get(band, 0))
        diff = c2 - c1
        note = ""
        if diff > 0:  note = f"(+{diff} banks promoted)"
        elif diff < 0: note = f"(-{abs(diff)} banks graduated up)"
        out.append({"band": band, "m1_count": c1, "m2_count": c2, "note": note})

    out.append({
        "band": "Total active banks",
        "m1_count": int(b1.shape[0]),
        "m2_count": int(b2.shape[0]),
        "note": ""
    })
    return out

def standout_performers(df, y1, m1, y2, m2, n=4):
    eom1 = pd.Timestamp(last_day(y1, m1))
    eom2 = pd.Timestamp(last_day(y2, m2))
    ip1  = df[df["In-Principle Date"].notna() & (df["In-Principle Date"] <= eom1)]
    ip2  = df[df["In-Principle Date"].notna() & (df["In-Principle Date"] <= eom2)]
    b1 = ip1.groupby("Bank Name").agg(count=("Loan Number","count")).reset_index()
    b2 = ip2.groupby("Bank Name").agg(count=("Loan Number","count")).reset_index()
    merged = b2.merge(b1, on="Bank Name", how="left", suffixes=("_m2","_m1"))
    merged["diff"] = merged["count_m2"] - merged["count_m1"].fillna(0)
    merged = merged.sort_values("diff", ascending=False).head(n)
    out = []
    for _, row in merged.iterrows():
        m1c = int(row["count_m1"]) if pd.notna(row.get("count_m1")) else 0
        diff = int(row["diff"])
        prefix = "+" if diff >= 0 else ""
        if m1c == 0:
            note = f"+{int(row['count_m2']):,} applications — fresh activation from zero in {month_label(y1,m1)}."
        else:
            note = f"{prefix}{diff:,} applications."
        out.append({"name": str(row["Bank Name"]), "note": note})
    return out

def build_report_json(y1, m1, y2, m2):
    ml1, ml2 = month_label(y1,m1), month_label(y2,m2)
    me1, me2 = month_end_label(y1,m1), month_end_label(y2,m2)

    sn1 = snapshot(mis_df, y1, m1)
    sn2 = snapshot(mis_df, y2, m2)

    zero_count = sn2["zero_banks"]
    zero_note  = f"{zero_count} contracted banks have yet to record their first application in {ml2}. BankBenchers continues to pursue activation and requests NABARD facilitation in accordance with Clause 2.2 of the Licensing Agreement."

    # report_date = month AFTER m2
    import calendar as _cal
    if m2 == 12: ry, rm = y2+1, 1
    else:         ry, rm = y2, m2+1
    rdate = date(ry, rm, 1).strftime("%B %Y")

    return {
        "m1_label":    ml1,
        "m2_label":    ml2,
        "m1_end":      me1,
        "m2_end":      me2,
        "report_date": rdate,
        "zero_banks_note": zero_note,
        "snapshot": {"m1": sn1, "m2": sn2},
        "top_states": top_states(mis_df, bank_df, y1, m1, y2, m2),
        "bands":      band_distribution(mis_df, y1, m1, y2, m2),
        "top_banks":  top_banks(mis_df, bank_df, y1, m1, y2, m2),
        "standouts":  standout_performers(mis_df, y1, m1, y2, m2),
    }

with tab5:
    st.markdown('<div class="section-hdr">Monthly Progress Report — Word Download</div>',
                unsafe_allow_html=True)
    st.markdown("""<div class='info-box'>
    Select two months to compare. The report will generate a Word document matching the
    <b>eKCC Progress Report</b> template — covering At-a-Glance, Geographic Reach,
    Top 10 States, Bank Application Bands, and Top 15 Banks with standout commentary.
    </div>""", unsafe_allow_html=True)

    # Month selectors
    all_months = sorted(mis_df["In-Principle Date"].dropna().dt.to_period("M").unique())
    all_month_strs = [str(m) for m in all_months]

    if len(all_month_strs) < 2:
        st.warning("Not enough months in MIS data to compare.")
    else:
        rc1, rc2, rc3 = st.columns([1.5, 1.5, 2])
        with rc1:
            sel_m1 = st.selectbox("Month 1 (baseline)",  all_month_strs,
                                  index=max(0, len(all_month_strs)-2), key="rpt_m1")
        with rc2:
            sel_m2 = st.selectbox("Month 2 (comparison)", all_month_strs,
                                  index=len(all_month_strs)-1, key="rpt_m2")

        p1 = pd.Period(sel_m1, "M")
        p2 = pd.Period(sel_m2, "M")

        if p1 >= p2:
            st.error("Month 2 must be later than Month 1.")
        else:
            y1, m1 = p1.year, p1.month
            y2, m2 = p2.year, p2.month

            # Preview key numbers
            st.markdown('<div class="section-hdr">Preview — At a Glance</div>',
                        unsafe_allow_html=True)
            sn1 = snapshot(mis_df, y1, m1)
            sn2 = snapshot(mis_df, y2, m2)
            ml1, ml2 = month_label(y1,m1), month_label(y2,m2)

            prev_data = {
                "Stage":           ["In-Principle", "Sanctioned", "Disbursed"],
                f"{ml1} (Count)":  [sn1["ip_count"], sn1["sanction_count"], sn1["disb_count"]],
                f"{ml1} Amt (Cr)": [round(sn1["ip_amt"]/1e7,2), round(sn1["sanction_amt"]/1e7,2), round(sn1["disb_amt"]/1e7,2)],
                f"{ml2} (Count)":  [sn2["ip_count"], sn2["sanction_count"], sn2["disb_count"]],
                f"{ml2} Amt (Cr)": [round(sn2["ip_amt"]/1e7,2), round(sn2["sanction_amt"]/1e7,2), round(sn2["disb_amt"]/1e7,2)],
            }
            st.dataframe(pd.DataFrame(prev_data), use_container_width=True, hide_index=True)

            rc4, rc5, rc6 = st.columns(3)
            rc4.metric(f"States ({ml2})",         sn2["active_states"],
                       delta=sn2["active_states"]-sn1["active_states"])
            rc5.metric(f"Active Banks ({ml2})",   sn2["active_banks"],
                       delta=sn2["active_banks"]-sn1["active_banks"])
            rc6.metric(f"Zero Banks ({ml2})",     sn2["zero_banks"],
                       delta=sn2["zero_banks"]-sn1["zero_banks"], delta_color="inverse")

            st.markdown("")
            gen_btn = st.button("Generate Word Report", type="primary", key="gen_report")

            if gen_btn:
                with st.spinner("Building report..."):
                    try:
                        data = build_report_json(y1, m1, y2, m2)

                        with tempfile.TemporaryDirectory() as tmpdir:
                            data_path = Path(tmpdir) / "report_data.json"
                            out_path  = Path(tmpdir) / "progress_report.docx"
                            script_path = Path(__file__).parent / "generate_report.js"

                            data_path.write_text(json.dumps(data, ensure_ascii=True), encoding='utf-8')

                            # Ensure docx is installed locally in the dashboard folder
                            node_modules = script_path.parent / "node_modules" / "docx"
                            if not node_modules.exists():
                                with st.spinner("Installing docx package (first time only)..."):
                                    install = subprocess.run(
                                        ["npm", "install", "docx"],
                                        capture_output=True, text=True,
                                        cwd=str(script_path.parent),
                                        timeout=120
                                    )
                                    if install.returncode != 0:
                                        st.error(f"npm install failed: {install.stderr}")
                                        st.stop()

                            result = subprocess.run(
                                ["node", str(script_path), str(data_path), str(out_path)],
                                capture_output=True, text=True, timeout=60,
                                cwd=str(script_path.parent)   # so Node finds ./node_modules/docx
                            )

                            if result.returncode != 0 or not out_path.exists():
                                st.error(f"Report generation failed: {result.stderr or result.stdout}")
                            else:
                                docx_bytes = out_path.read_bytes()
                                fname = f"eKCC_Progress_Report_{ml1.replace(' ','_')}_{ml2.replace(' ','_')}.docx"
                                st.success("Report generated successfully!")
                                st.download_button(
                                    label=f"Download: {fname}",
                                    data=docx_bytes,
                                    file_name=fname,
                                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                                )
                    except Exception as e:
                        st.error(f"Error: {e}")