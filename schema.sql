-- 绿循校园 数据库结构（增量 2：碳积分流水与兑换礼品）
CREATE TABLE IF NOT EXISTS point_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    delta INTEGER NOT NULL,                        -- 正为获得，负为消耗
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    cost_points INTEGER NOT NULL,
    stock INTEGER NOT NULL DEFAULT 0,
    emoji TEXT NOT NULL DEFAULT '🎁'
);

-- 种子数据：积分商城礼品
INSERT INTO products (name, description, cost_points, stock, emoji) SELECT '定制帆布袋', '环保帆布材质，绿循校园纪念款', 100, 20, '🛍️' WHERE NOT EXISTS (SELECT 1 FROM products WHERE name='定制帆布袋');
INSERT INTO products (name, description, cost_points, stock, emoji) SELECT '食堂 5 元代金券', '全校食堂通用，当月有效', 60, 50, '🎫' WHERE NOT EXISTS (SELECT 1 FROM products WHERE name='食堂 5 元代金券');
INSERT INTO products (name, description, cost_points, stock, emoji) SELECT '植物盲盒（多肉）', '随机品种，含花盆与营养土', 150, 15, '🪴' WHERE NOT EXISTS (SELECT 1 FROM products WHERE name='植物盲盒（多肉）');
INSERT INTO products (name, description, cost_points, stock, emoji) SELECT '校园文创笔记本', '再生纸材质，碳足迹标识', 120, 30, '📒' WHERE NOT EXISTS (SELECT 1 FROM products WHERE name='校园文创笔记本');
INSERT INTO products (name, description, cost_points, stock, emoji) SELECT '咖啡免费券', '校园咖啡店任意一杯', 200, 10, '☕' WHERE NOT EXISTS (SELECT 1 FROM products WHERE name='咖啡免费券');

-- 绿循校园 数据库结构（增量 1：用户与物品）
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    student_no TEXT UNIQUE,
    college TEXT NOT NULL DEFAULT '未填写学院',
    role TEXT NOT NULL DEFAULT 'student',          -- student / admin
    points INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id INTEGER NOT NULL REFERENCES users(id),
    title TEXT NOT NULL,
    category TEXT NOT NULL,                        -- 教材 / 考研 / 生活品
    description TEXT NOT NULL DEFAULT '',
    price REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'available',      -- available / reserved / completed / offshelf
    cycle_count INTEGER NOT NULL DEFAULT 0,        -- 循环度：流转次数
    carbon_saved REAL NOT NULL DEFAULT 0,          -- 累计减碳量（kg）
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- 种子数据：用户（含 1 名管理员）
INSERT INTO users (name, student_no, college, role, points) SELECT '管理员老师', 'A000000', '信息学院', 'admin', 0 WHERE NOT EXISTS (SELECT 1 FROM users WHERE role='admin');
INSERT INTO users (name, student_no, college, role, points) SELECT '张绿循', '20230101', '计算机学院', 'student', 120 WHERE NOT EXISTS (SELECT 1 FROM users WHERE student_no='20230101');
INSERT INTO users (name, student_no, college, role, points) SELECT '李循环', '20230205', '环境学院', 'student', 80 WHERE NOT EXISTS (SELECT 1 FROM users WHERE student_no='20230205');
INSERT INTO users (name, student_no, college, role, points) SELECT '王低碳', '20230312', '经济管理学院', 'student', 60 WHERE NOT EXISTS (SELECT 1 FROM users WHERE student_no='20230312');
INSERT INTO users (name, student_no, college, role, points) SELECT '赵再利用', '20230418', '外国语学院', 'student', 30 WHERE NOT EXISTS (SELECT 1 FROM users WHERE student_no='20230418');

