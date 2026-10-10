"""绿循校园 认证与授权回归测试：验证越权（IDOR）已被修复。"""
import http.cookiejar
import json
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8011"
passed = failed = 0


def enc(path):
    if "?" not in path:
        return path
    base, qs = path.split("?", 1)
    return base + "?" + urllib.parse.quote(qs, safe="=&")


class Client:
    """带 Cookie 会话的 HTTP 客户端，模拟一个真实浏览器。"""
    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))

    def raw_status(self, method, path, body=None):
        """只返回 HTTP 状态码，不参与通过/失败统计（用于并发场景）。"""
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(BASE + enc(path), data=data, method=method)
        if data:
            req.add_header("Content-Type", "application/json")
        try:
            with self.opener.open(req, timeout=20) as r:
                return r.status
        except urllib.error.HTTPError as e:
            return e.code

    def call(self, method, path, body=None, expect=200, label=""):
        global passed, failed
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(BASE + enc(path), data=data, method=method)
        if data:
            req.add_header("Content-Type", "application/json")
        try:
            with self.opener.open(req, timeout=15) as r:
                code, payload = r.status, r.read().decode()
        except urllib.error.HTTPError as e:
            code, payload = e.code, e.read().decode()
        ok = code == expect
        passed, failed = passed + ok, failed + (not ok)
        tag = f" {label}" if label else ""
        print(f"[{'PASS' if ok else 'FAIL'}] {method:6} {path[:46]:46} -> {code} (期望 {expect}){tag}")
        if not ok:
            print(f"        {payload[:220]}")
        try:
            return json.loads(payload)
        except Exception:
            return payload


print("=" * 80)
print("一、登录 / 注册 / 会话")
anon = Client()
anon.call("GET", "/api/auth/me", expect=401, label="未登录访问本人信息")
anon.call("GET", "/api/items", expect=200, label="未登录可浏览市集")

stu = Client()
r = stu.call("POST", "/api/auth/login", {"login": "20230101", "password": "campus123"}, expect=200, label="学号登录")
me_id = r["id"]
stu.call("GET", "/api/auth/me", expect=200, label="登录后取本人信息")
stu.call("POST", "/api/auth/login", {"login": "20230101", "password": "wrong"}, expect=401, label="错误密码被拒")
stu.call("POST", "/api/auth/login", {"login": "不存在的用户", "password": "campus123"}, expect=401, label="不存在账号被拒")

reg = Client()
uniq = "T" + str(int(time.time()))[-6:]
reg.call("POST", "/api/auth/register", {"name": "回归测试生", "student_no": uniq, "college": "测试学院", "password": "test123456"}, expect=201, label="注册并自动登录")
reg.call("GET", "/api/auth/me", expect=200, label="注册后会话有效")
reg.call("POST", "/api/auth/register", {"name": "重复学号", "student_no": uniq, "college": "x", "password": "test123456"}, expect=400, label="学号重复被拒")
reg.call("POST", "/api/auth/register", {"name": "弱密码", "student_no": "W1", "college": "x", "password": "123"}, expect=422, label="密码过短被拒")

print("=" * 80)
print("二、越权回归：客户端伪造 user_id / 未登录访问受限资源")
# 关键：即使显式传入 user_id=1（管理员），也必须无法获得管理员数据
stu.call("GET", "/api/admin/summary?user_id=1", expect=403, label="学生伪造 user_id=1 访问后台")
stu.call("GET", "/api/admin/items?user_id=1", expect=403, label="学生伪造 user_id=1 读后台物品")
stu.call("GET", "/api/admin/users?user_id=1", expect=403, label="学生伪造 user_id=1 读用户表")
stu.call("POST", "/api/admin/items/1/offshelf", {"user_id": 1}, expect=403, label="学生伪造 user_id=1 下架物品")
stu.call("POST", "/api/admin/reports/1/resolve", {"user_id": 1}, expect=403, label="学生伪造 user_id=1 处理举报")
anon.call("GET", "/api/admin/summary", expect=401, label="未登录访问后台")
anon.call("GET", "/api/admin/summary?user_id=1", expect=401, label="未登录伪造 user_id=1")

