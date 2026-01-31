import streamlit as st
import psycopg2
import pandas as pd

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