-- 种子数据：闲置物品
INSERT INTO items (owner_id, title, category, description, price) SELECT 2, '《数据结构（C语言版）》严蔚敏', '教材', '九成新，少量笔记，考研上岸学长整理', 15.0 WHERE NOT EXISTS (SELECT 1 FROM items WHERE title='《数据结构（C语言版）》严蔚敏');
INSERT INTO items (owner_id, title, category, description, price) SELECT 2, '《高等数学》同济第七版上下册', '教材', '上下册一套，无划线', 22.0 WHERE NOT EXISTS (SELECT 1 FROM items WHERE title='《高等数学》同济第七版上下册');
INSERT INTO items (owner_id, title, category, description, price) SELECT 3, '2025考研英语一真题黄皮书', '考研', '真题+解析全套，附赠答题卡', 18.0 WHERE NOT EXISTS (SELECT 1 FROM items WHERE title='2025考研英语一真题黄皮书');
INSERT INTO items (owner_id, title, category, description, price) SELECT 3, '肖秀荣政治精讲精练+1000题', '考研', '1000题未拆封，精讲精练有笔记', 25.0 WHERE NOT EXISTS (SELECT 1 FROM items WHERE title='肖秀荣政治精讲精练+1000题');
INSERT INTO items (owner_id, title, category, description, price) SELECT 4, '小米台灯 Pro', '生活品', '宿舍神器，亮度可调，功能完好', 39.9 WHERE NOT EXISTS (SELECT 1 FROM items WHERE title='小米台灯 Pro');
INSERT INTO items (owner_id, title, category, description, price) SELECT 4, '置物收纳架（三层）', '生活品', '毕业急出，宿舍楼下自提', 20.0 WHERE NOT EXISTS (SELECT 1 FROM items WHERE title='置物收纳架（三层）');
INSERT INTO items (owner_id, title, category, description, price) SELECT 5, '英语四级词汇书 闪过', '教材', '背完了已过级，助力下一届', 8.0 WHERE NOT EXISTS (SELECT 1 FROM items WHERE title='英语四级词汇书 闪过');
INSERT INTO items (owner_id, title, category, description, price) SELECT 5, '自行车（捷安特 ATX）', '生活品', '骑了一年，车况良好，附车锁', 260.0 WHERE NOT EXISTS (SELECT 1 FROM items WHERE title='自行车（捷安特 ATX）');

-- 种子数据：已完成流转的历史物品（用于排行榜与统计演示）
INSERT INTO items (owner_id, title, category, description, price, status, cycle_count, carbon_saved) SELECT 2, '《线性代数》第六版', '教材', '已完成3次流转的明星教材', 12.0, 'completed', 3, 7.5 WHERE NOT EXISTS (SELECT 1 FROM items WHERE title='《线性代数》第六版');
INSERT INTO items (owner_id, title, category, description, price, status, cycle_count, carbon_saved) SELECT 3, '《考研数学复习全书》', '考研', '已完成2次流转', 20.0, 'completed', 2, 4.0 WHERE NOT EXISTS (SELECT 1 FROM items WHERE title='《考研数学复习全书》');
INSERT INTO items (owner_id, title, category, description, price, status, cycle_count, carbon_saved) SELECT 4, '旧自行车（已循环）', '生活品', '已完成1次流转', 150.0, 'completed', 1, 3.5 WHERE NOT EXISTS (SELECT 1 FROM items WHERE title='旧自行车（已循环）');
INSERT INTO items (owner_id, title, category, description, price, status, cycle_count, carbon_saved) SELECT 5, '《新概念英语》全套', '教材', '已完成2次流转', 30.0, 'completed', 2, 5.0 WHERE NOT EXISTS (SELECT 1 FROM items WHERE title='《新概念英语》全套');
INSERT INTO items (owner_id, title, category, description, price, status, cycle_count, carbon_saved) SELECT 2, '宿舍小冰箱', '生活品', '已完成1次流转', 199.0, 'completed', 1, 3.5 WHERE NOT EXISTS (SELECT 1 FROM items WHERE title='宿舍小冰箱');

-- 绿循校园 数据库结构（增量 4：订单与线下自提履约）
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL REFERENCES items(id),
    buyer_id INTEGER NOT NULL REFERENCES users(id),
    seller_id INTEGER NOT NULL REFERENCES users(id),
    status TEXT NOT NULL DEFAULT 'reserved',       -- reserved / confirmed / completed / cancelled
    pickup_code TEXT NOT NULL,                     -- 线下自提码
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- 种子数据：一条已确认待自提的订单（演示履约流程）
INSERT INTO orders (item_id, buyer_id, seller_id, status, pickup_code) SELECT 1, 4, 2, 'confirmed', 'GC-' || upper(hex(randomblob(3))) WHERE NOT EXISTS (SELECT 1 FROM orders);
UPDATE items SET status = 'reserved' WHERE status = 'available' AND id IN (SELECT item_id FROM orders WHERE status IN ('reserved', 'confirmed'));

-- 绿循校园 数据库结构（增量 5：违规举报与后台审核）
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL REFERENCES items(id),
    reporter_id INTEGER NOT NULL REFERENCES users(id),
    reason TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',           -- open / resolved
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- 种子数据：一条待处理举报
INSERT INTO reports (item_id, reporter_id, reason) SELECT 6, 5, '物品描述与实物不符，疑似损坏' WHERE NOT EXISTS (SELECT 1 FROM reports);

-- 绿循校园 数据库结构（增量 6：收藏关注）
CREATE TABLE IF NOT EXISTS favorites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    item_id INTEGER NOT NULL REFERENCES items(id),
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (user_id, item_id)
);