# 读取他人私有数据：身份来自会话，传他人 id 不再生效
stu.call("GET", "/api/orders?user_id=3", expect=200, label="订单只返回本人(忽略传入 id)")
stu.call("GET", "/api/point-logs?user_id=3", expect=200, label="流水只返回本人(忽略传入 id)")
stu.call("GET", "/api/favorites?user_id=3", expect=200, label="收藏只返回本人(忽略传入 id)")
stu.call("GET", "/api/items/mine?user_id=3", expect=200, label="我的物品只返回本人")

print("=" * 80)
print("三、资源级授权：改他人物品 / 抢他人订单")
other_item = stu.call("POST", "/api/items", {"title": "越权回归-物主A", "category": "教材", "price": 5}, expect=201, label="学生发布物品")
iid = other_item["id"]
reg.call("PATCH", f"/api/items/{iid}", {"price": 1}, expect=403, label="他人修改我的物品")
reg.call("DELETE", f"/api/items/{iid}", expect=403, label="他人下架我的物品")
order = reg.call("POST", "/api/orders", {"item_id": iid}, expect=201, label="他人预约(reg=买家, stu=卖家)")
oid = order["id"]
# 第三方（管理员）既非买家也非卖家，必须被拒
adm_third = Client()
adm_third.call("POST", "/api/auth/login", {"login": "20230418", "password": "campus123"}, expect=200, label="第三方登录")
adm_third.call("POST", f"/api/orders/{oid}/cancel", {}, expect=403, label="非参与方取消订单")
adm_third.call("POST", f"/api/orders/{oid}/complete", {"pickup_code": order["pickup_code"]}, expect=403, label="非参与方完成订单")
adm_third.call("POST", f"/api/orders/{oid}/confirm", {}, expect=403, label="非卖家确认订单")
stu.call("POST", f"/api/orders/{oid}/cancel", {}, expect=200, label="物主(卖家)取消订单")
reg.call("POST", f"/api/orders/{oid}/cancel", {}, expect=400, label="重复取消被状态机拒绝")
reg.call("GET", "/api/orders", expect=200, label="买家查看本人订单")
# 举报：物主不能举报自己的物品；他人可以
stu.call("POST", "/api/reports", {"item_id": iid, "reason": "举报自己的物品测试"}, expect=400, label="不能举报自己的物品")
reg.call("POST", "/api/reports", {"item_id": iid, "reason": "描述与实物不符，申请核实"}, expect=201, label="他人可举报")

print("=" * 80)
print("四、资料与头像")
stu.call("PATCH", "/api/users/me", {"bio": "热爱循环利用", "contact": "wx: zhang"}, expect=200, label="更新本人资料")
stu.call("PATCH", "/api/users/me", {}, expect=400, label="空更新被拒")
tiny_png = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
stu.call("POST", "/api/users/me/avatar", {"image": tiny_png}, expect=200, label="上传头像")
stu.call("POST", "/api/users/me/avatar", {"image": "data:text/html;base64,PHNjcmlwdD4="}, expect=400, label="非图片类型被拒")
stu.call("POST", "/api/users/me/avatar", {"image": "not-a-data-url"}, expect=400, label="非法格式被拒")
prof = stu.call("GET", f"/api/users/{me_id}/profile", expect=200, label="公开主页")
has_contact = "contact" in json.dumps(prof)
print(f"        {'PASS' if not has_contact else 'FAIL'} 公开主页不含联系方式隐私")
passed, failed = passed + (not has_contact), failed + has_contact

print("=" * 80)
print("五、物品图片")
item_img = stu.call("POST", "/api/items", {"title": "带图物品", "category": "生活品", "price": 8, "image": tiny_png}, expect=201, label="发布带图物品")
print(f"        image={item_img.get('image')}")
stu.call("POST", "/api/items", {"title": "坏图", "category": "教材", "price": 1, "image": "data:image/svg+xml;base64,PHN2Zz4="}, expect=400, label="SVG 被拒(防 XSS)")

