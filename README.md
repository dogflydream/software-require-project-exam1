# 绿循校园 —— 校园闲置教材与物品循环流转系统

软件工程实验项目：基于 **增量模型** 开发的校园闲置物品循环流转平台。

技术栈：Python 3.12 + FastAPI + SQLite + Vue 3 (CDN) + Tailwind CSS (CDN)

## 快速启动

```bash
# 安装依赖（首次）
uv sync

# 启动开发服务器
uv run uvicorn main:app --reload

# 浏览器访问
http://127.0.0.1:8000
```

首次启动会自动创建 `campus.db` 并注入种子数据（5 个用户、13+ 件物品、礼品、订单、举报各若干）。

- 管理员账号：管理员老师（选择该身份可进入「后台管理」）
- 普通学生：张绿循、李循环、王低碳、赵再利用

## 功能模块（按增量交付）

| 增量 | Tag | 功能 |
|------|-----|------|
| 0 | v0.0.1-init | 脚手架：uv + FastAPI + SQLite + 单页前端 |
| 1 | v0.1.0-inc1 | 市集：物品浏览、分类筛选（教材/考研/生活品）、关键词搜索、发布闲置 |
| 2 | v0.2.0-inc2 | 碳积分：发布闲置 +10 分、积分流水、积分商城礼品兑换 |
| 3 | v0.3.0-inc3 | 循环度与减碳量估算、环保先锋榜、学院减碳排行大屏 |
| 4 | v0.4.0-inc4 | 订单：预约意向 → 卖家确认 → 线下验货自提（自提码）→ 完成流转（循环度 +1、卖家 +20 分）；状态机扭转校验 |
| 5 | v1.0.0-release | 后台：物品下架/恢复、违规举报与审核、平台全局汇总卡片 |

## 版本回滚演示

每个增量提交后均为可运行状态，可随时切换：

```bash
git tag                    # 查看全部版本
git checkout v0.2.0-inc2   # 回滚到增量 2 演示
git checkout main          # 回到最新版本
```

## 核心 API 一览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/items?category=&keyword= | 物品列表/筛选/搜索 |
| POST | /api/items | 发布闲置（+10 碳积分） |
| GET | /api/point-logs?user_id= | 积分流水 |
| GET | /api/products · POST /api/redeem | 礼品列表 / 积分兑换 |
| GET | /api/stats/summary · /api/rank/users · /api/rank/colleges | 统计与排行 |
| POST | /api/orders | 买家发起预约意向 |
| POST | /api/orders/{id}/confirm · /complete · /cancel | 订单状态扭转（自提码校验） |
| POST | /api/reports | 举报违规物品 |
| GET | /api/admin/summary · /api/admin/items · /api/admin/reports | 后台数据（仅管理员） |
| POST | /api/admin/items/{id}/offshelf · /restore · /api/admin/reports/{id}/resolve | 后台操作（仅管理员） |

接口文档（Swagger）：启动后访问 http://127.0.0.1:8000/docs