-- 查询性能索引：市集筛选、订单归属、流水与举报待办
CREATE INDEX IF NOT EXISTS idx_items_status_created ON items(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_items_category ON items(category);
CREATE INDEX IF NOT EXISTS idx_items_owner ON items(owner_id);
CREATE INDEX IF NOT EXISTS idx_orders_buyer ON orders(buyer_id, id DESC);
CREATE INDEX IF NOT EXISTS idx_orders_seller ON orders(seller_id, id DESC);
CREATE INDEX IF NOT EXISTS idx_orders_item ON orders(item_id);
CREATE INDEX IF NOT EXISTS idx_point_logs_user ON point_logs(user_id, id DESC);
CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status, id DESC);
CREATE INDEX IF NOT EXISTS idx_favorites_user ON favorites(user_id, id DESC);

-- 绿循校园 种子数据（增量 6 补全）：碳积分流水账本
-- 依据 BR2-2「每笔积分变动必须写入 point_logs」补齐可审计流水；
-- 每个用户的流水 delta 合计与其 users.points 严格一致，不改变任何既有积分余额与统计值。
-- 守卫按「该用户尚无流水」判断，整批插入，保证重复启动幂等。

-- 张绿循 120 = 发布 4 件×10 + 完成流转 4 次×20
INSERT INTO point_logs (user_id, delta, reason, created_at)
SELECT u.id, v.delta, v.reason, datetime('now','localtime', v.off)
FROM users u JOIN (
    SELECT 10 AS delta, '发布闲置《《数据结构（C语言版）》严蔚敏》获得碳积分' AS reason, '-13 days' AS off
    UNION ALL SELECT 10, '发布闲置《《高等数学》同济第七版上下册》获得碳积分', '-12 days'
    UNION ALL SELECT 10, '发布闲置《《线性代数》第六版》获得碳积分', '-11 days'
    UNION ALL SELECT 10, '发布闲置《宿舍小冰箱》获得碳积分', '-10 days'
    UNION ALL SELECT 20, '完成流转《《线性代数》第六版》获得碳积分', '-9 days'
    UNION ALL SELECT 20, '完成流转《《线性代数》第六版》获得碳积分', '-6 days'
    UNION ALL SELECT 20, '完成流转《《线性代数》第六版》获得碳积分', '-4 days'
    UNION ALL SELECT 20, '完成流转《宿舍小冰箱》获得碳积分', '-2 days'
) v WHERE u.student_no='20230101'
  AND NOT EXISTS (SELECT 1 FROM point_logs pl WHERE pl.user_id = u.id);

-- 李循环 80 = 发布 3 件×10 + 完成流转 2 次×20 + 平台上线活跃奖励 10
INSERT INTO point_logs (user_id, delta, reason, created_at)
SELECT u.id, v.delta, v.reason, datetime('now','localtime', v.off)
FROM users u JOIN (
    SELECT 10 AS delta, '发布闲置《2025考研英语一真题黄皮书》获得碳积分' AS reason, '-13 days' AS off
    UNION ALL SELECT 10, '发布闲置《肖秀荣政治精讲精练+1000题》获得碳积分', '-12 days'
    UNION ALL SELECT 10, '发布闲置《《考研数学复习全书》》获得碳积分', '-11 days'
    UNION ALL SELECT 20, '完成流转《《考研数学复习全书》》获得碳积分', '-7 days'
    UNION ALL SELECT 20, '完成流转《《考研数学复习全书》》获得碳积分', '-3 days'
    UNION ALL SELECT 10, '平台上线活跃奖励', '-14 days'
) v WHERE u.student_no='20230205'
  AND NOT EXISTS (SELECT 1 FROM point_logs pl WHERE pl.user_id = u.id);

-- 王低碳 60 = 发布 3 件×10 + 完成流转 1 次×20 + 平台上线活跃奖励 10
INSERT INTO point_logs (user_id, delta, reason, created_at)
SELECT u.id, v.delta, v.reason, datetime('now','localtime', v.off)
FROM users u JOIN (
    SELECT 10 AS delta, '发布闲置《置物收纳架（三层）》获得碳积分' AS reason, '-13 days' AS off
    UNION ALL SELECT 10, '发布闲置《小米台灯 Pro》获得碳积分', '-12 days'
    UNION ALL SELECT 10, '发布闲置《旧自行车（已循环）》获得碳积分', '-8 days'
    UNION ALL SELECT 20, '完成流转《旧自行车（已循环）》获得碳积分', '-5 days'
    UNION ALL SELECT 10, '平台上线活跃奖励', '-14 days'
) v WHERE u.student_no='20230312'
  AND NOT EXISTS (SELECT 1 FROM point_logs pl WHERE pl.user_id = u.id);

