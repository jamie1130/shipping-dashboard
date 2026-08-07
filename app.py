# -*- coding: utf-8 -*-
"""干线收发货看板 · 统一版:对象(整体/单hub) × 周期(单天/周/月)。上传→清洗入库→看板。
注:装载率=票数/核载(估算);准时率、操作时长为【示例】占位(库里暂无相关列),上线前接真实列。"""
import datetime as dt
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import cleaning, db

st.set_page_config(page_title="干线收发货看板", layout="wide")
pio.templates.default = "plotly_white"
st.markdown("""<style>
[data-testid="stVerticalBlockBorderWrapper"]{background:#fff;border:1px solid #e5e9f0;border-radius:14px;padding:4px 14px;box-shadow:0 1px 2px rgba(20,30,50,.05),0 8px 24px rgba(20,30,50,.06)}
h1,h2,h3{letter-spacing:-.4px}
.kcard{background:#fff;border:1px solid #e5e9f0;border-top:6px solid var(--tc,#cbd5e1);border-radius:14px;padding:11px 14px;min-height:100px;box-shadow:0 1px 2px rgba(20,30,50,.05),0 8px 24px rgba(20,30,50,.06)}
.kcard .tag{font-size:20px;color:#6b7888;font-weight:700}
.kcard .val{font-size:45px;font-weight:800;letter-spacing:-.6px;margin:2px 0;color:#18212e}
.kcard .foot{display:flex;align-items:center;gap:6px;overflow:hidden}
.kcard .sub{font-size:15px;color:#6b7888;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.chip{font-weight:800;padding:1px 8px;border-radius:20px;font-size:11px}
.chip.up{color:#12a150;background:#e6f6ec}.chip.down{color:#e5484d;background:#fdecec}.chip.flat{color:#6b7888;background:#eef1f6}
.demo{display:inline-block;background:#fff4e6;color:#b45309;border:1px solid #fcd9a8;border-radius:6px;padding:0 6px;font-size:11px;font-weight:700}
</style>""", unsafe_allow_html=True)
WAN = 10000
WD = ["一", "二", "三", "四", "五", "六", "日"]
RATED = {"53FT": 12000, "26FT": 4000, "22FT": 3385, "Cargo Van": 1480}   # 核载票数(估)
BLUE, GREEN, RED, GRAY, ACCENT = "#2f6bff", "#0eae97", "#e5484d", "#94a3b8", "#ff7a29"
PIE = ["#2f6bff", "#0eae97", "#ff7a29", "#8b5cf6", "#eab308", "#ec4899", "#12a150", "#38bdf8"]
STATE2ABBR = {"Alabama":"AL","Alaska":"AK","Arizona":"AZ","Arkansas":"AR","California":"CA",
 "Colorado":"CO","Connecticut":"CT","Delaware":"DE","Florida":"FL","Georgia":"GA","Hawaii":"HI",
 "Idaho":"ID","Illinois":"IL","Indiana":"IN","Iowa":"IA","Kansas":"KS","Kentucky":"KY",
 "Louisiana":"LA","Maine":"ME","Maryland":"MD","Massachusetts":"MA","Michigan":"MI","Minnesota":"MN",
 "Mississippi":"MS","Missouri":"MO","Montana":"MT","Nebraska":"NE","Nevada":"NV","New Hampshire":"NH",
 "New Jersey":"NJ","New Mexico":"NM","New York":"NY","North Carolina":"NC","North Dakota":"ND",
 "Ohio":"OH","Oklahoma":"OK","Oregon":"OR","Pennsylvania":"PA","Rhode Island":"RI",
 "South Carolina":"SC","South Dakota":"SD","Tennessee":"TN","Texas":"TX","Utah":"UT","Vermont":"VT",
 "Virginia":"VA","Washington":"WA","West Virginia":"WV","Wisconsin":"WI","Wyoming":"WY",
 "District Of Columbia":"DC","Puerto Rico":"PR"}
STATE_CENTROID = {"AL":(32.8,-86.8),"AK":(63.6,-152.0),"AZ":(34.3,-111.7),"AR":(34.9,-92.4),
 "CA":(37.2,-119.5),"CO":(39.0,-105.5),"CT":(41.6,-72.7),"DE":(39.0,-75.5),"FL":(28.6,-81.7),
 "GA":(32.6,-83.4),"HI":(20.7,-156.4),"ID":(44.4,-114.6),"IL":(40.0,-89.2),"IN":(39.9,-86.3),
 "IA":(42.0,-93.5),"KS":(38.5,-98.4),"KY":(37.5,-85.3),"LA":(31.0,-92.0),"ME":(45.4,-69.2),
 "MD":(39.0,-76.8),"MA":(42.3,-71.8),"MI":(44.3,-85.4),"MN":(46.3,-94.3),"MS":(32.7,-89.7),
 "MO":(38.4,-92.5),"MT":(46.9,-110.0),"NE":(41.5,-99.8),"NV":(39.3,-116.6),"NH":(43.7,-71.6),
 "NJ":(40.1,-74.7),"NM":(34.4,-106.1),"NY":(42.9,-75.5),"NC":(35.5,-79.4),"ND":(47.5,-100.5),
 "OH":(40.3,-82.8),"OK":(35.6,-97.5),"OR":(44.0,-120.6),"PA":(40.9,-77.8),"RI":(41.7,-71.5),
 "SC":(33.9,-80.9),"SD":(44.4,-100.2),"TN":(35.9,-86.4),"TX":(31.5,-99.3),"UT":(39.3,-111.7),
 "VT":(44.1,-72.7),"VA":(37.5,-78.9),"WA":(47.4,-120.5),"WV":(38.6,-80.6),"WI":(44.6,-89.9),
 "WY":(43.0,-107.5),"DC":(38.9,-77.0),"PR":(18.2,-66.4)}