print("=" * 80)
print("六、管理员正常路径")
adm = Client()
adm.call("POST", "/api/auth/login", {"login": "管理员老师", "password": "campus123"}, expect=200, label="管理员登录")
adm.call("GET", "/api/admin/summary", expect=200, label="管理员读汇总")
adm.call("GET", "/api/admin/items", expect=200, label="管理员读物品")
adm.call("GET", "/api/admin/users", expect=200, label="管理员读用户")
adm.call("POST", "/api/admin/items/1/offshelf", {}, expect=200, label="管理员下架")
adm.call("POST", "/api/admin/items/1/restore", {}, expect=200, label="管理员恢复")

print("=" * 80)
print("七、退出登录后会话失效")
out = Client()
out.call("POST", "/api/auth/login", {"login": "20230205", "password": "campus123"}, expect=200, label="登录")
out.call("GET", "/api/auth/me", expect=200, label="会话有效")
out.call("POST", "/api/auth/logout", {}, expect=200, label="退出")
out.call("GET", "/api/auth/me", expect=401, label="退出后会话失效")

print("=" * 80)
print("八、会话令牌伪造 / 篡改")


def raw_get(path, cookie, expect):
    """绕过 CookieJar 直接指定原始 Cookie 头，验证服务端不信任客户端令牌。"""
    global passed, failed
    req = urllib.request.Request(BASE + path)
    req.add_header("Cookie", cookie)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            code = r.status
    except urllib.error.HTTPError as e:
        code = e.code
    good = code == expect
    passed, failed = passed + good, failed + (not good)
    print(f"[{'PASS' if good else 'FAIL'}] GET    {path:52} -> {code} (期望 {expect}) 令牌 {cookie[:34]}")


for tok in ["gc_session=forged-token-12345", "gc_session=", "gc_session=1", "gc_session=' OR '1'='1"]:
    raw_get("/api/auth/me", tok, 401)
raw_get("/api/admin/summary", "gc_session=forged-admin", 401)

print("=" * 80)
print("九、提权尝试：注册或改资料时夹带高权限字段")
esc = Client()
esc.call("POST", "/api/auth/register",
         {"name": "提权测试生", "student_no": "ESC" + str(int(time.time()))[-6:], "college": "测试学院",
          "password": "test123456", "role": "admin", "points": 999999}, expect=201, label="注册夹带 role/points")
esc_me = esc.call("GET", "/api/auth/me", expect=200, label="读取注册结果")
role_ok = esc_me.get("role") == "student"
pts_ok = esc_me.get("points") == 0
print(f"        {'PASS' if role_ok else 'FAIL'} 注册后 role 仍为 student（实际 {esc_me.get('role')}）")
print(f"        {'PASS' if pts_ok else 'FAIL'} 注册后 points 仍为 0（实际 {esc_me.get('points')}）")
passed, failed = passed + role_ok + pts_ok, failed + (not role_ok) + (not pts_ok)

esc.call("PATCH", "/api/users/me", {"role": "admin", "points": 999999}, expect=400, label="改资料夹带 role/points 被拒")
esc_me2 = esc.call("GET", "/api/auth/me", expect=200, label="读取改资料结果")
role_ok2 = esc_me2.get("role") == "student"
pts_ok2 = esc_me2.get("points") == 0
print(f"        {'PASS' if role_ok2 else 'FAIL'} 改资料后 role 仍为 student（实际 {esc_me2.get('role')}）")
print(f"        {'PASS' if pts_ok2 else 'FAIL'} 改资料后 points 仍为 0（实际 {esc_me2.get('points')}）")
passed, failed = passed + role_ok2 + pts_ok2, failed + (not role_ok2) + (not pts_ok2)
esc.call("GET", "/api/admin/summary", expect=403, label="提权后仍无法访问后台")

