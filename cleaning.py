# -*- coding: utf-8 -*-
"""清洗:两个 taskArrivalTaskList(发货+收货)→ 段级收发货明细。复用已定口径。"""
import pandas as pd, re, datetime
from zoneinfo import ZoneInfo

TZMAP = {"东部":"America/New_York","中部":"America/Chicago","山地":"America/Denver",
         "太平洋":"America/Los_Angeles","凤凰城":"America/Phoenix",
         "夏威夷":"Pacific/Honolulu","波多黎各":"America/Puerto_Rico"}
PAC = ZoneInfo("America/Los_Angeles")
MAXY = datetime.date.today().year + 1
TRUNK = {"一级干线", "二级干线", "支线"}          # 干线+支线;剔除提货

def to_pacific(v):
    if v is None or str(v).strip() == "": return None
    txt = str(v); src = PAC
    m = re.search(r"[（(]([^)）]+)[)）]", txt)
    if m:
        for k, z in TZMAP.items():
            if k in m.group(1): src = ZoneInfo(z); break
    body = re.sub(r"\s*[（(][^)）]*[)）]\s*$", "", txt).strip()
    dt = None
    for f in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%m/%d/%Y %H:%M:%S", "%Y-%m-%d"):
        try: dt = datetime.datetime.strptime(body, f); break
        except: pass
    if dt is None or dt.year < 2024 or dt.year > MAXY: return None
    return dt.replace(tzinfo=src).astimezone(PAC).replace(tzinfo=None)

def load_site2region(path="dim_site.csv"):
    ds = pd.read_csv(path, dtype=str)
    return dict(zip(ds["site_code"].str.strip(), ds["region"]))

def clean(files, site2region):
    """files: 一个文件,或多个文件的列表(路径或上传对象)。单个 taskArrivalTaskList
    每行同时含 实际发车 与 实际到车 时间,所以一个文件即可同时算收发。"""
    if not isinstance(files, (list, tuple)):
        files = [files]
    frames = []
    for p in files:
        d = pd.read_excel(p); d.columns = [str(c).strip() for c in d.columns]; frames.append(d)
    raw = pd.concat(frames, ignore_index=True).dropna(how="all")
    raw = raw[raw["运输类型"].isin(TRUNK)].copy()                       # 只留干线+支线
    raw["_t"] = pd.to_numeric(raw["路段总票数"], errors="coerce")
    raw = raw.sort_values("_t", ascending=False).drop_duplicates(["任务编码", "始发地", "目的地"])  # 段级去重
    dep = raw["实际发车时间"].apply(to_pacific)
    arr = raw["实际抵达目的站时间"].apply(to_pacific)
    out = pd.DataFrame({
        "task_id": raw["任务编码"].astype(str),
        "origin": raw["始发地"].astype(str), "dest": raw["目的地"].astype(str),
        "trunk_type": raw["运输类型"].astype(str),
        "vehicle_type": raw.get("车型名称"), "supplier": raw.get("供应商名称"),
        "load_tickets": pd.to_numeric(raw["装车总票数"], errors="coerce").fillna(0).astype(int),
        "unload_tickets": pd.to_numeric(raw["卸车总票数"], errors="coerce").fillna(0).astype(int),
        "depart_ts": dep.values, "arrive_ts": arr.values,
    })
    out["depart_date"] = pd.to_datetime(out["depart_ts"]).dt.date
    out["arrive_date"] = pd.to_datetime(out["arrive_ts"]).dt.date
    out["origin_region"] = out["origin"].map(lambda h: site2region.get(h))
    out["dest_region"] = out["dest"].map(lambda h: site2region.get(h))
    out["seg_key"] = out["task_id"] + "|" + out["origin"] + "|" + out["dest"]
    out = out[out["depart_date"].notna() | out["arrive_date"].notna()].reset_index(drop=True)
    return out