# ---------------- 侧栏 ① 上传 ----------------
with st.sidebar:
    st.header("① 上传数据")
    files = st.file_uploader("taskArrivalTaskList(.xlsx,可多选)", type=["xlsx"], accept_multiple_files=True,
                             help="一个文件即可(含发车与到车时间)。建议每次导近14天滚动窗口。")
    if st.button("处理并入库", type="primary", disabled=not files):
        with st.spinner("清洗入库中…"):
            s2r = cleaning.load_site2region("dim_site.csv")
            out = cleaning.clean(files, s2r)
            db.upsert_shipments(out)
            db.load_recent.clear()
        st.success(f"已入库/更新 {len(out)} 段")

# ---------------- 读数 ----------------
try:
    df_all = db.load_recent(400)
except Exception:
    st.error("连不上数据库。检查 secrets 连接串,并确认跑过 schema.sql。")
    st.stop()
if df_all.empty:
    st.warning("库里还没有数据,请先在左侧上传。"); st.stop()
for col in ("week", "route_name"):
    if col not in df_all.columns:
        df_all[col] = None
df_all["dep"] = pd.to_datetime(df_all["depart_date"], errors="coerce")
df_all["arr"] = pd.to_datetime(df_all["arrive_date"], errors="coerce")
df_all["dept"] = pd.to_datetime(df_all.get("depart_ts"), errors="coerce")
df_all["arrt"] = pd.to_datetime(df_all.get("arrive_ts"), errors="coerce")
df_all["dhour"] = df_all["dept"].dt.hour                                                # 发车时段(真实)
df_all["核载"] = df_all["vehicle_type"].map(RATED)
df_all["ldr"] = (df_all["load_tickets"] / df_all["核载"]).clip(upper=1.3)               # 装载率(估:票/核载)

@st.cache_data
def hub_state():
    ds = pd.read_csv("dim_site.csv", dtype=str)
    return dict(zip(ds["site_code"].str.strip(), ds["state"]))
H2S = hub_state()
def hub_ll(h):
    ab = STATE2ABBR.get(str(H2S.get(h)).title()) if H2S.get(h) else None
    return STATE_CENTROID.get(ab)

# ---------------- 侧栏 ② 设置 ----------------
with st.sidebar:
    st.header("② 看板设置")
    scope = st.radio("范围", ["一级+二级干线", "支线", "全部"], index=0)
    hubs = sorted({h for h in df_all["origin"].dropna() if str(h).endswith(".H")} |
                  {h for h in df_all["dest"].dropna() if str(h).endswith(".H")})
    obj = st.selectbox("对象", ["整体"] + hubs, index=0)
    period = st.radio("周期", ["单天", "周", "月"], index=0, horizontal=True)     # 年报已删(2025无数据)
    _vd = pd.to_datetime(df_all["depart_date"], errors="coerce").dropna()
    if period == "单天":
        sel = st.date_input("选日期", dt.date.today() - dt.timedelta(1))
    elif period == "周":
        wks = sorted([w for w in df_all["week"].dropna().unique()], reverse=True)
        sel = st.selectbox("选周 (ISO 周一→周日)", wks) if wks else None
    else:
        months = sorted({d.strftime("%Y-%m") for d in _vd.dt.date if d.year >= 2026}, reverse=True)  # 只留2026+
        sel = st.selectbox("选月", months) if months else None
    if sel is None:
        st.warning("该周期暂无数据。"); st.stop()

OBJ = None if obj == "整体" else obj
scope_types = {"支线": ["支线"], "全部": ["一级干线", "二级干线", "支线"]}.get(scope, ["一级干线", "二级干线"])
df = df_all[df_all.trunk_type.isin(scope_types)]

# ---------------- 周期区间 ----------------
def period_bounds(period, sel):
    if period == "单天":
        d0 = d1 = sel; label = f"{sel:%Y-%m-%d}(周{WD[sel.weekday()]})"
        p0 = p1 = sel - dt.timedelta(7); pl = "上周同日"
    elif period == "周":
        y, w = int(sel.split("-W")[0]), int(sel.split("-W")[1])
        d0 = dt.date.fromisocalendar(y, w, 1); d1 = d0 + dt.timedelta(6)
        p0, p1 = d0 - dt.timedelta(7), d1 - dt.timedelta(7); label = f"{sel} ({d0:%m/%d}-{d1:%m/%d})"; pl = "上周"
    else:
        y, m = int(sel.split("-")[0]), int(sel.split("-")[1])
        d0 = dt.date(y, m, 1); d1 = dt.date(y + (m == 12), (m % 12) + 1, 1) - dt.timedelta(1)
        pm, py = (12, y - 1) if m == 1 else (m - 1, y)
        p0 = dt.date(py, pm, 1); p1 = d0 - dt.timedelta(1); label = sel; pl = "上月"
    return d0, d1, p0, p1, label, pl
d0, d1, p0, p1, label, pl = period_bounds(period, sel)

# ---------------- 取数助手 ----------------
def sends(a, b, base=None):
    x = base if base is not None else df
    x = x[(x.dep >= pd.Timestamp(a)) & (x.dep <= pd.Timestamp(b))]
    return x[x.origin == OBJ] if OBJ else x
def recvs(a, b, base=None):
    x = base if base is not None else df
    x = x[(x.arr >= pd.Timestamp(a)) & (x.arr <= pd.Timestamp(b))]
    return x[x.dest == OBJ] if OBJ else x
def mend(x): return dt.date(x.year + (x.month == 12), (x.month % 12) + 1, 1) - dt.timedelta(1)
def month_list(endd, n=12):
    out = []
    for i in range(n - 1, -1, -1):
        yy, mm = endd.year, endd.month - i
        while mm <= 0: mm += 12; yy -= 1
        if dt.date(yy, mm, 1) >= dt.date(2026, 1, 1): out.append(dt.date(yy, mm, 1))   # 2026前过滤
    return out
