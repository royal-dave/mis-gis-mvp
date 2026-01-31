import streamlit as st
import pandas as pd
import io

import folium
from streamlit_folium import st_folium

# ✅ import from your separated files
from src.db import (
    init_db,
    fetch_assets,
    insert_asset,
    update_asset_status,
    delete_asset,
)
from src.auth import check_user


# ---------------- HELPERS ----------------
def apply_filters(df: pd.DataFrame, department: str, status: str) -> pd.DataFrame:
    if department != "All":
        df = df[df["department"] == department]
    if status != "All":
        df = df[df["status"] == status]
    return df


def to_excel_bytes(df: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Assets")
    return output.getvalue()


# ---------------- APP START ----------------
st.set_page_config(page_title="MIS + GIS MVP", layout="wide")
init_db()

# session init
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None

st.title("🗺️ MIS + GIS MVP (Streamlit)")

# ---------------- LOGIN ----------------
if not st.session_state.logged_in:
    st.subheader("🔐 Login")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        login_btn = st.form_submit_button("Login")

    if login_btn:
        result = check_user(username.strip(), password.strip())
        if result:
            st.session_state.logged_in = True
            st.session_state.username = result[0]
            st.session_state.role = result[1]
            st.success(f"Welcome {result[0]} ({result[1]})")
            st.rerun()
        else:
            st.error("Invalid username or password")

    st.stop()

# ---------------- SIDEBAR ----------------
st.sidebar.success(
    f"Logged in as: {st.session_state.username} ({st.session_state.role})"
)

if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None
    st.rerun()

pages = ["🌍 GIS Map View", "📋 Asset Table"]

if st.session_state.role in ["entry", "admin"]:
    pages.insert(0, "➕ Add Asset (MIS Form)")

if st.session_state.role == "admin":
    pages.append("🛠️ Manage Assets (Update/Delete)")
    pages.append("👤 User Management (Admin)")

menu = st.sidebar.radio("Navigation", pages)

# ---------------- CITY COORDINATES ----------------
city_coords = {
    "Pune": (18.5204, 73.8567),
    "Mumbai": (19.0760, 72.8777),
    "Nagpur": (21.1458, 79.0882),
    "Delhi": (28.6139, 77.2090),
    "Bengaluru": (12.9716, 77.5946),
}

# ---------------- PAGE 1: MIS FORM ----------------
if menu == "➕ Add Asset (MIS Form)":
    st.subheader("➕ Add New Asset (MIS Form)")

    # initialize session state for clicked coordinates
    if "clicked_lat" not in st.session_state:
        st.session_state.clicked_lat = None
    if "clicked_lon" not in st.session_state:
        st.session_state.clicked_lon = None

    city = st.selectbox("Choose City (Map will zoom)", list(city_coords.keys()))
    center_lat, center_lon = city_coords[city]

    st.markdown("### 🗺️ Click on map to pick asset location")
    m = folium.Map(location=[center_lat, center_lon], zoom_start=11)

    # show existing points on map too
    df_existing = fetch_assets()
    if not df_existing.empty:
        for _, row in df_existing.iterrows():
            folium.Marker(
                location=[row["latitude"], row["longitude"]],
                popup=f'{row["asset_name"]} ({row["department"]}, {row["status"]})',
            ).add_to(m)

    map_data = st_folium(m, height=450, width=900)

    if map_data and map_data.get("last_clicked"):
        st.session_state.clicked_lat = map_data["last_clicked"]["lat"]
        st.session_state.clicked_lon = map_data["last_clicked"]["lng"]

    st.info("📍 Selected Location:")
    colA, colB = st.columns(2)
    with colA:
        st.write("Latitude:", st.session_state.clicked_lat)
    with colB:
        st.write("Longitude:", st.session_state.clicked_lon)

    st.markdown("---")

    with st.form("asset_form"):
        asset_name = st.text_input("Asset Name", placeholder="e.g., Street Light 101")
        department = st.selectbox(
            "Department", ["Water", "Road", "Electricity", "Drainage", "Other"]
        )
        status = st.selectbox("Status", ["Proposed", "In Progress", "Completed"])

        col1, col2 = st.columns(2)

        default_lat = st.session_state.clicked_lat if st.session_state.clicked_lat else center_lat
        default_lon = st.session_state.clicked_lon if st.session_state.clicked_lon else center_lon

        with col1:
            lat = st.number_input("Latitude", value=float(default_lat), format="%.6f")
        with col2:
            lon = st.number_input("Longitude", value=float(default_lon), format="%.6f")

        submitted = st.form_submit_button("✅ Submit")

    if submitted:
        if asset_name.strip() == "":
            st.error("Asset Name is required.")
        else:
            insert_asset(asset_name.strip(), department, status, lat, lon)
            st.success("✅ Asset saved successfully!")
            st.rerun()

# ---------------- PAGE 2: GIS MAP VIEW ----------------
elif menu == "🌍 GIS Map View":
    st.subheader("🌍 GIS Map View (OpenStreetMap)")

    df = fetch_assets()
    if df.empty:
        st.warning("No assets added yet. Add assets first.")
    else:
        st.markdown("### 🔍 Filters")
        colF1, colF2 = st.columns(2)

        with colF1:
            dept_options = ["All"] + sorted(df["department"].unique().tolist())
            selected_dept = st.selectbox("Department", dept_options)

        with colF2:
            status_options = ["All", "Proposed", "In Progress", "Completed"]
            selected_status = st.selectbox("Status", status_options)

        filtered_df = apply_filters(df, selected_dept, selected_status)

        st.markdown("### 📊 Summary")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total", len(filtered_df))
        c2.metric("Proposed", int((filtered_df["status"] == "Proposed").sum()))
        c3.metric("In Progress", int((filtered_df["status"] == "In Progress").sum()))
        c4.metric("Completed", int((filtered_df["status"] == "Completed").sum()))

        st.markdown("### 🗺️ Map")
        if filtered_df.empty:
            st.warning("No assets match the selected filters.")
        else:
            map_df = filtered_df.rename(columns={"latitude": "lat", "longitude": "lon"})
            st.map(map_df[["lat", "lon"]])

        st.markdown("### 📋 Filtered Assets")
        st.dataframe(filtered_df, use_container_width=True)

        st.markdown("### ⬇️ Download Report")
        excel_data = to_excel_bytes(filtered_df)
        st.download_button(
            label="Download Excel Report",
            data=excel_data,
            file_name="assets_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

# ---------------- PAGE 3: TABLE VIEW ----------------
elif menu == "📋 Asset Table":
    st.subheader("📋 Asset Table")
    df = fetch_assets()

    if df.empty:
        st.warning("No assets found.")
    else:
        st.dataframe(df, use_container_width=True)

# ---------------- PAGE 4: ADMIN MANAGE ----------------
elif menu == "🛠️ Manage Assets (Update/Delete)":
    if st.session_state.role != "admin":
        st.error("Access denied.")
        st.stop()

    st.subheader("🛠️ Manage Assets (Update/Delete)")
    df = fetch_assets()

    if df.empty:
        st.warning("No assets found.")
    else:
        st.dataframe(df, use_container_width=True)

        st.markdown("### ✅ Update Asset Status")
        asset_id = st.number_input("Enter Asset ID", min_value=1, step=1)
        new_status = st.selectbox("New Status", ["Proposed", "In Progress", "Completed"])

        if st.button("Update Status"):
            update_asset_status(asset_id, new_status)
            st.success(f"Updated Asset ID {asset_id} status to {new_status}")
            st.rerun()

        st.markdown("---")

        st.markdown("### 🗑️ Delete Asset")
        delete_id = st.number_input(
            "Enter Asset ID to Delete", min_value=1, step=1, key="delete_id"
        )

        if st.button("Delete Asset"):
            delete_asset(delete_id)
            st.warning(f"Deleted Asset ID {delete_id}")
            st.rerun()


elif menu == "👤 User Management (Admin)":
    if st.session_state.role != "admin":
        st.error("Access denied.")
        st.stop()

    from src.db import create_or_update_user
    from src.security import hash_password

    st.subheader("👤 User Management (Admin)")

    with st.form("create_user_form"):
        new_username = st.text_input("Username").strip().lower()
        new_password = st.text_input("Password", type="password")
        role = st.selectbox("Role", ["viewer", "entry", "admin"])

        submit_user = st.form_submit_button("Create / Update User")

    if submit_user:
        if not new_username or not new_password:
            st.error("Username and password required.")
        else:
            password_hash = hash_password(new_password)
            create_or_update_user(new_username, password_hash, role)
            st.success(f"✅ User '{new_username}' created/updated as {role}")
