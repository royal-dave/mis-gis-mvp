import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime

import folium
from streamlit_folium import st_folium


# ---------------- DB FUNCTIONS ----------------
def get_conn():
    db_url = st.secrets["SUPABASE_DB_URL"]
    return psycopg2.connect(db_url)

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS assets (
            id BIGSERIAL PRIMARY KEY,
            asset_name TEXT NOT NULL,
            department TEXT NOT NULL,
            status TEXT NOT NULL,
            latitude DOUBLE PRECISION NOT NULL,
            longitude DOUBLE PRECISION NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

def insert_asset(asset_name, department, status, lat, lon):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO assets (asset_name, department, status, latitude, longitude)
        VALUES (%s, %s, %s, %s, %s)
    """, (asset_name, department, status, lat, lon))
    conn.commit()
    cur.close()
    conn.close()

def fetch_assets():
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM assets ORDER BY id DESC", conn)
    conn.close()
    return df

def update_asset_status(asset_id, new_status):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE assets
        SET status = %s
        WHERE id = %s
    """, (new_status, asset_id))
    conn.commit()
    cur.close()
    conn.close()

def delete_asset(asset_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM assets WHERE id = %s", (asset_id,))
    conn.commit()
    cur.close()
    conn.close()

# ---------------- APP START ----------------
st.set_page_config(page_title="MIS + GIS MVP", layout="wide")
init_db()

st.title("🗺️ MIS + GIS MVP (Streamlit)")

menu = st.sidebar.radio("Navigation", [
    "➕ Add Asset (MIS Form)",
    "🌍 GIS Map View",
    "📋 Asset Table",
    "🛠️ Manage Assets (Update/Delete)"
])

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

    # Choose city to zoom map
    city = st.selectbox("Choose City (Map will zoom)", list(city_coords.keys()))
    center_lat, center_lon = city_coords[city]

    st.markdown("### 🗺️ Click on map to pick asset location")
    m = folium.Map(location=[center_lat, center_lon], zoom_start=11)

    # show existing points on map too (very useful)
    df_existing = fetch_assets()
    if not df_existing.empty:
        for _, row in df_existing.iterrows():
            folium.Marker(
                location=[row["latitude"], row["longitude"]],
                popup=f'{row["asset_name"]} ({row["department"]}, {row["status"]})',
            ).add_to(m)

    map_data = st_folium(m, height=450, width=900)

    # If user clicked on map, capture coordinates
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
        department = st.selectbox("Department", ["Water", "Road", "Electricity", "Drainage", "Other"])
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

# ---------------- PAGE 2: GIS MAP VIEW ----------------
elif menu == "🌍 GIS Map View":
    st.subheader("🌍 GIS Map View (OpenStreetMap)")

    df = fetch_assets()

    if df.empty:
        st.warning("No assets added yet. Add assets first.")
    else:
        map_df = df.rename(columns={"latitude": "lat", "longitude": "lon"})
        st.map(map_df[["lat", "lon"]])

        st.markdown("### 🔎 Assets")
        st.dataframe(df, use_container_width=True)

# ---------------- PAGE 3: TABLE VIEW ----------------
elif menu == "📋 Asset Table":
    st.subheader("📋 Asset Table")
    df = fetch_assets()

    if df.empty:
        st.warning("No assets found.")
    else:
        st.dataframe(df, use_container_width=True)

elif menu == "🛠️ Manage Assets (Update/Delete)":
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
        delete_id = st.number_input("Enter Asset ID to Delete", min_value=1, step=1, key="delete_id")

        if st.button("Delete Asset"):
            delete_asset(delete_id)
            st.warning(f"Deleted Asset ID {delete_id}")
            st.rerun()