def week_mondays(mon, n=12): return [mon - dt.timedelta(7 * i) for i in range(n - 1, -1, -1)]
def wk_lbl(m): return f"W{m.isocalendar()[1]:02d}"     # 周标签(x轴用 week number)
def rsend(a, b): s = sends(a, b); return s.load_tickets.sum()/WAN if metric == "票数" else s.task_id.nunique()
def rrecv(a, b): r = recvs(a, b); return r.unload_tickets.sum()/WAN if metric == "票数" else r.task_id.nunique()
def _demo(seed, lo, hi): return round(lo + (abs(hash(seed)) % 1000)/1000*(hi-lo), 1)   # 示例占位

# 车次口径:每个 MT(整条路线)算一次;发车归"整条路线始发站",收车归"终点站"(串点中间站不重复计)
_s = df.dropna(subset=["dept"]).sort_values("dept")
STARTS = _s.groupby("task_id", as_index=False).agg(origin=("origin", "first"), origin_region=("origin_region", "first"),
         depart_date=("depart_date", "first"), dhour=("dhour", "first"))
STARTS["d"] = pd.to_datetime(STARTS["depart_date"], errors="coerce")
_e = df.dropna(subset=["arrt"]).sort_values("arrt")
ENDS = _e.groupby("task_id", as_index=False).agg(dest=("dest", "last"), arrive_date=("arrive_date", "last"))
ENDS["a2"] = pd.to_datetime(ENDS["arrive_date"], errors="coerce")
def starts_range(a, b):
    x = STARTS[(STARTS.d >= pd.Timestamp(a)) & (STARTS.d <= pd.Timestamp(b))]
    return x[x.origin == OBJ] if OBJ else x
def ends_range(a, b):
    x = ENDS[(ENDS.a2 >= pd.Timestamp(a)) & (ENDS.a2 <= pd.Timestamp(b))]
    return x[x.dest == OBJ] if OBJ else x
def dstarts(x): return len(starts_range(x, x))

S, R, Sp, Rp = sends(d0, d1), recvs(d0, d1), sends(p0, p1), recvs(p0, p1)
sv, rv = S.load_tickets.sum(), R.unload_tickets.sum()
stp, rtp = len(starts_range(d0, d1)), len(ends_range(d0, d1))
sv0, rv0 = Sp.load_tickets.sum(), Rp.unload_tickets.sum()
stp0, rtp0 = len(starts_range(p0, p1)), len(ends_range(p0, p1))
ratio = rv / sv if sv else 0
_bal = "发多于收,留意空返" if ratio < 0.9 else ("收多于发,留意积压" if ratio > 1.1 else "收发基本均衡")
tsh = S.groupby("origin")["load_tickets"].sum(); top_s = tsh.idxmax() if len(tsh) and tsh.max() > 0 else "—"
trh = R.groupby("dest")["unload_tickets"].sum(); top_r = trh.idxmax() if len(trh) and trh.max() > 0 else "—"
def ratio_anomaly():                                   # 收发比偏离"自身常态±40%"且发货量够大才算异常
    hs = df.groupby("origin")["load_tickets"].sum(); hr = df.groupby("dest")["unload_tickets"].sum()
    cs = S.groupby("origin")["load_tickets"].sum(); cr = R.groupby("dest")["unload_tickets"].sum()
    out = []
    for h in set(cs.index) | set(cr.index):
        if not str(h).endswith(".H"): continue
        if min(cs.get(h, 0), cr.get(h, 0), hs.get(h, 0), hr.get(h, 0)) < 20000: continue  # 两向都要有量
        cur, norm = cr.get(h, 0)/cs.get(h, 1), hr.get(h, 0)/hs.get(h, 1)
        if 0.3 <= norm <= 3 and abs(cur/norm - 1) >= 0.4: out.append((h, cur, norm, abs(cur/norm - 1)))
    out.sort(key=lambda x: -x[3]); return out[:2]
if OBJ is None:
    _ra = ratio_anomaly()
    rsub = (f"异常 {_ra[0][0]} {_ra[0][1]:.2f}(常态{_ra[0][2]:.2f})" if _ra else "各 HUB 收发比正常")
else:
    _hn = df[df.dest == OBJ]["unload_tickets"].sum() / max(df[df.origin == OBJ]["load_tickets"].sum(), 1)
    rsub = f"该 HUB 常态收发比 {_hn:.2f}"

# ================================ 页头 + KPI(5卡)================================
st.title(f"📦 {(obj + ' · ') if OBJ else ''}{label}")
st.caption(f"数据最新发车日 {_vd.max().date()} · 覆盖 {_vd.dt.date.nunique()} 天 · 共 {len(df_all):,} 段")
def chip(cur, prev):
    if not prev: return '<span class="chip flat">—</span>'
    d = (cur/prev - 1) * 100
    cls = "up" if d > 0 else ("down" if d < 0 else "flat")
    arr = "▲" if d > 0 else ("▼" if d < 0 else "•")
    return f'<span class="chip {cls}">{arr} {abs(d):.1f}%</span>'
def kcard(tag, val, cur, prev, color, sub=""):
    ch = chip(cur, prev) if cur is not None else ""     # cur=None → 无环比胶囊(收发比卡用)
    return (f'<div class="kcard" style="--tc:{color}"><div class="tag">{tag}</div>'
            f'<div class="val">{val}</div><div class="foot">{ch}'
            f'<span class="sub">{sub or ("vs"+pl)}</span></div></div>')
kc = st.columns(5)
kc[0].markdown(kcard("发货量(万票)", f"{sv/WAN:.1f}", sv, sv0, BLUE, sub=f"最大发出 {top_s}"), unsafe_allow_html=True)
kc[1].markdown(kcard("收货量(万票)", f"{rv/WAN:.1f}", rv, rv0, GREEN, sub=f"最大收货 {top_r}"), unsafe_allow_html=True)
kc[2].markdown(kcard("发货车次", f"{stp:,}", stp, stp0, GRAY), unsafe_allow_html=True)
kc[3].markdown(kcard("收货车次", f"{rtp:,}", rtp, rtp0, GRAY), unsafe_allow_html=True)
kc[4].markdown(kcard("收发比(收/发)", f"{ratio:.2f}", None, None, ACCENT, sub=rsub), unsafe_allow_html=True)
st.markdown("<div style='height:30px'></div>", unsafe_allow_html=True)     # KPI 与下方图表留白(改这个数字调间距)

