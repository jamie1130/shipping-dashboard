# -*- coding: utf-8 -*-
"""Supabase(PostgreSQL)连接 + upsert + 读取。凭据放 .streamlit/secrets.toml。"""
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

COLS = ["seg_key","task_id","origin","dest","origin_region","dest_region","trunk_type",
        "vehicle_type","supplier","load_tickets","unload_tickets",
        "depart_ts","arrive_ts","depart_date","arrive_date"]

@st.cache_resource
def get_engine():
    url = st.secrets["db"]["url"]        # postgresql+psycopg2://user:pwd@host:5432/postgres
    return create_engine(url, pool_pre_ping=True)

def upsert_shipments(df):
    """按 seg_key 幂等写入(重复上传自动更新,不重复)。"""
    d = df.reindex(columns=COLS).copy()
    eng = get_engine()
    setcols = [c for c in COLS if c != "seg_key"]
    setclause = ", ".join([f"{c}=EXCLUDED.{c}" for c in setcols])
    with eng.begin() as con:
        d.to_sql("_staging", con, if_exists="replace", index=False)
        con.execute(text(f"""
            INSERT INTO fact_shipment ({','.join(COLS)})
            SELECT {','.join(COLS)} FROM _staging
            ON CONFLICT (seg_key) DO UPDATE SET {setclause};
        """))
        con.execute(text("DROP TABLE IF EXISTS _staging;"))
    return len(d)

@st.cache_data(ttl=300)
def load_recent(days=60):
    """读近 N 天(按发车日或到车日)。缓存 5 分钟。"""
    eng = get_engine()
    sql = text(f"""
        SELECT * FROM fact_shipment
        WHERE depart_date >= CURRENT_DATE - INTERVAL '{int(days)} days'
           OR arrive_date >= CURRENT_DATE - INTERVAL '{int(days)} days'
    """)
    df = pd.read_sql(sql, eng)
    for c in ("depart_date","arrive_date"):
        df[c] = pd.to_datetime(df[c]).dt.date
    return df