print("=" * 80)
print("十、SQL 注入（参数化占位符防护）")
inj = Client()
inj.call("POST", "/api/auth/login", {"login": "' OR '1'='1' --", "password": "x"}, expect=401, label="登录名注入")
inj.call("POST", "/api/auth/login", {"login": "20230101", "password": "' OR '1'='1"}, expect=401, label="密码注入")
rows = inj.call("GET", "/api/items?keyword=" + urllib.parse.quote("' OR 1=1 --"), expect=200, label="搜索关键词注入")
empty_ok = isinstance(rows, list) and len(rows) == 0
print(f"        {'PASS' if empty_ok else 'FAIL'} 注入关键词未返回全部数据（返回 {len(rows) if isinstance(rows, list) else rows} 条）")
passed, failed = passed + empty_ok, failed + (not empty_ok)
inj.call("GET", "/api/items?category=" + urllib.parse.quote("' OR '1'='1"), expect=422, label="分类注入被枚举校验拒绝")

print("=" * 80)
print("十一、分类管理（管理员维护，含兜底分类「其它」）")
cat = Client()
cat.call("POST", "/api/auth/login", {"login": "A000000", "password": "campus123"}, expect=200, label="管理员登录")
stu2 = Client()
stu2.call("POST", "/api/auth/login", {"login": "20230101", "password": "campus123"}, expect=200, label="学生登录")

cats = cat.call("GET", "/api/categories", expect=200, label="分类列表")
names = [c["name"] for c in cats]
has_other = "其它" in names
print(f"        {'PASS' if has_other else 'FAIL'} 分类含兜底分类「其它」（实际 {names}）")
passed, failed = passed + has_other, failed + (not has_other)
other = next((c for c in cats if c["name"] == "其它"), None)
prot_ok = bool(other and other.get("protected"))
print(f"        {'PASS' if prot_ok else 'FAIL'} 「其它」标记为受保护分类")
passed, failed = passed + prot_ok, failed + (not prot_ok)

created = cat.call("POST", "/api/admin/categories",
                   {"name": "数码", "icon": "box", "carbon_factor": 4.0, "sort_order": 40},
                   expect=201, label="新增分类")
cat.call("POST", "/api/admin/categories", {"name": "数码"}, expect=400, label="重名分类被拒")
cat.call("DELETE", f"/api/admin/categories/{other['id']}", expect=400, label="删除兜底分类被拒")
cat.call("PATCH", f"/api/admin/categories/{created['id']}", {"name": "数码产品"}, expect=200, label="重命名分类")
stu2.call("POST", "/api/admin/categories", {"name": "越权"}, expect=403, label="学生不能建分类")
stu2.call("DELETE", f"/api/admin/categories/{created['id']}", expect=403, label="学生不能删分类")
cat.call("POST", "/api/admin/categories", {"name": ""}, expect=422, label="空分类名被拒")

print("=" * 80)
print("十二、物品引用动态分类 + 编辑后重新审核")
item = stu2.call("POST", "/api/items", {"title": "数码测试物品", "category": "数码产品", "price": 10},
                 expect=201, label="用新分类发布")
stu2.call("POST", "/api/items", {"title": "其它测试", "category": "其它", "price": 5},
          expect=201, label="用「其它」发布")
stu2.call("POST", "/api/items", {"title": "非法分类", "category": "不存在的分类", "price": 5},
          expect=422, label="不存在的分类被拒")

iid = item["id"]
stu2.call("PATCH", f"/api/items/{iid}", {"price": 99}, expect=200, label="物主编辑物品")
after = stu2.call("GET", f"/api/items/{iid}", expect=200, label="物主可查看自己的待审物品")
pend_ok = after.get("review_status") == "pending"
print(f"        {'PASS' if pend_ok else 'FAIL'} 编辑后状态变为 pending（实际 {after.get('review_status')}）")
passed, failed = passed + pend_ok, failed + (not pend_ok)

market = cat.call("GET", "/api/items?keyword=数码测试", expect=200, label="市集搜索")
hidden_ok = len(market) == 0
print(f"        {'PASS' if hidden_ok else 'FAIL'} 待审物品不出现在市集（返回 {len(market)} 条）")
passed, failed = passed + hidden_ok, failed + (not hidden_ok)
anon2 = Client()
anon2.call("GET", f"/api/items/{iid}", expect=404, label="匿名无法查看待审物品")