metric, unit = "票数", "万票"     # 票数/车次开关已删;统一按万票,车次在专用图里单独展示
def dsend(x): s = sends(x, x); return s.load_tickets.sum()/WAN if metric == "票数" else s.task_id.nunique()
def drecv(x): r = recvs(x, x); return r.unload_tickets.sum()/WAN if metric == "票数" else r.task_id.nunique()
def dldr(x):                                            # 当日平均装载率(估)%
    s = sends(x, x); return round(s["ldr"].mean()*100, 1) if len(s) else 0

# 同一行图统一:图外 markdown 标题 + 相同 height + 相同 t/b 边距 → 标题、x轴、底部都对齐
ROW_H = 340                                             # 同行图统一高度(想调一起改)
ROW_M = dict(l=10, r=10, t=20, b=44)                    # 同行图统一边距(t=顶 b=底)

def labeled_fig(cats, sv_, rv_, title):
    fig = go.Figure()
    fig.add_bar(x=cats, y=sv_, name="发货", marker_color="#93c5fd", cliponaxis=False,
                text=[f"{v:.0f}" for v in sv_], textposition="outside")
    fig.add_scatter(x=cats, y=sv_, mode="lines", line=dict(color=BLUE, width=2), name="发货趋势")
    fig.add_scatter(x=cats, y=rv_, mode="lines+markers", line=dict(color=GREEN, width=2), name="收货")
    if sv_:
        avg = sum(sv_)/len(sv_)
        fig.add_hline(y=avg, line_dash="dash", line_color=GRAY, annotation_text=f"发货均值{avg:.0f}", annotation_position="top left")
        i1 = max(range(len(sv_)), key=lambda i: sv_[i]); i2 = min(range(len(sv_)), key=lambda i: sv_[i])
        fig.add_scatter(x=[cats[i1]], y=[sv_[i1]], mode="markers", name="最高", marker=dict(color=GREEN, size=13, symbol="triangle-up"))
        fig.add_scatter(x=[cats[i2]], y=[sv_[i2]], mode="markers", name="最低", marker=dict(color=RED, size=13, symbol="triangle-down"))
    fig.update_layout(title_text=title, title_y=0.97, height=ROW_H, margin=dict(l=10, r=10, t=55, b=10),
                      legend=dict(orientation="h", y=1.13, x=0), barmode="overlay", yaxis_title=unit)
    fig.update_yaxes(rangemode="tozero"); return fig

def weekday_fig(mark_day=None, h=ROW_H):                # 标题走图外 markdown;h 可调,和同行表格底部对齐
    t2 = (df if OBJ is None else df[df.origin == OBJ]).dropna(subset=["depart_date"]).copy()
    t2["wd"] = t2["depart_date"].map(lambda d: d.weekday())
    wdavg = (t2.groupby(["wd", "depart_date"])["load_tickets"].sum().groupby("wd").mean()/WAN).reindex(range(7)).fillna(0)
    f = go.Figure(go.Bar(x=[f"周{WD[i]}" for i in range(7)], y=wdavg.round(1).values, marker_color="#cbd5e1",
                         cliponaxis=False, text=[f"{v:.0f}" for v in wdavg.values], textposition="outside", name="均值"))
    if mark_day is not None:                            # 标出所选日期的实际货量
        val = sends(mark_day, mark_day).load_tickets.sum()/WAN
        f.add_scatter(x=[f"周{WD[mark_day.weekday()]}"], y=[val], mode="markers+text", text=[f"当日{val:.0f}"],
                      textposition="top center", marker=dict(color=RED, size=14, symbol="diamond"), name="所选日")
    f.update_layout(height=h, margin=ROW_M, yaxis_title="万票", showlegend=False)
    f.update_yaxes(rangemode="tozero"); return f

