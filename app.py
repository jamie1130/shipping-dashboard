# -*- coding: utf-8 -*-
"""干线收发货看板(Streamlit)。上传发货/收货 → 清洗入库 → 日/周报。"""
import io, datetime
import streamlit as st
import pandas as pd
import plotly.express as px
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import cleaning, db

matplotlib.rcParams["font.sans-serif"] = ["Noto Sans CJK SC", "Noto Sans CJK JP",
    "WenQuanYi Zen Hei", "Microsoft YaHei", "SimHei", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
st.set_page_config(page_title="干线收发货看板", layout="wide")
WAN = 10000
WD = ["一", "二", "三", "四", "五", "六", "日"]

# ---------------- 侧栏:上传 + 设置 ----------------
with st.sidebar:
    st.header("① 上传昨日数据")
    f1 = st.file_uploader("发货 taskArrivalTaskList", type=["xlsx"], key="fa")
    f2 = st.file_uploader("收货 taskArrivalTaskList", type=["xlsx"], key="sh")
    if st.button("处理并入库", type="primary", disabled=not (f1 and f2)):
        with st.spinner("清洗入库中…"):
            s2r = cleaning.load_site2region("dim_site.csv")
            out = cleaning.clean(f1, f2, s2r)
            db.upsert_shipments(out)
            db.load_recent.clear()
        st.success(f"已入库/更新 {len(out)} 段")
    st.divider()
    st.header("② 看板设置")
    scope = st.radio("范围", ["一级+二级干线", "支线", "全部"], index=0)
    report = st.radio("报表", ["日报", "周报"], index=0)
    day = st.date_input("日期(默认昨天)", datetime.date.today() - datetime.timedelta(days=1))

# ---------------- 读数 ----------------
try:
    df = db.load_recent(70)
except Exception:
    st.error("连不上数据库。请检查 .streamlit/secrets.toml 里的连接串,并确认已在 Supabase 跑过 schema.sql。")
    st.stop()
if scope == "一级+二级干线":
    df = df[df.trunk_type.isin(["一级干线", "二级干线"])]
elif scope == "支线":
    df = df[df.trunk_type == "支线"]
if df.empty:
    st.warning("库里还没有对应数据,请先在左侧上传发货/收货文件。")
    st.stop()

def send_day(d):
    s = df[df.depart_date == d]; return s.load_tickets.sum(), s.task_id.nunique()
def recv_day(d):
    s = df[df.arrive_date == d]; return s.unload_tickets.sum(), s.task_id.nunique()

# ---------------- 日报 ----------------
if report == "日报":
    st.title(f"干线收发货日报 · {day:%m/%d}(周{WD[day.weekday()]})")
    st.caption(f"发货按发车日 · 收货按到车日 · {scope} · 对比上周同日 {day - datetime.timedelta(7):%m/%d}")
    prev = day - datetime.timedelta(7)
    sv, stp = send_day(day); rv, rtp = recv_day(day)
    sv0, stp0 = send_day(prev); rv0, rtp0 = recv_day(prev)
    def wow(a, b): return (f"{(a/b-1)*100:+.1f}% vs上周" if b else "—")
    c = st.columns(4)
    c[0].metric("发货量(万票)", f"{sv/WAN:.1f}", wow(sv, sv0))
    c[1].metric("收货量(万票)", f"{rv/WAN:.1f}", wow(rv, rv0))
    c[2].metric("发货车次", f"{stp}", wow(stp, stp0))
    c[3].metric("收货车次", f"{rtp}", wow(rtp, rtp0))

    days = [day - datetime.timedelta(i) for i in range(29, -1, -1)]
    tr = pd.DataFrame({"日期": days,
                       "发货量": [send_day(x)[0]/WAN for x in days],
                       "收货量": [recv_day(x)[0]/WAN for x in days]})
    st.plotly_chart(px.line(tr, x="日期", y=["发货量", "收货量"], markers=True,
                            title="近30天 收发趋势(万票)"), use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("各 hub 当日收发(万票)")
        s = df[df.depart_date == day].groupby("origin")["load_tickets"].sum()
        r = df[df.arrive_date == day].groupby("dest")["unload_tickets"].sum()
        hub = pd.DataFrame({"发货": s, "收货": r}).fillna(0)
        hub = hub[hub.index.astype(str).str.endswith(".H")]
        st.dataframe((hub/WAN).round(2).sort_values("发货", ascending=False),
                     use_container_width=True, height=360)
    with col2:
        st.subheader("大区流向热图(当日发货 万票)")
        fm = df[df.depart_date == day].pivot_table(index="origin_region", columns="dest_region",
                values="load_tickets", aggfunc="sum", fill_value=0) / WAN
        if not fm.empty:
            st.plotly_chart(px.imshow(fm.round(1), text_auto=True, aspect="auto",
                            color_continuous_scale="Blues",
                            labels=dict(x="目的大区", y="始发大区", color="万票")),
                            use_container_width=True)

    st.subheader("异常拠点:各 hub 发货量环比上周同日")
    s_now = df[df.depart_date == day].groupby("origin")["load_tickets"].sum()
    s_prev = df[df.depart_date == prev].groupby("origin")["load_tickets"].sum()
    hubs = [h for h in s_now.index if str(h).endswith(".H")]
    ano = pd.DataFrame({"now": s_now.reindex(hubs).fillna(0), "prev": s_prev.reindex(hubs).fillna(0)})
    ano = ano[ano["prev"] > 0].copy()
    ano["环比%"] = ((ano["now"]/ano["prev"] - 1) * 100).round(0)
    ano = ano.sort_values("环比%")
    if not ano.empty:
        st.plotly_chart(px.bar(ano.reset_index(), x="origin", y="环比%", color="环比%",
                        color_continuous_scale="RdYlGn", title="环比%(±20%内为常态)"),
                        use_container_width=True)

    # 导出 PNG(复刻日报图)
    fig, ax = plt.subplots(2, 1, figsize=(11, 8), gridspec_kw={"height_ratios": [1, 1.3]})
    fig.suptitle(f"干线收发货日报  {day:%m/%d}(周{WD[day.weekday()]})· {scope}", fontsize=15, weight="bold")
    ax[0].axis("off")
    kpis = [("发货量", f"{sv/WAN:.1f}万", wow(sv, sv0)), ("收货量", f"{rv/WAN:.1f}万", wow(rv, rv0)),
            ("发货车次", f"{stp}", wow(stp, stp0)), ("收货车次", f"{rtp}", wow(rtp, rtp0))]
    for i, (lab, val, d2) in enumerate(kpis):
        x = 0.02 + i*0.25
        ax[0].text(x, 0.7, lab, fontsize=12, color="#666")
        ax[0].text(x, 0.4, val, fontsize=20, weight="bold")
        ax[0].text(x, 0.15, d2, fontsize=10, color="#2a7")
    ax[1].plot(tr["日期"], tr["发货量"], "-o", ms=3, label="发货量", color="#2563eb")
    ax[1].plot(tr["日期"], tr["收货量"], "-o", ms=3, label="收货量", color="#16a34a")
    ax[1].set_title("近30天 收发趋势(万票)"); ax[1].legend(); ax[1].grid(alpha=.3)
    fig.autofmt_xdate(); plt.tight_layout()
    buf = io.BytesIO(); fig.savefig(buf, format="png", dpi=110, bbox_inches="tight"); plt.close(fig)
    st.download_button("⬇ 导出日报 PNG", buf.getvalue(),
                       file_name=f"收发货日报_{day:%Y%m%d}.png", mime="image/png")

# ---------------- 周报 ----------------
else:
    st.title(f"干线收发货周报 · {scope}")
    st.caption("按发车日归 ISO 周")
    dfx = df.copy()
    dfx["周"] = pd.to_datetime(dfx["depart_date"]).dt.to_period("W").astype(str)
    wk = dfx.groupby("周").agg(发货量万票=("load_tickets", lambda s: round(s.sum()/WAN, 1)),
                               发货车次=("task_id", "nunique")).tail(8)
    st.plotly_chart(px.bar(wk.reset_index(), x="周", y="发货量万票", title="周度发货趋势(万票)"),
                    use_container_width=True)
    st.subheader("按运输类型 × 周(发货量 万票)")
    pt = dfx.pivot_table(index="trunk_type", columns="周", values="load_tickets",
                         aggfunc="sum", fill_value=0) / WAN
    st.dataframe(pt.round(1), use_container_width=True)
    st.subheader("各 hub 周度发货(万票,近8周)")
    hh = dfx[dfx.origin.astype(str).str.endswith(".H")].pivot_table(
        index="origin", columns="周", values="load_tickets", aggfunc="sum", fill_value=0) / WAN
    st.dataframe(hh.round(1), use_container_width=True)
