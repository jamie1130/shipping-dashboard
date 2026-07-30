-- 在 Supabase → SQL Editor 里跑一次,建收发货事实表
create table if not exists fact_shipment (
    seg_key        text primary key,       -- 任务编码|始发地|目的地(段级唯一)
    task_id        text,
    origin         text,
    dest           text,
    origin_region  text,
    dest_region    text,
    trunk_type     text,                    -- 一级干线/二级干线/支线
    vehicle_type   text,
    supplier       text,
    load_tickets   bigint,                  -- 装车总票数(发货)
    unload_tickets bigint,                  -- 卸车总票数(收货)
    depart_ts      timestamp,               -- 实际发车(太平洋)
    arrive_ts      timestamp,               -- 实际到车(太平洋)
    depart_date    date,                    -- 发货日
    arrive_date    date                     -- 收货日
);
create index if not exists idx_depart_date on fact_shipment(depart_date);
create index if not exists idx_arrive_date on fact_shipment(arrive_date);
