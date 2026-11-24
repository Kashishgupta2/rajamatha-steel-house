"""Rajamatha Steel House - Sales Management System
Streamlit + MySQL Expanded CRUD (8 Operations) on `rajamatha`.
Theme: Slate Grey & Emerald Green | Layout: Modern Top-Tab & 8-KPI Executive View.
"""
import re
import traceback
import altair as alt
import pandas as pd
import streamlit as st
import mysql.connector

# ---------------------------------------------------------------- Page & Theme Setup
st.set_page_config(page_title="Rajamatha Steel House", page_icon="🏗️", layout="wide")

st.markdown("""
<style>
    /* Global App Background & Typography */
    .stApp {
        background-color: #f4f6f8;
        color: #1e293b;
    }
    
    /* Custom Top Header Banner */
    .brand-banner {
        background: linear-gradient(135deg, #1e293b 0%, #334155 60%, #065f46 100%);
        padding: 1.5rem 2rem;
        border-radius: 14px;
        color: #ffffff;
        margin-bottom: 1.2rem;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.12);
        border-left: 6px solid #10b981;
    }
    .brand-banner h1 {
        margin: 0;
        font-size: 1.85rem;
        font-weight: 700;
        letter-spacing: -0.5px;
        color: #ffffff;
    }
    .brand-banner p {
        margin: 0.3rem 0 0 0;
        color: #cbd5e1;
        font-size: 0.95rem;
    }

    /* KPI Metric Cards (Grey Surface + Emerald Accent) */
    div[data-testid="stMetric"] {
        background: linear-gradient(180deg, #ffffff 0%, #f1f5f9 100%);
        border: 1px solid #cbd5e1;
        border-top: 4px solid #059669;
        padding: 14px 16px;
        border-radius: 10px;
        box-shadow: 0 2px 6px rgba(15, 23, 42, 0.04);
    }
    div[data-testid="stMetric"] label {
        color: #475569 !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        text-transform: uppercase;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #064e3b !important;
        font-weight: 700 !important;
    }

    /* Navigation Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #e2e8f0;
        padding: 6px;
        border-radius: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 600;
        color: #334155;
        background-color: transparent;
    }
    .stTabs [aria-selected="true"] {
        background-color: #059669 !important;
        color: #ffffff !important;
    }

    /* Primary Buttons in Emerald Green */
    .stButton > button[kind="primary"], div[data-testid="stFormSubmitButton"] > button {
        background-color: #059669 !important;
        border-color: #047857 !important;
        color: #ffffff !important;
        font-weight: 600;
        border-radius: 8px;
    }
    .stButton > button[kind="primary"]:hover, div[data-testid="stFormSubmitButton"] > button:hover {
        background-color: #047857 !important;
    }

    /* Section Cards */
    .section-box {
        background-color: #ffffff;
        padding: 1.25rem;
        border-radius: 12px;
        border: 1px solid #cbd5e1;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------- Constants
COLS = ["Product", "Product_Type", "Quantity_Sold", "Selling_Price", "Discount",
        "Final_Sales", "Cost_Price", "Profit", "Payment_Type"]
NUMERIC = ["Quantity_Sold", "Selling_Price", "Discount", "Final_Sales", "Cost_Price", "Profit"]
ALIASES = {"quantitysold": "Quantity_Sold", "quantity": "Quantity_Sold", "qty": "Quantity_Sold",
           "sellingprice": "Selling_Price", "finalsales": "Final_Sales", "costprice": "Cost_Price",
           "producttype": "Product_Type", "paymenttype": "Payment_Type", "payment": "Payment_Type"}
PAYMENTS_DEFAULT = ["Cash", "UPI", "Debit Card", "Credit Card"]


def norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


# ---------------------------------------------------------------- Database Layer
def cfg():
    return dict(st.secrets["mysql"])


def get_conn():
    c = cfg()
    kw = dict(host=str(c["host"]), port=int(c.get("port", 3306)), user=str(c["user"]),
              password=str(c["password"]), database=str(c.get("database", "rajamatha")), use_pure=True)
    if c.get("ssl_ca"):
        kw["ssl_ca"] = c["ssl_ca"]
    return mysql.connector.connect(**kw)


def run_query(sql, params=None):
    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params or ())
        return cur.fetchall()
    finally:
        conn.close()


def run_execute(sql, params=None):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(sql, params or ())
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def run_executemany(sql, seq_params):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.executemany(sql, seq_params)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@st.cache_data(ttl=600, show_spinner="Reading MySQL structure…")
def discover():
    db = cfg().get("database", "rajamatha")
    rows = run_query("SELECT TABLE_NAME AS t, COLUMN_NAME AS c FROM information_schema.COLUMNS "
                     "WHERE TABLE_SCHEMA=%s ORDER BY TABLE_NAME, ORDINAL_POSITION", (db,))
    tables = {}
    for r in rows:
        tables.setdefault(r["t"], []).append(r["c"])
    found = {}
    for t, cols in tables.items():
        m = {}
        for actual in cols:
            n = norm(actual)
            logical = next((x for x in COLS if norm(x) == n), None) or ALIASES.get(n)
            if logical and logical not in m:
                m[logical] = actual
        if all(x in m for x in COLS):
            found[t] = m
    return found, tables


@st.cache_resource(show_spinner=False)
def primary_key(t):
    pk = run_query(f"SHOW KEYS FROM `{t}` WHERE Key_name='PRIMARY'")
    if pk:
        return pk[0]["Column_name"]
    run_execute(f"ALTER TABLE `{t}` ADD COLUMN `row_id` INT NOT NULL AUTO_INCREMENT PRIMARY KEY FIRST")
    return "row_id"


@st.cache_data(ttl=300, show_spinner="Loading from MySQL…")
def load_data(t, pk, mapping_items):
    d = pd.DataFrame(run_query(f"SELECT * FROM `{t}`"))
    if d.empty:
        return pd.DataFrame(columns=["id"] + COLS)
    d = d.rename(columns={a: l for l, a in mapping_items}).rename(columns={pk: "id"})
    for col in NUMERIC:
        d[col] = pd.to_numeric(d[col].astype(str).str.replace(",", "", regex=False), errors="coerce")
    return d


def calc(qty, price, discount, cost):
    final = round(qty * price - discount, 2)
    return final, round(final - qty * cost, 2)


def save_row(row_id, v):
    final, profit = calc(v["qty"], v["price"], v["discount"], v["cost"])
    vals = dict(Product=v["product"], Product_Type=v["ptype"], Quantity_Sold=int(v["qty"]),
                Selling_Price=v["price"], Discount=v["discount"], Final_Sales=final,
                Cost_Price=v["cost"], Profit=profit, Payment_Type=v["payment"])
    args = tuple(vals[c] for c in COLS)
    names = [f"`{M[c]}`" for c in COLS]
    if row_id is None:
        run_execute(f"INSERT INTO `{T}` ({','.join(names)}) VALUES ({','.join(['%s'] * len(COLS))})", args)
    else:
        run_execute(f"UPDATE `{T}` SET {','.join(n + '=%s' for n in names)} WHERE `{PK}`=%s", args + (row_id,))


# ---------------------------------------------------------------- UI Helpers
def flash(msg):
    st.session_state["flash"] = msg
    st.rerun()


def safe(action, ok_msg):
    try:
        action()
    except (ValueError, mysql.connector.Error) as e:
        st.error(f"Database error: {e}")
    else:
        load_data.clear()
        flash(ok_msg)


def sale_form(key, data, rec=None):
    rec = rec or {}
    products = sorted(data["Product"].dropna().astype(str).unique())
    types = sorted(data["Product_Type"].dropna().astype(str).unique())
    pays = sorted(set(data["Payment_Type"].dropna().astype(str)) | set(PAYMENTS_DEFAULT))
    products, types = products or [""], types or [""]

    c1, c2 = st.columns(2)
    p_sel = c1.selectbox("Product*", products,
                         index=products.index(rec["product"]) if rec.get("product") in products else 0, key=f"{key}p")
    p_new = c2.text_input("…or enter NEW Product", key=f"{key}pn")

    c3, c4 = st.columns(2)
    t_sel = c3.selectbox("Product Type*", types,
                         index=types.index(rec["ptype"]) if rec.get("ptype") in types else 0, key=f"{key}t")
    t_new = c4.text_input("…or enter NEW Type", key=f"{key}tn")

    c5, c6, c7 = st.columns(3)
    qty = c5.number_input("Quantity Sold*", min_value=0, value=int(rec.get("qty") or 1), step=1, key=f"{key}q")
    price = c6.number_input("Selling Price (₹)*", min_value=0.0, value=float(rec.get("price") or 0), step=50.0, key=f"{key}s")
    disc = c7.number_input("Discount (₹, total)", min_value=0.0, value=float(rec.get("discount") or 0), step=10.0, key=f"{key}d")

    c8, c9 = st.columns(2)
    cost = c8.number_input("Cost Price (₹) – 0 = auto from existing product", min_value=0.0,
                           value=float(rec.get("cost") or 0), step=50.0, key=f"{key}c")
    pay = c9.selectbox("Payment Type*", pays,
                       index=pays.index(rec["payment"]) if rec.get("payment") in pays else 0, key=f"{key}pm")

    return dict(product=p_new.strip() or p_sel, ptype=t_new.strip() or t_sel, qty=qty, price=price,
                discount=disc, cost=cost, payment=pay)


def build_payload(v, data):
    if not v["product"] or not v["ptype"]:
        st.error("Product and Product Type are required."); return None
    if v["qty"] <= 0:
        st.error("Quantity must be greater than 0."); return None
    if v["price"] <= 0:
        st.error("Selling price must be greater than 0."); return None
    if v["discount"] > v["qty"] * v["price"]:
        st.error("Discount cannot exceed Quantity × Selling Price."); return None
    if v["cost"] == 0:
        m = data[(data["Product"] == v["product"]) & (data["Product_Type"] == v["ptype"])]
        if m.empty:
            st.error("New product/type: please enter its Cost Price."); return None
        v["cost"] = float(m["Cost_Price"].iloc[-1])
    return v


def pick_record(data, key):
    text = st.text_input("🔍 Search by ID, Product, Type, or Payment", key=f"{key}s").strip()
    d = data
    if text:
        m = d["id"].astype(str).eq(text)
        for col in ["Product", "Product_Type", "Payment_Type"]:
            m |= d[col].astype(str).str.contains(text, case=False, na=False, regex=False)
        d = d[m]
    d = d.sort_values("id", ascending=False).head(200)
    if d.empty:
        st.warning("No matching records found."); return None
    labels = {f"#{r['id']} | {r['Product']} ({r['Product_Type']}) | Qty: {r['Quantity_Sold']:.0f} | "
              f"₹{r['Final_Sales']:,.0f} | {r['Payment_Type']}": r["id"] for _, r in d.iterrows()}
    choice = st.selectbox("Select record (latest 200 matches)", list(labels), key=f"{key}c")
    return d[d["id"] == labels[choice]].iloc[0]


# ---------------------------------------------------------------- Startup & Connection
try:
    found, all_tables = discover()
    if not found:
        st.error(f"No table in database `{cfg().get('database', 'rajamatha')}` has the columns: {', '.join(COLS)}")
        st.write("Tables and columns found in MySQL:", all_tables)
        st.stop()
    wanted = cfg().get("table")
    if wanted and wanted in found:
        T = wanted
    elif len(found) == 1:
        T = next(iter(found))
    else:
        T = st.sidebar.selectbox("Select Database Table", list(found))
    M = found[T]
    PK = primary_key(T)
    data = load_data(T, PK, tuple(M.items()))
except Exception as e:
    st.error(f"Cannot connect to / read MySQL - {type(e).__name__}: {e!r}")
    st.info("Check `.streamlit/secrets.toml` (host, user, password, database = \"rajamatha\").")
    with st.expander("Technical details"):
        st.code(traceback.format_exc())
    st.stop()

# ---------------------------------------------------------------- Header & Control Bar
st.markdown("""
<div class="brand-banner">
    <h1>🏗️ Rajamatha Steel House — Sales & Inventory Command Center</h1>
    <p>Real-Time MySQL Analytics • Multi-Mode CRUD Operations • Slate & Emerald Edition</p>
</div>
""", unsafe_allow_html=True)

info_col, btn_col = st.columns([5, 1])
info_col.caption(f"🟢 Connected to MySQL `{cfg().get('database', 'rajamatha')}`  |  Table: `{T}`  |  "
                 f"Total Records: **{len(data):,}**  |  Primary Key: `{PK}`")
if btn_col.button("🔄 Sync MySQL", use_container_width=True):
    load_data.clear()
    discover.clear()
    st.rerun()

if "flash" in st.session_state:
    st.success(st.session_state.pop("flash"))

# ---------------------------------------------------------------- Top Navigation Tabs
tab_dash, tab_read, tab_create, tab_update, tab_delete = st.tabs([
    "📊 Executive Dashboard",
    "👁️ 1. View & Export Records",
    "➕ 2-3. Add & Bulk Import",
    "✏️ 4-6. Edit, Clone & Bulk Update",
    "🗑️ 7-8. Single & Batch Delete"
])

# ================================================================ TAB 1: DASHBOARD (8 KPIs)
with tab_dash:
    if data.empty:
        st.info("No records available yet. Switch to **➕ Add & Bulk Import** to create your first sale.")
    else:
        total_sales = data["Final_Sales"].sum()
        total_profit = data["Profit"].sum()
        total_units = data["Quantity_Sold"].sum()
        total_disc = data["Discount"].sum()
        gross_sales = (data["Quantity_Sold"] * data["Selling_Price"]).sum()
        margin_pct = (total_profit / total_sales * 100) if total_sales else 0.0
        aov = (total_sales / len(data)) if len(data) else 0.0
        disc_rate = (total_disc / gross_sales * 100) if gross_sales else 0.0
        unique_prods = data["Product"].nunique()

        # Row 1: 4 Primary Financial KPIs
        r1c1, r1c2, r1c3, r1c4 = st.columns(4)
        r1c1.metric("Total Revenue", f"₹ {total_sales:,.0f}")
        r1c2.metric("Net Profit", f"₹ {total_profit:,.0f}")
        r1c3.metric("Profit Margin", f"{margin_pct:.1f}%")
        r1c4.metric("Avg Order Value", f"₹ {aov:,.0f}")

        st.write("")  # Spacer

        # Row 2: 4 Operational & Discount KPIs
        r2c1, r2c2, r2c3, r2c4 = st.columns(4)
        r2c1.metric("Total Units Sold", f"{total_units:,.0f}")
        r2c2.metric("Total Discounts", f"₹ {total_disc:,.0f}")
        r2c3.metric("Discount Rate", f"{disc_rate:.1f}%")
        r2c4.metric("Active Products", f"{unique_prods:,}")

        st.divider()

        # Charts Grid (Emerald & Slate Altair Charts)
        ch1, ch2 = st.columns(2)
        with ch1:
            st.subheader("Revenue by Product (₹)")
            df_prod = data.groupby("Product", as_index=False)["Final_Sales"].sum().sort_values("Final_Sales", ascending=False)
            chart1 = alt.Chart(df_prod).mark_bar(color="#059669", cornerRadiusTopRight=4, cornerRadiusBottomRight=4).encode(
                x=alt.X("Final_Sales:Q", title="Revenue (₹)"),
                y=alt.Y("Product:N", sort="-x", title=None),
                tooltip=["Product", alt.Tooltip("Final_Sales:Q", format=",.0f")]
            ).properties(height=300)
            st.altair_chart(chart1, use_container_width=True)

        with ch2:
            st.subheader("Profit by Product (₹)")
            df_prof = data.groupby("Product", as_index=False)["Profit"].sum().sort_values("Profit", ascending=False)
            chart2 = alt.Chart(df_prof).mark_bar(color="#334155", cornerRadiusTopRight=4, cornerRadiusBottomRight=4).encode(
                x=alt.X("Profit:Q", title="Profit (₹)"),
                y=alt.Y("Product:N", sort="-x", title=None),
                tooltip=["Product", alt.Tooltip("Profit:Q", format=",.0f")]
            ).properties(height=300)
            st.altair_chart(chart2, use_container_width=True)

        ch3, ch4 = st.columns(2)
        with ch3:
            st.subheader("Sales Share by Payment Mode")
            df_pay = data.groupby("Payment_Type", as_index=False)["Final_Sales"].sum()
            chart3 = alt.Chart(df_pay).mark_arc(innerRadius=55).encode(
                theta=alt.Theta("Final_Sales:Q"),
                color=alt.Color("Payment_Type:N", scale=alt.Scale(range=["#059669", "#334155", "#10b981", "#64748b", "#94a3b8"])),
                tooltip=["Payment_Type", alt.Tooltip("Final_Sales:Q", format=",.0f")]
            ).properties(height=280)
            st.altair_chart(chart3, use_container_width=True)

        with ch4:
            st.subheader("Units Sold by Product Type")
            df_type = data.groupby("Product_Type", as_index=False)["Quantity_Sold"].sum().sort_values("Quantity_Sold", ascending=False)
            chart4 = alt.Chart(df_type).mark_bar(color="#10b981", cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
                x=alt.X("Product_Type:N", sort="-y", title=None),
                y=alt.Y("Quantity_Sold:Q", title="Units Sold"),
                tooltip=["Product_Type", alt.Tooltip("Quantity_Sold:Q", format=",.0f")]
            ).properties(height=280)
            st.altair_chart(chart4, use_container_width=True)

        st.subheader("📋 Product Performance Matrix")
        s = data.groupby(["Product", "Product_Type"]).agg(
            Orders=("id", "count"),
            Units=("Quantity_Sold", "sum"),
            Revenue=("Final_Sales", "sum"),
            Discounts=("Discount", "sum"),
            Profit=("Profit", "sum")
        ).reset_index()
        s["Margin %"] = (s["Profit"] / s["Revenue"] * 100).round(1)
        st.dataframe(s.sort_values("Revenue", ascending=False), use_container_width=True, hide_index=True)

# ================================================================ TAB 2: READ & FILTER (CRUD #1)
with tab_read:
    st.subheader("Operation 1: Advanced Filter, Inspect & Export")
    if data.empty:
        st.info("No records to display.")
    else:
        f1, f2, f3, f4 = st.columns([2, 2, 2, 2])
        sel_p = f1.multiselect("Filter Product", sorted(data["Product"].dropna().unique()))
        sel_t = f2.multiselect("Filter Product Type", sorted(data["Product_Type"].dropna().unique()))
        sel_pay = f3.multiselect("Filter Payment Type", sorted(data["Payment_Type"].dropna().unique()))
        min_sale = f4.number_input("Min Final Sale (₹)", min_value=0.0, value=0.0, step=500.0)

        d = data.copy()
        if sel_p: d = d[d["Product"].isin(sel_p)]
        if sel_t: d = d[d["Product_Type"].isin(sel_t)]
        if sel_pay: d = d[d["Payment_Type"].isin(sel_pay)]
        if min_sale > 0: d = d[d["Final_Sales"] >= min_sale]

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Filtered Records", f"{len(d):,}")
        m2.metric("Filtered Revenue", f"₹ {d['Final_Sales'].sum():,.0f}")
        m3.metric("Filtered Profit", f"₹ {d['Profit'].sum():,.0f}")
        m4.metric("Filtered Units", f"{d['Quantity_Sold'].sum():,.0f}")

        shown = d.sort_values("id", ascending=False)[["id"] + COLS]
        st.dataframe(shown, use_container_width=True, hide_index=True)
        if len(d):
            st.download_button("⬇️ Download Filtered CSV", shown.to_csv(index=False),
                               "rajamatha_filtered_sales.csv", "text/csv")

# ================================================================ TAB 3: CREATE & BULK IMPORT (CRUD #2 & #3)
with tab_create:
    col_single, col_bulk = st.columns([3, 2], gap="large")

    # CRUD #2: Single Create
    with col_single:
        st.subheader("Operation 2: Add Single Sale")
        with st.form("add_form", clear_on_submit=True):
            vals = sale_form("add", data)
            if st.form_submit_button("➕ Save Single Sale", type="primary", use_container_width=True):
                payload = build_payload(vals, data)
                if payload:
                    f, p = calc(payload["qty"], payload["price"], payload["discount"], payload["cost"])
                    safe(lambda: save_row(None, payload), f"Sale added ✅  Final ₹{f:,.0f} • Profit ₹{p:,.0f}")

    # CRUD #3: Bulk CSV Create
    with col_bulk:
        st.subheader("Operation 3: Bulk CSV Import")
        st.caption("Upload a CSV with columns: `Product, Product_Type, Quantity_Sold, Selling_Price, Discount, Cost_Price, Payment_Type`")
        sample_csv = "Product,Product_Type,Quantity_Sold,Selling_Price,Discount,Cost_Price,Payment_Type\nTMT Bar 12mm,Construction,10,550,100,480,UPI\n"
        st.download_button("📄 Download Sample CSV Template", sample_csv, "sample_import.csv", "text/csv")

        up_file = st.file_uploader("Upload CSV File", type=["csv"])
        if up_file is not None:
            try:
                imp_df = pd.read_csv(up_file)
                req_cols = ["Product", "Product_Type", "Quantity_Sold", "Selling_Price", "Discount", "Cost_Price", "Payment_Type"]
                missing = [c for c in req_cols if c not in imp_df.columns]
                if missing:
                    st.error(f"Missing columns in CSV: {', '.join(missing)}")
                else:
                    st.dataframe(imp_df.head(5), use_container_width=True)
                    if st.button(f"📥 Import {len(imp_df)} Rows into MySQL", type="primary", use_container_width=True):
                        def bulk_insert():
                            names = [f"`{M[c]}`" for c in COLS]
                            sql = f"INSERT INTO `{T}` ({','.join(names)}) VALUES ({','.join(['%s'] * len(COLS))})"
                            batch = []
                            for _, row in imp_df.iterrows():
                                qty = int(row["Quantity_Sold"])
                                price = float(row["Selling_Price"])
                                disc = float(row["Discount"])
                                cost = float(row["Cost_Price"])
                                final, profit = calc(qty, price, disc, cost)
                                batch.append((str(row["Product"]), str(row["Product_Type"]), qty, price, disc, final, cost, profit, str(row["Payment_Type"])))
                            run_executemany(sql, batch)
                        safe(bulk_insert, f"Successfully imported {len(imp_df)} records ✅")
            except Exception as ex:
                st.error(f"Error reading CSV: {ex}")

# ================================================================ TAB 4: UPDATE, CLONE & BULK ADJUST (CRUD #4, #5, #6)
with tab_update:
    if data.empty:
        st.info("No records available to update or clone.")
    else:
        u_mode = st.radio(
            "Select Update Operation:",
            ["Operation 4: Edit Single Record", "Operation 5: Clone / Duplicate Record", "Operation 6: Bulk Price / Discount Update"],
            horizontal=True
        )
        st.divider()

        # CRUD #4: Standard Single Update
        if u_mode == "Operation 4: Edit Single Record":
            r = pick_record(data, "up")
            if r is not None:
                rid = int(r["id"])
                rec = dict(product=r["Product"], ptype=r["Product_Type"], qty=r["Quantity_Sold"], price=r["Selling_Price"],
                           discount=r["Discount"], cost=r["Cost_Price"], payment=r["Payment_Type"])
                with st.form(f"upd_{rid}"):
                    vals = sale_form(f"u{rid}", data, rec)
                    if st.form_submit_button("💾 Update Record", type="primary"):
                        payload = build_payload(vals, data)
                        if payload:
                            safe(lambda: save_row(rid, payload), f"Record #{rid} updated ✅")

        # CRUD #5: Clone / Duplicate Existing Record as New Sale
        elif u_mode == "Operation 5: Clone / Duplicate Record":
            st.caption("Select an existing transaction to pre-fill a brand new sale entry.")
            r = pick_record(data, "clone")
            if r is not None:
                rid = int(r["id"])
                rec = dict(product=r["Product"], ptype=r["Product_Type"], qty=r["Quantity_Sold"], price=r["Selling_Price"],
                           discount=r["Discount"], cost=r["Cost_Price"], payment=r["Payment_Type"])
                with st.form(f"clone_form_{rid}"):
                    vals = sale_form(f"cl{rid}", data, rec)
                    if st.form_submit_button("📋 Save as New Cloned Sale", type="primary"):
                        payload = build_payload(vals, data)
                        if payload:
                            f, p = calc(payload["qty"], payload["price"], payload["discount"], payload["cost"])
                            safe(lambda: save_row(None, payload), f"Cloned from #{rid} into new sale ✅ (Final ₹{f:,.0f})")

        # CRUD #6: Bulk Price / Discount Adjustment by Product
        else:
            st.caption("Apply a percentage price adjustment across all historical/selected records of a specific Product.")
            b1, b2, b3 = st.columns(3)
            target_prod = b1.selectbox("Target Product", sorted(data["Product"].dropna().unique()))
            pct_change = b2.number_input("Selling Price Adjustment (%)", min_value=-50.0, max_value=200.0, value=5.0, step=1.0)
            target_rows = data[data["Product"] == target_prod]
            b3.metric("Matching Records", len(target_rows))

            if st.button(f"⚡ Apply {pct_change:+.1f}% Price Change to {len(target_rows)} Records", type="primary"):
                def bulk_price_update():
                    factor = 1.0 + (pct_change / 100.0)
                    sql = (f"UPDATE `{T}` SET `{M['Selling_Price']}` = ROUND(`{M['Selling_Price']}` * %s, 2), "
                           f"`{M['Final_Sales']}` = ROUND((`{M['Quantity_Sold']}` * ROUND(`{M['Selling_Price']}` * %s, 2)) - `{M['Discount']}`, 2), "
                           f"`{M['Profit']}` = ROUND(((`{M['Quantity_Sold']}` * ROUND(`{M['Selling_Price']}` * %s, 2)) - `{M['Discount']}`) - (`{M['Quantity_Sold']}` * `{M['Cost_Price']}`), 2) "
                           f"WHERE `{M['Product']}` = %s")
                    run_execute(sql, (factor, factor, factor, target_prod))
                safe(bulk_price_update, f"Updated selling price & recalculated profit for {len(target_rows)} records of '{target_prod}' ✅")

# ================================================================ TAB 5: DELETE OPERATIONS (CRUD #7 & #8)
with tab_delete:
    if data.empty:
        st.info("No records available to delete.")
    else:
        del_col1, del_col2 = st.columns(2, gap="large")

        # CRUD #7: Single Record Delete
        with del_col1:
            st.subheader("Operation 7: Delete Single Record")
            r = pick_record(data, "del")
            if r is not None:
                rid = int(r["id"])
                st.json({k: str(v) for k, v in r.items()})
                sure = st.checkbox("Confirm permanent deletion of this single record", key="chk_del_single")
                if st.button("🗑️ Delete Single Record", type="primary", disabled=not sure):
                    safe(lambda: run_execute(f"DELETE FROM `{T}` WHERE `{PK}`=%s", (rid,)), f"Record #{rid} deleted 🗑️")

        # CRUD #8: Batch Delete by Filter
        with del_col2:
            st.subheader("Operation 8: Batch Delete by Category / Payment")
            st.caption("Remove multiple records matching a specific Product or Payment Type (e.g., clearing test entries).")
            filter_col = st.selectbox("Filter Column", ["Product", "Product_Type", "Payment_Type"])
            filter_val = st.selectbox("Value to Delete", sorted(data[filter_col].dropna().unique()))
            matches = data[data[filter_col] == filter_val]
            st.warning(f"⚠️ This will permanently delete **{len(matches)}** records where `{filter_col}` = **{filter_val}**.")
            sure_bulk = st.checkbox(f"I confirm deleting all {len(matches)} matching records", key="chk_del_bulk")
            if st.button(f"🔥 Batch Delete {len(matches)} Records", type="primary", disabled=not sure_bulk):
                safe(lambda: run_execute(f"DELETE FROM `{T}` WHERE `{M[filter_col]}`=%s", (filter_val,)),
                     f"Deleted {len(matches)} records where {filter_col} = '{filter_val}' 🗑️")