# ================================ 趋势 ================================
if period == "单天":
    days = [d1 - dt.timedelta(i) for i in range(29, -1, -1)]
    fig = go.Figure()
    fig.add_scatter(x=days, y=[dsend(x) for x in days], name="发货", mode="lines+markers", line=dict(color=BLUE, width=2.5), marker=dict(size=5))
    fig.add_scatter(x=days, y=[drecv(x) for x in days], name="收货", mode="lines+markers", line=dict(color=GREEN, width=2.5), marker=dict(size=5))
    fig.add_scatter(x=days, y=[dldr(x) for x in days], name="装载率(估)%", mode="lines", line=dict(color=ACCENT, width=1.6, dash="dot"), yaxis="y2")
    for x in days:
        if x.weekday() == 6:
            fig.add_vline(x=dt.datetime.combine(x, dt.time()), line_width=1, line_dash="dot", line_color="#e2e8f0")
    fig.update_layout(height=ROW_H, margin=ROW_M, yaxis_title="万票", hovermode="x unified",
                      legend=dict(orientation="h", y=1.02, x=0),
                      yaxis2=dict(title="装载率%", overlaying="y", side="right", range=[0, 110], showgrid=False))
    fig.update_xaxes(dtick=7*86400000, tickformat="%m/%d"); fig.update_yaxes(rangemode="tozero")
    # 右侧:近30天 供应商集中度(前1大 / 前3大 承运占比;越高越依赖少数承运商)
    cr1, cr3 = [], []
    for x in days:
        sp = sends(x, x).groupby("supplier")["load_tickets"].sum().sort_values(ascending=False); tot = sp.sum()
        cr1.append(round(sp.iloc[0]/tot*100, 1) if tot > 0 and len(sp) else 0)
        cr3.append(round(sp.head(3).sum()/tot*100, 1) if tot > 0 else 0)
    figc = go.Figure()
    figc.add_scatter(x=days, y=cr3, name="前3大占比", mode="lines", line=dict(color="#8b5cf6", width=2.5),
                     fill="tozeroy", fillcolor="rgba(139,92,246,.08)")
    figc.add_scatter(x=days, y=cr1, name="第1大占比", mode="lines", line=dict(color=ACCENT, width=2))
    figc.update_layout(height=ROW_H, margin=ROW_M, yaxis_title="占比%", yaxis_range=[0, 100], hovermode="x unified",
                       legend=dict(orientation="h", y=1.02, x=0))
    figc.update_xaxes(dtick=7*86400000, tickformat="%m/%d")
    c1, c2 = st.columns([2, 1])
    c1.markdown("**近30天收发趋势与装载率(估)**"); c1.plotly_chart(fig, use_container_width=True)
    c1.caption("发货按发车日、收货按到车日;货平均在途约1天,故单日发≠收属正常错位,看周/月更准。")
    c2.markdown("**供应商集中度(前1/前3大占比)**"); c2.plotly_chart(figc, use_container_width=True)
    if OBJ is None:                                    # 整体日报:星期货量均值 + 星期车次均值 + 加/减车(同一行)
        WROW_H = 390                                   # 第二行图高(拉长,和右侧加减车表底部对齐)
        w1, w2, w3 = st.columns([1, 1, 1.1])
        w1.markdown("**各星期发货量均值 vs 单日**"); w1.plotly_chart(weekday_fig(mark_day=sel, h=WROW_H), use_container_width=True)
        sw = STARTS.dropna(subset=["depart_date"]).copy(); sw["wd"] = sw["depart_date"].map(lambda d: d.weekday())
        tavg = sw.groupby(["wd", "depart_date"]).size().groupby("wd").mean().reindex(range(7)).fillna(0)
        today_tr = dstarts(sel)
        fv = go.Figure(go.Bar(x=[f"周{WD[i]}" for i in range(7)], y=tavg.round(0).values, marker_color="#cbd5e1",
                       text=[f"{v:.0f}" for v in tavg.values], textposition="outside", cliponaxis=False))
        fv.add_scatter(x=[f"周{WD[sel.weekday()]}"], y=[today_tr], mode="markers+text", text=[f"当日{today_tr}"],
                       textposition="top center", marker=dict(color=RED, size=14, symbol="diamond"))
        fv.update_layout(height=WROW_H, margin=ROW_M, showlegend=False, yaxis_title="车次")
        w2.markdown("**各星期平均发货车次 vs 单日**"); w2.plotly_chart(fv, use_container_width=True)
        wm = STARTS[STARTS["depart_date"].map(lambda d: d is not None and not pd.isna(d) and d.weekday() == sel.weekday())]
        norm = wm.groupby(["origin", "depart_date"]).size().groupby("origin").mean()
        tod = starts_range(sel, sel).groupby("origin").size()
        rows = []
        for h in sorted(set(norm.index) | set(tod.index)):
            if not str(h).endswith(".H"): continue
            diff = tod.get(h, 0) - norm.get(h, 0)
            rows.append({"HUB": h, "今日车次": int(tod.get(h, 0)), "该星期均值": round(norm.get(h, 0), 1), "增减(车)": round(diff, 1)})
        rows.sort(key=lambda r: -abs(r["增减(车)"]))
        w3.markdown("**加减车次情况**")
        if rows: w3.dataframe(pd.DataFrame(rows).set_index("HUB"), use_container_width=True, height=WROW_H - 40)
        else: w3.info("暂无数据")
    else:
        st.markdown("**各星期发货量均值 vs 单日**")
        st.plotly_chart(weekday_fig(mark_day=sel), use_container_width=True)
elif period == "周":
    days = [d0 + dt.timedelta(i) for i in range(7)]
    def gbar(vthis, vlast, title, ytitle):
        txt = [f"{v:.0f}<br>{((v/l-1)*100):+.0f}%" if l else f"{v:.0f}" for v, l in zip(vthis, vlast)]
        mx = max(list(vthis) + list(vlast) + [1])
        f = go.Figure()
        f.add_bar(x=[f"周{WD[i]}" for i in range(7)], y=vthis, name="本周", marker_color=BLUE,
                  text=txt, textposition="outside", cliponaxis=False, textfont=dict(size=11))
        f.add_bar(x=[f"周{WD[i]}" for i in range(7)], y=vlast, name="上周", marker_color="#cbd5e1")
        f.update_layout(height=ROW_H, barmode="group", margin=ROW_M, legend=dict(orientation="h", y=1.02, x=0),
                        yaxis_title=ytitle, yaxis_range=[0, mx * 1.32])   # 顶部留白,标签不顶到标题
        return f
    sthis = [sends(days[i], days[i]).load_tickets.sum()/WAN for i in range(7)]
    slast = [sends(days[i]-dt.timedelta(7), days[i]-dt.timedelta(7)).load_tickets.sum()/WAN for i in range(7)]
    tthis = [dstarts(days[i]) for i in range(7)]
    tlast = [dstarts(days[i]-dt.timedelta(7)) for i in range(7)]
    c1, c2 = st.columns(2)
    c1.markdown("**本周 vs 上周 每天发货量(万票)· 本周柱标 vs上周%**"); c1.plotly_chart(gbar(sthis, slast, "", "万票"), use_container_width=True)
    c2.markdown("**本周 vs 上周 每天发货车次 · 本周柱标 vs上周%**"); c2.plotly_chart(gbar(tthis, tlast, "", "车次"), use_container_width=True)
    ld = [round(sends(days[i], days[i])["ldr"].mean()*100, 1) if len(sends(days[i], days[i])) else 0 for i in range(7)]
    fld = go.Figure(go.Bar(x=[f"{days[i]:%m/%d}周{WD[days[i].weekday()]}" for i in range(7)], y=ld, marker_color=ACCENT,
                    text=[f"{v:.0f}%" for v in ld], textposition="outside", cliponaxis=False))
    fld.update_layout(height=260, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="装载率%", yaxis_range=[0, 110])
    st.markdown("**本周每天 平均装载率(估)%**"); st.plotly_chart(fld, use_container_width=True)
    mons = week_mondays(d0, 12)
    st.markdown("**近12周 收发趋势(万票)**")
    st.plotly_chart(labeled_fig([wk_lbl(m) for m in mons], [rsend(m, m+dt.timedelta(6)) for m in mons],
                    [rrecv(m, m+dt.timedelta(6)) for m in mons], ""), use_container_width=True)