pend_list = cat.call("GET", "/api/admin/items?review_status=pending", expect=200, label="后台待审列表")
cat.call("POST", f"/api/admin/items/{iid}/review", {"approve": False}, expect=400, label="驳回未填理由被拒")
rej = cat.call("POST", f"/api/admin/items/{iid}/review", {"approve": False, "note": "价格异常，请核对"},
               expect=200, label="驳回物品")
note_ok = rej.get("review_note") == "价格异常，请核对"
print(f"        {'PASS' if note_ok else 'FAIL'} 驳回理由已记录")
passed, failed = passed + note_ok, failed + (not note_ok)
still_hidden = cat.call("GET", "/api/items?keyword=数码测试", expect=200, label="驳回后市集仍不可见")
sh_ok = len(still_hidden) == 0
print(f"        {'PASS' if sh_ok else 'FAIL'} 驳回后市集不可见（返回 {len(still_hidden)} 条）")
passed, failed = passed + sh_ok, failed + (not sh_ok)

cat.call("POST", f"/api/admin/items/{iid}/review", {"approve": True}, expect=200, label="审核通过")
visible = cat.call("GET", "/api/items?keyword=数码测试", expect=200, label="通过后市集可见")
vis_ok = len(visible) == 1
print(f"        {'PASS' if vis_ok else 'FAIL'} 通过后市集可见（返回 {len(visible)} 条）")
passed, failed = passed + vis_ok, failed + (not vis_ok)
cat.call("POST", f"/api/admin/items/{iid}/review", {"approve": True}, expect=400, label="重复通过被拒")
stu2.call("POST", f"/api/admin/items/{iid}/review", {"approve": True}, expect=403, label="学生不能审核")

# 清理：删除测试分类前需先清空引用
cat.call("DELETE", f"/api/admin/categories/{created['id']}", expect=400, label="仍有物品引用时不可删分类")

print("=" * 80)
print("十三、并发预约竞态（防超卖）")
import threading


def login_client(login_name):
    c = Client()
    c.call("POST", "/api/auth/login", {"login": login_name, "password": "campus123"}, expect=200)
    return c


race_owner = login_client("20230101")
race_buyers = [login_client(x) for x in ("20230205", "20230312", "20230418")]
race_bad = 0
ROUNDS = 5
for rnd in range(ROUNDS):
    it = race_owner.call("POST", "/api/items",
                         {"title": f"并发用例{rnd}", "category": "教材", "price": 1}, expect=201)
    iid = it["id"]
    codes = []
    barrier = threading.Barrier(len(race_buyers))

    def attempt(c, item_id):
        barrier.wait()  # 尽量同时发起，制造真实竞争
        codes.append(c.raw_status("POST", "/api/orders", {"item_id": item_id}))

    threads = [threading.Thread(target=attempt, args=(c, iid)) for c in race_buyers]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    if codes.count(201) != 1:
        race_bad += 1

race_ok = race_bad == 0
print(f"        {'PASS' if race_ok else 'FAIL'} {ROUNDS} 轮并发预约均只有 1 人成功（异常 {race_bad} 轮）")
passed, failed = passed + race_ok, failed + (not race_ok)

print("=" * 80)
print("十四、审核状态拦截交易入口")
pend_owner = login_client("20230101")
pend_buyer = login_client("20230205")
pit = pend_owner.call("POST", "/api/items",
                      {"title": "待审拦截用例", "category": "教材", "price": 1}, expect=201)
pend_owner.call("PATCH", f"/api/items/{pit['id']}", {"price": 2}, expect=200, label="编辑转待审")
pend_buyer.call("POST", "/api/orders", {"item_id": pit["id"]}, expect=400, label="预约待审物品被拒")
pend_buyer.call("POST", "/api/favorites", {"item_id": pit["id"]}, expect=400, label="收藏待审物品被拒")

