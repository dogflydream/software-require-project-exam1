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