else:
    ms = month_list(d1, 12)
    st.markdown("**近12个月 收发趋势(万票)· 均值/最高低**")
    st.plotly_chart(labeled_fig([f"{m:%Y-%m}" for m in ms], [rsend(m, mend(m)) for m in ms],
                    [rrecv(m, mend(m)) for m in ms], ""), use_container_width=True)

# ================================ 结构:干支甜甜圈 + 大区→hub 旭日图 + 明细 ================================
Sall = sends(d0, d1, base=df_all)
rc, hc = ("origin_region", "origin") if OBJ is None else ("dest_region", "dest")
sb = (S.groupby([rc, hc])["load_tickets"].sum()/WAN).round(2).reset_index()
sb = sb[(sb["load_tickets"] > 0) & (sb[hc].astype(str).str.endswith(".H"))]     # 只留 .H 枢纽
g1, g2, g3 = st.columns([1, 1.25, 1])
with g1:
    st.markdown("**干线/支线占比**")
    stt = (Sall.groupby("trunk_type")["load_tickets"].sum()/WAN).round(1)
    stt = stt[stt > 0].rename_axis("运输类型").reset_index()
    if len(stt):
        fig = px.pie(stt, names="运输类型", values="load_tickets", hole=.45, height=ROW_H, color_discrete_sequence=PIE)
        fig.update_traces(texttemplate="%{label}<br>%{value:.1f}万·%{percent}", textposition="inside", sort=True)
        fig.update_layout(margin=dict(l=6, r=6, t=6, b=6), showlegend=False, uniformtext_minsize=11, uniformtext_mode="hide")
        st.plotly_chart(fig, use_container_width=True)
with g2:
    st.markdown(("**大区/HUB占比**" if OBJ is None else f"**{obj} 发往:大区 → hub**"))
    if len(sb):
        fig = px.sunburst(sb, path=[rc, hc], values="load_tickets", height=ROW_H, color_discrete_sequence=PIE)
        fig.update_traces(textinfo="label+percent parent", insidetextorientation="radial")
        fig.update_layout(margin=dict(l=6, r=6, t=6, b=6))
        st.plotly_chart(fig, use_container_width=True)
with g3:
    st.markdown("**大区 / HUB 明细**")                  # 保留一行标题,和左边两张图顶部对齐
    if len(sb):
        tot = sb["load_tickets"].sum() or 1
        tb = sb.sort_values("load_tickets", ascending=False).copy()
        tb["占比"] = (tb["load_tickets"]/tot*100).round(1).astype(str) + "%"
        tb = tb.rename(columns={rc: "大区", hc: "HUB", "load_tickets": "万票"})[["大区", "HUB", "万票", "占比"]]
        st.dataframe(tb, use_container_width=True, height=ROW_H, hide_index=True)

# 周/月:大区占比趋势(堆叠面积,看结构变化)
if period in ("周", "月"):
    st.markdown("**大区发货占比趋势**")
    per = week_mondays(d0, 10) if period == "周" else month_list(d1, 12)
    rowsx = []
    for pm in per:
        a, b = (pm, pm+dt.timedelta(6)) if period == "周" else (pm, mend(pm))
        gg = sends(a, b).groupby("origin_region")["load_tickets"].sum()
        for reg, v in gg.items():
            rowsx.append({"期": wk_lbl(pm) if period == "周" else f"{pm:%Y-%m}", "大区": reg, "发货": v})
    if rowsx:
        area = px.area(pd.DataFrame(rowsx), x="期", y="发货", color="大区", groupnorm="fraction",
                       height=300, color_discrete_sequence=PIE)
        area.update_layout(margin=dict(l=6, r=6, t=6, b=6), yaxis_tickformat=".0%", yaxis_title="占比")
        st.plotly_chart(area, use_container_width=True)

# ================================ Top 线路(始发→目的)货量 ================================
if period != "单天":                                    # 日报里删掉此图
    st.markdown("**Top 线路(始发→目的)发货量(万票)**")
    lane = (S.groupby(["origin", "dest"])["load_tickets"].sum()/WAN).round(1).sort_values(ascending=True).tail(10)
    if len(lane):
        ldf = lane.reset_index(); ldf["线路"] = ldf["origin"] + "→" + ldf["dest"]
        fl = px.bar(ldf, x="load_tickets", y="线路", orientation="h", text="load_tickets",
                    labels={"load_tickets": "万票", "线路": ""}, height=320)
        fl.update_traces(marker_color=BLUE, textposition="outside", cliponaxis=False)
        fl.update_layout(margin=dict(l=6, r=6, t=6, b=6)); st.plotly_chart(fl, use_container_width=True)

# 周/月:Top 线路货量趋势(多线)
if period in ("周", "月"):
    st.markdown("**Top5 线路 货量趋势**")
    top5 = (S.groupby(["origin", "dest"])["load_tickets"].sum().sort_values(ascending=False).head(5).index)
    per = week_mondays(d0, 10) if period == "周" else month_list(d1, 12)
    rl = []
    for pm in per:
        a, b = (pm, pm+dt.timedelta(6)) if period == "周" else (pm, mend(pm))
        sub = sends(a, b)
        for (o, de) in top5:
            v = sub[(sub.origin == o) & (sub.dest == de)]["load_tickets"].sum()/WAN
            rl.append({"期": wk_lbl(pm) if period == "周" else f"{pm:%Y-%m}", "线路": f"{o}→{de}", "发货": round(v, 1)})
    if rl:
        fll = px.line(pd.DataFrame(rl), x="期", y="发货", color="线路", markers=True, height=300, color_discrete_sequence=PIE)
        fll.update_layout(margin=dict(l=6, r=6, t=6, b=6), yaxis_title="万票"); st.plotly_chart(fll, use_container_width=True)

