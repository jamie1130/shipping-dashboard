# 干线收发货看板 · 搭建清单(Streamlit + Supabase)

一个网页:每天上传发货/收货两个文件 → 自动清洗入库 → 看日报/周报,日报可导 PNG。

## 文件说明
| 文件 | 作用 |
|---|---|
| `app.py` | Streamlit 看板主程序 |
| `cleaning.py` | 清洗(筛干线+支线、段级去重、时间转太平洋、区域映射、收发口径) |
| `db.py` | 连 Supabase、幂等入库、读数 |
| `dim_site.csv` | 站点→大区 映射(WE/NE/GL/MS/TX/FL) |
| `schema.sql` | Supabase 建表脚本 |
| `requirements.txt` / `packages.txt` | 依赖(packages 装中文字体,PNG 才显示中文) |
| `.streamlit/secrets.toml.example` | 数据库连接串模板 |

## 每天怎么用
1. 打开网址(闲置休眠的话等几十秒唤醒)。
2. 左侧上传 `taskArrivalTaskList`——**一个文件就够**(每行同时含发车与到车时间,自动算收发)。**建议每次导"实际发车时间=近14天"的滚动窗口**,这样"前几天发车、这两天才到"的记录也会被补全、不漏。可一次多选几个文件。点「处理并入库」(按 seg_key 幂等,重复上传自动更新不重复)。
3. 右侧选「范围(一级+二级/支线/全部)」「日报/周报」「日期」看板即时刷新。
4. 日报底部「导出日报 PNG」下载图片。

## 首次灌历史
用 `backfill.py`:填好 `URL`、把历史文件名列进 `FILES`、`CUTOFF=2026-07-29`,本地 `python backfill.py` 跑一次。

## 口径
- 发货 = 装车总票数,按**始发地** hub、**实际发车日**。
- 收货 = 卸车总票数,按**目的地** hub、**实际到车日**。
- 干线 = 一级+二级(H→H);支线单独;剔除提货。全部时间转**太平洋**。
- 对比 = 上周同一星期几。

## 常见问题
- **看板报"连不上数据库"**:检查 Secrets 里的连接串(是否 `+psycopg2`、密码对不对),以及是否跑过 `schema.sql`。
- **PNG 里中文变方块**:确认 `packages.txt` 里有 `fonts-noto-cjk` 且已重新部署。
- **新站点区域为空**:说明该站点不在 `dim_site.csv`,补一行(site_code,region,...)重新部署即可。
- **想要更好看的高管版**:可以让 Looker Studio 连同一个 Supabase 库再做一版,不影响这个。