print("=" * 80)
print("十五、联系方式仅对交易对方可见")
ct_owner = login_client("20230101")
ct_buyer = login_client("20230205")
ct_owner.call("PATCH", "/api/users/me", {"contact": "wx: test_owner"}, expect=200, label="物主填写联系方式")
ct_item = ct_owner.call("POST", "/api/items",
                        {"title": "联系方式用例", "category": "教材", "price": 1}, expect=201)
ct_order = ct_buyer.call("POST", "/api/orders", {"item_id": ct_item["id"]}, expect=201, label="买家预约")
buyer_contact = ct_order.get("counterparty_contact")
print(f"        {'PASS' if buyer_contact == 'wx: test_owner' else 'FAIL'} 买家可见卖家联系方式（{buyer_contact}）")
passed, failed = passed + (buyer_contact == "wx: test_owner"), failed + (buyer_contact != "wx: test_owner")

ct_third = login_client("20230418")
third_orders = ct_third.call("GET", "/api/orders", expect=200, label="第三方订单列表")
leak = any(o["id"] == ct_order["id"] for o in third_orders)
print(f"        {'PASS' if not leak else 'FAIL'} 非参与方看不到该订单")
passed, failed = passed + (not leak), failed + leak

print("=" * 80)
print("十六、登录失败限流")
throttle = Client()
codes_seq = [throttle.raw_status("POST", "/api/auth/login",
                                 {"login": "20230312", "password": "definitely-wrong"}) for _ in range(6)]
locked = codes_seq[-1] == 429 and codes_seq[:5] == [401] * 5
print(f"        {'PASS' if locked else 'FAIL'} 连续失败后被限流（序列 {codes_seq}）")
passed, failed = passed + locked, failed + (not locked)
throttle.call("POST", "/api/auth/login", {"login": "20230312", "password": "campus123"}, expect=429,
              label="锁定期间正确密码也被拒")

print("=" * 80)
print("十七、管理员重置密码（含解除锁定）")
rp_admin = login_client("A000000")
rp_users = rp_admin.call("GET", "/api/admin/users", expect=200, label="管理员读用户")
rp_uid = next(u["id"] for u in rp_users if u.get("student_no") == "20230312")
rp_admin.call("POST", f"/api/admin/users/{rp_uid}/password", {"new_password": "reset12345"},
              expect=200, label="重置密码")
rp_client = Client()
rp_client.call("POST", "/api/auth/login", {"login": "20230312", "password": "reset12345"},
               expect=200, label="用新密码登录成功（锁定已解除）")
rp_client.call("POST", "/api/auth/login", {"login": "20230312", "password": "campus123"},
               expect=401, label="旧密码已失效")
stu_reset = login_client("20230205")
stu_reset.call("POST", f"/api/admin/users/{rp_uid}/password", {"new_password": "hack12345"},
               expect=403, label="学生不能重置他人密码")

print("=" * 80)
print("十八、我的举报与统计口径")
rep_client = login_client("20230205")
rep_item = rep_client.call("POST", "/api/items",
                           {"title": "举报进度用例", "category": "教材", "price": 1}, expect=201)
other = login_client("20230418")
other.call("POST", "/api/reports", {"item_id": rep_item["id"], "reason": "举报进度测试理由"},
           expect=201, label="提交举报")
mine_reports = other.call("GET", "/api/reports/mine", expect=200, label="我的举报")
has_rep = any(r["item_id"] == rep_item["id"] for r in mine_reports)
print(f"        {'PASS' if has_rep else 'FAIL'} 可查看自己举报的处理进度")
passed, failed = passed + has_rep, failed + (not has_rep)

summ = Client().call("GET", "/api/stats/summary", expect=200, label="统计汇总")
has_pending = "pending_items" in summ
print(f"        {'PASS' if has_pending else 'FAIL'} 汇总区分待审物品（pending_items={summ.get('pending_items')}）")
passed, failed = passed + has_pending, failed + (not has_pending)

print("=" * 80)
print(f"结果：通过 {passed}，失败 {failed}")