# ================================ 地图(整体):热力 + 今日 Top 线路表 ================================
if OBJ is None:
    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)   # 与上一行留白(第四行整体下移)
    MAP_H = 430
    mcol, tcol = st.columns([2, 1])
    mm = S.copy(); mm["st"] = mm["origin"].map(H2S).map(lambda s: STATE2ABBR.get(str(s).title()) if s else None)
    mp = (mm.dropna(subset=["st"]).groupby("st")["load_tickets"].sum()/WAN).round(1)
    with mcol:
        st.markdown("**各州发货量热力图**")
        if len(mp):
            hi = mp.max() or 1
            figm = go.Figure(go.Choropleth(locations=mp.index, locationmode="USA-states", z=mp.values, colorscale="Blues",
                             colorbar_title="万票", marker_line_color="white", marker_line_width=.5,
                             hovertemplate="%{location}: %{z:.1f} 万票<extra></extra>"))
            lab = [(STATE_CENTROID[s][1], STATE_CENTROID[s][0], f"{s}<br>{v:.1f}",     # 1位小数:不足整万也不显示0
                    "white" if v > hi*0.45 else "#18212e") for s, v in mp.items() if s in STATE_CENTROID]
            figm.add_trace(go.Scattergeo(lon=[x[0] for x in lab], lat=[x[1] for x in lab], text=[x[2] for x in lab],
                           mode="text", hoverinfo="skip", showlegend=False,
                           textfont=dict(size=10, color=[x[3] for x in lab], family="Arial")))
            figm.update_geos(scope="usa", showlakes=False, bgcolor="rgba(0,0,0,0)")
            figm.update_layout(height=MAP_H, margin=dict(l=0, r=0, t=0, b=0)); st.plotly_chart(figm, use_container_width=True)
    with tcol:
        st.markdown("**今日 Top 线路**")
        lf = S.groupby(["origin", "dest"])["load_tickets"].sum().sort_values(ascending=False).head(10)
        if len(lf):
            lt = lf.reset_index(); lt["线路"] = lt["origin"] + "→" + lt["dest"]
            lt["万票"] = (lt["load_tickets"]/WAN).round(1); lt["票数"] = lt["load_tickets"].astype(int)   # 完整票数
            st.dataframe(lt[["线路", "万票", "票数"]], use_container_width=True, height=MAP_H, hide_index=True)

    st.markdown("**各 HUB 收发(车次 · 完整票数)与净流量**")
    g_send = df[(df.dep >= pd.Timestamp(d0)) & (df.dep <= pd.Timestamp(d1))].groupby("origin")["load_tickets"].sum().rename("发货票")
    g_recv = df[(df.arr >= pd.Timestamp(d0)) & (df.arr <= pd.Timestamp(d1))].groupby("dest")["unload_tickets"].sum().rename("收货票")
    n_send = starts_range(d0, d1).groupby("origin").size().rename("发车")
    n_recv = ends_range(d0, d1).groupby("dest").size().rename("收车")
    bal = pd.concat([n_send, g_send, n_recv, g_recv], axis=1).fillna(0)
    bal = bal[bal.index.astype(str).str.endswith(".H")]
    for c in ["发车", "收车", "发货票", "收货票"]: bal[c] = bal[c].astype(int)
    bal["净流量(票)"] = (bal["发货票"] - bal["收货票"]).astype(int)
    bal["净车次"] = (bal["发车"] - bal["收车"]).astype(int); bal.index.name = "hub"
    bal = bal.rename(columns={"发货票": "发货票数", "收货票": "收货票数"})
    st.dataframe(bal[["发车", "发货票数", "收车", "收货票数", "净流量(票)", "净车次"]].sort_values("净流量(票)", ascending=False),
                 use_container_width=True, height=340)