-- 赵再利用 30 = 发布 3 件×10 + 完成流转 2 次×20 - 兑换礼品 40
INSERT INTO point_logs (user_id, delta, reason, created_at)
SELECT u.id, v.delta, v.reason, datetime('now','localtime', v.off)
FROM users u JOIN (
    SELECT 10 AS delta, '发布闲置《英语四级词汇书 闪过》获得碳积分' AS reason, '-12 days' AS off
    UNION ALL SELECT 10, '发布闲置《自行车（捷安特 ATX）》获得碳积分', '-11 days'
    UNION ALL SELECT 10, '发布闲置《《新概念英语》全套》获得碳积分', '-10 days'
    UNION ALL SELECT 20, '完成流转《《新概念英语》全套》获得碳积分', '-6 days'
    UNION ALL SELECT 20, '完成流转《《新概念英语》全套》获得碳积分', '-3 days'
    UNION ALL SELECT -40, '兑换礼品「食堂 5 元代金券」', '-1 days'
) v WHERE u.student_no='20230418'
  AND NOT EXISTS (SELECT 1 FROM point_logs pl WHERE pl.user_id = u.id);

-- 绿循校园 数据库结构（增量 6：会话认证与资料）
CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    expires_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);

-- 绿循校园 数据库结构（增量 7：用户资料与物品图片）
-- 说明：SQLite 不支持 ADD COLUMN IF NOT EXISTS，故用 ALTER 失败忽略的方式幂等补列。

-- 绿循校园 数据库结构（增量 8：可管理的物品分类）
-- 分类由管理员维护，物品通过 category 名称引用；「其它」为受保护兜底分类，不可删除。
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    icon TEXT NOT NULL DEFAULT 'box',
    carbon_factor REAL NOT NULL DEFAULT 2.0,   -- 该类别单次流转的减碳估算系数（kg CO₂e）
    sort_order INTEGER NOT NULL DEFAULT 0,
    protected INTEGER NOT NULL DEFAULT 0,      -- 1 = 系统兜底分类，禁止删除
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

INSERT INTO categories (name, icon, carbon_factor, sort_order, protected)
SELECT '教材', 'book', 2.5, 10, 0 WHERE NOT EXISTS (SELECT 1 FROM categories);
INSERT INTO categories (name, icon, carbon_factor, sort_order, protected)
SELECT '考研', 'pencil', 2.0, 20, 0 WHERE NOT EXISTS (SELECT 1 FROM categories WHERE name='考研');
INSERT INTO categories (name, icon, carbon_factor, sort_order, protected)
SELECT '生活品', 'sofa', 3.5, 30, 0 WHERE NOT EXISTS (SELECT 1 FROM categories WHERE name='生活品');
INSERT INTO categories (name, icon, carbon_factor, sort_order, protected)
SELECT '其它', 'box', 2.0, 99, 1 WHERE NOT EXISTS (SELECT 1 FROM categories WHERE name='其它');

-- 绿循校园 数据库结构（增量 12：登录失败限流）
-- 记录登录失败次数，用于防暴力破解；成功登录或锁定到期后清零。
CREATE TABLE IF NOT EXISTS login_attempts (
    identifier TEXT PRIMARY KEY,                   -- 登录名（学号/姓名）
    fail_count INTEGER NOT NULL DEFAULT 0,
    locked_until TEXT,                             -- 锁定截止时间，为空表示未锁定
    last_fail_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);


-- Persistent gift redemption receipts. Keep snapshots after a product is deleted.
CREATE TABLE IF NOT EXISTS redemptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
    product_name TEXT NOT NULL,
    cost_points INTEGER NOT NULL CHECK (cost_points > 0),
    pickup_code TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_redemptions_user ON redemptions(user_id, id DESC);


-- Versioned data-policy migrations; pickup credentials rotate only on policy adoption.
CREATE TABLE IF NOT EXISTS app_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);


-- First-party order conversations. No external contact information is required.
CREATE TABLE IF NOT EXISTS order_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    sender_id INTEGER NOT NULL REFERENCES users(id),
    content TEXT NOT NULL CHECK(length(content) BETWEEN 1 AND 1000),
    client_nonce TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE(order_id, sender_id, client_nonce)
);
CREATE INDEX IF NOT EXISTS idx_order_messages_order ON order_messages(order_id, id);
CREATE INDEX IF NOT EXISTS idx_order_messages_sender ON order_messages(sender_id, created_at);
CREATE TABLE IF NOT EXISTS order_message_reads (
    order_id INTEGER NOT NULL REFERENCES orders(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    last_message_id INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY(order_id, user_id)
);
