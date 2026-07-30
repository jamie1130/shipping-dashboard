# 干线收发货看板 · 搭建清单(Streamlit + Supabase)

一个网页:每天上传发货/收货两个文件 → 自动清洗入库 → 看日报/周报,日报可导 PNG。全程免费。

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

## 一次性搭建(约 20 分钟)

**第 1 步 · 建 Supabase 库**
1. 到 supabase.com 注册,New Project(选个区域、设个数据库密码,记住)。
2. 左侧 SQL Editor → 新建 query → 把 `schema.sql` 内容粘进去 → Run(建好 `fact_shipment` 表)。
3. Project Settings → Database → Connection string → 选 **URI**,复制那串;把开头 `postgresql://` 改成 `postgresql+psycopg2://`,并把 `[YOUR-PASSWORD]` 换成你的密码。

**第 2 步 · 放到 GitHub**
1. 建一个 GitHub 仓库(Private 也行),把本文件夹**所有文件**(含 `.streamlit/` 但**不要**上传 `secrets.toml`)推上去。
2. `secrets.toml.example` 只是模板,别把真密码提交到仓库。

**第 3 步 · 部署到 Streamlit Cloud**
1. 到 share.streamlit.io 用 GitHub 登录 → New app → 选你的仓库、分支、主文件 `app.py`。
2. Advanced settings → Secrets,粘贴:
   ```
   [db]
   url = "postgresql+psycopg2://postgres:你的密码@db.xxxx.supabase.co:5432/postgres"
   ```
3. Deploy。第一次装依赖要几分钟,好了会给你一个网址。

## 每天怎么用
1. 打开网址(闲置休眠的话等几十秒唤醒)。
2. 左侧上传**发货**、**收货**两个 `taskArrivalTaskList` → 点「处理并入库」(重复上传同一天不会重复,自动更新)。
3. 右侧选「范围(一级+二级/支线/全部)」「日报/周报」「日期」看板即时刷新。
4. 日报底部「导出日报 PNG」下载图片。

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