# ================================ hub 深度视图 ================================
if OBJ:
    st.divider(); st.header(f"🏭 {obj} · 枢纽深度")
    h1, h2 = st.columns(2)
    with h1:
        st.markdown("**主要发往 HUB(发货 万票)**")
        dd = (S.groupby("dest")["load_tickets"].sum()/WAN).round(1).sort_values(ascending=True).tail(10)
        if len(dd):
            f = px.bar(dd.reset_index(), x="load_tickets", y="dest", orientation="h", text="load_tickets",
                       labels={"load_tickets": "万票", "dest": ""}, height=ROW_H)
            f.update_traces(marker_color=GREEN, textposition="outside", cliponaxis=False)
            f.update_layout(margin=dict(l=6, r=6, t=6, b=6)); st.plotly_chart(f, use_container_width=True)
    with h2:
        st.markdown("**发车时段分布(按 MT · 实际发车钟点)**")
        stq = starts_range(d0, d1).dropna(subset=["dhour"])
        hh = stq.groupby(stq["dhour"].astype("Int64")).size().reindex(range(24)).fillna(0)
        f = px.bar(x=[f"{i:02d}" for i in range(24)], y=hh.values, labels={"x": "时", "y": "车次"}, height=ROW_H)
        f.update_traces(marker_color=BLUE); f.update_layout(margin=dict(l=6, r=6, t=6, b=6))
        st.plotly_chart(f, use_container_width=True)

    st.markdown("**同线路货量:本期 vs 上期(万票)**")
    cur = S.groupby(["origin", "dest"])["load_tickets"].sum()/WAN
    prev = Sp.groupby(["origin", "dest"])["load_tickets"].sum()/WAN
    top_l = cur.sort_values(ascending=False).head(8).index
    comp = pd.DataFrame({"线路": [f"{o}→{de}" for (o, de) in top_l],
                         "本期": [round(cur.get((o, de), 0), 1) for (o, de) in top_l],
                         f"上期({pl})": [round(prev.get((o, de), 0), 1) for (o, de) in top_l]})
    if len(comp):
        fc = px.bar(comp.melt(id_vars="线路", var_name="期", value_name="万票"), x="线路", y="万票", color="期",
                    barmode="group", height=300, color_discrete_sequence=[BLUE, "#cbd5e1"])
        fc.update_layout(margin=dict(l=6, r=6, t=6, b=6)); st.plotly_chart(fc, use_container_width=True)

    s1, s2 = st.columns(2)
    with s1:
        st.markdown("**主要供应商(发货 万票)**")
        sup = (S.groupby("supplier")["load_tickets"].sum()/WAN).round(1).sort_values(ascending=True).tail(10)
        if len(sup):
            f = px.bar(sup.reset_index(), x="load_tickets", y="supplier", orientation="h", text="load_tickets",
                       labels={"load_tickets": "万票", "supplier": ""}, height=ROW_H)
            f.update_traces(marker_color="#8b5cf6", textposition="outside", cliponaxis=False)
            f.update_layout(margin=dict(l=6, r=6, t=6, b=6)); st.plotly_chart(f, use_container_width=True)
    with s2:
        st.markdown("**各供应商 跑哪些线路**")
        sr = S.copy(); sr["线路"] = sr["origin"] + "→" + sr["dest"]
        srt = sr.groupby("supplier").agg(线路数=("线路", "nunique"), 发货万票=("load_tickets", lambda x: round(x.sum()/WAN, 1)),
                主要线路=("线路", lambda x: x.value_counts().idxmax() if len(x) else "")).sort_values("发货万票", ascending=False)
        st.dataframe(srt, use_container_width=True, height=ROW_H)

    st.markdown(f"**准时率 与 操作时长 <span class='demo'>示例数据</span>**", unsafe_allow_html=True)
    dd2 = sorted({t.date() for t in pd.to_datetime(pd.concat([S["dep"], R["arr"]]), errors="coerce").dropna()})[-14:]
    demo = pd.DataFrame({"日期": dd2, "准时率%": [_demo(f"{obj}{x}otp", 78, 96) for x in dd2],
                         "操作时长(分)": [_demo(f"{obj}{x}op", 45, 95) for x in dd2]})
    if len(demo):
        f = go.Figure()
        f.add_bar(x=demo["日期"], y=demo["操作时长(分)"], name="操作时长(分)", marker_color="#cbd5e1")
        f.add_scatter(x=demo["日期"], y=demo["准时率%"], name="准时率%", mode="lines+markers", line=dict(color=GREEN), yaxis="y2")
        f.update_layout(height=300, margin=dict(l=6, r=6, t=10, b=6), legend=dict(orientation="h", y=1.15),
                        yaxis_title="操作时长(分)", yaxis2=dict(title="准时率%", overlaying="y", side="right", range=[0, 100]))
        st.plotly_chart(f, use_container_width=True)
        st.caption("⚠️ 准时率/操作时长为示例占位;上线前接入 计划到车时间、卸车完成时间 等真实列。")

    if period != "单天":
        st.markdown(f"**{obj} 期内每日 发/收**")
        dd = sorted({t.date() for t in pd.to_datetime(pd.concat([S["dep"], R["arr"]]), errors="coerce").dropna()})
        rows = [{"日期": x, "发车": sends(x, x).task_id.nunique(), "发货(万票)": round(sends(x, x).load_tickets.sum()/WAN, 2),
                 "收车": recvs(x, x).task_id.nunique(), "收货(万票)": round(recvs(x, x).unload_tickets.sum()/WAN, 2)} for x in dd]
        if rows: st.dataframe(pd.DataFrame(rows).set_index("日期"), use_container_width=True, height=280)

# ================================ 流向明细 ================================
st.divider(); st.header("🔎 流向明细")
st.caption("口径:按段(始发地→目的地);串点线路各段分别计。")
Sd = sends(d0, d1)
f1, f2, f3 = st.columns(3)
regs = sorted([r for r in Sd["origin_region"].dropna().unique()])
sel_reg = f1.multiselect("大区(始发)", regs, default=[])
sel_o = f2.multiselect("始发地", sorted(set(Sd["origin"])), default=[])
sel_d = f3.multiselect("目的地", sorted(set(Sd["dest"])), default=[])
dl = Sd
if sel_reg: dl = dl[dl["origin_region"].isin(sel_reg)]
if sel_o: dl = dl[dl["origin"].isin(sel_o)]
if sel_d: dl = dl[dl["dest"].isin(sel_d)]

st.subheader("明细(每段:MT · 路线 · 始发→目的 · 收发)")
det = dl[["task_id", "route_name", "origin", "dest", "load_tickets", "unload_tickets", "supplier"]].copy()
det.columns = ["MT号", "整段路线", "始发", "目的", "装车票", "卸车票", "供应商"]
det = det.sort_values("装车票", ascending=False)
st.dataframe(det, use_container_width=True, height=360, hide_index=True)
st.download_button("⬇ 导出流向明细 CSV", det.to_csv(index=False).encode("utf-8-sig"), file_name=f"流向明细_{label}.csv", mime="text/csv")

st.subheader("异常清单:放空 / 低装载(<50%)")
a = dl.copy(); a["装载率"] = a["ldr"].round(3)
empty = a[a["load_tickets"] == 0].assign(类型="放空(0票)")
low = a[(a["load_tickets"] > 0) & (a["装载率"] < 0.5)].assign(类型="低装载<50%")
anom = pd.concat([empty, low])[["类型", "task_id", "route_name", "origin", "dest", "vehicle_type", "load_tickets", "装载率", "supplier"]].rename(
    columns={"task_id": "MT号", "route_name": "整段路线", "origin": "始发", "dest": "目的",
             "load_tickets": "装车票", "vehicle_type": "车型", "supplier": "供应商"})
st.caption(f"区间异常段:放空 {len(empty)} · 低装载 {len(low)}")
st.dataframe(anom, use_container_width=True, height=260, hide_index=True)
if len(anom):
    st.download_button("⬇ 导出异常清单 CSV", anom.to_csv(index=False).encode("utf-8-sig"), file_name=f"异常清单_{label}.csv", mime="text/csv")
