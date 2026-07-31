# -*- coding: utf-8 -*-
"""一次性历史回灌:把多对(发货,收货)文件清洗后灌进 Supabase。本地跑一次即可。
   用法:和 cleaning.py、dim_site.csv 放同一文件夹;填好下面 URL 和 PAIRS;python backfill.py"""
import datetime
import pandas as pd
from sqlalchemy import create_engine, text
import cleaning

# ① 你的 Supabase Session pooler 连接串(和测试时那条一样)
URL = "postgresql+psycopg2://postgres.你的项目编号:你的真密码@aws-0-你的区域.pooler.supabase.com:5432/postgres"

# ② 把所有历史文件名列进来(一个文件即含收发;整段历史一个也行,按周分就多个)
FILES = [
    "全量历史.xlsx",
    # "W13.xlsx", "W14.xlsx", "W15.xlsx",
]

# ③ 只保留 实际发车时间 <= 这一天(按需改;不想过滤就设 None)
CUTOFF = datetime.date(2026, 7, 29)

COLS = ["seg_key","task_id","origin","dest","origin_region","dest_region","trunk_type",
        "vehicle_type","supplier","load_tickets","unload_tickets",
        "depart_ts","arrive_ts","depart_date","arrive_date"]

def main():
    s2r = cleaning.load_site2region("dim_site.csv")
    df = cleaning.clean(FILES, s2r).drop_duplicates("seg_key")
    if CUTOFF is not None:
        dd = pd.to_datetime(df["depart_date"], errors="coerce").dt.date
        df = df[(dd.isna()) | (dd <= CUTOFF)]          # 未发车(空)保留;已发车的只留 <= CUTOFF
    df = df.reindex(columns=COLS)
    eng = create_engine(URL, pool_pre_ping=True)
    setclause = ", ".join(f"{c}=EXCLUDED.{c}" for c in COLS if c != "seg_key")
    with eng.begin() as con:
        df.to_sql("_staging", con, if_exists="replace", index=False)
        con.execute(text(f"""INSERT INTO fact_shipment ({','.join(COLS)})
                             SELECT {','.join(COLS)} FROM _staging
                             ON CONFLICT (seg_key) DO UPDATE SET {setclause};"""))
        con.execute(text("DROP TABLE IF EXISTS _staging;"))
    print(f"完成:清洗 {len(df)} 段已灌入 fact_shipment")

if __name__ == "__main__":
    main()
