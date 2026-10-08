# -*- coding: utf-8 -*-
"""以《软件需求工程》实验指导书 docx 为模板，生成 5 份实验报告。

每个报告 = 指导书中该实验的原文（目的要求/实验内容，含表1~表9）
         + 报告头（课程/实验名称/学生信息占位表）
         + 填写完成的"实验报告"节（绿循校园项目成果 + UML 图）。
"""
import copy
from pathlib import Path

import docx
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt

BASE = Path(__file__).parent
TEMPLATE = BASE.parent.parent / "《软件需求工程》实验指导书.docx"
ASSETS = BASE / "assets"

EXPERIMENTS = {
    1: {"title": "AI 辅助的软件功能描述", "keep": (1, 42), "drop": [43]},
    2: {"title": "AI 辅助的用例图绘制", "keep": (44, 73), "drop": [74, 75, 76, 77]},
    3: {"title": "AI 辅助的类图设计", "keep": (78, 121), "drop": [122]},
    4: {"title": "AI 辅助的顺序图绘制", "keep": (123, 144), "drop": [145, 146]},
    5: {"title": "AI 辅助的活动图绘制", "keep": (147, 172), "drop": [173]},
}


# ---------- 通用构件 ----------

def set_run_font(run, size=12, bold=False, east="宋体", ascii_f="Times New Roman"):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.name = ascii_f
    rpr = run._element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.append(rf)
    rf.set(qn("w:eastAsia"), east)


def body_para(doc, text, indent=True, size=12):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf = p.paragraph_format
    if indent:
        pf.first_line_indent = Pt(size * 2)
    pf.line_spacing = 1.15
    pf.space_after = Pt(3)
    run = p.add_run(text)
    set_run_font(run, size=size)
    return p


def h3(doc, text):
    p = doc.add_paragraph(style="Heading 3")
    run = p.add_run(text)
    set_run_font(run, size=14, bold=True, east="黑体", ascii_f="Arial")
    return p


def caption(doc, text, keep_next=False):
    p = doc.add_paragraph(style="Caption")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if keep_next:
        p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    set_run_font(run, size=10.5, bold=True)
    return p


def picture(doc, path, width_in):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    run.add_picture(str(path), width=Inches(width_in))
    return p


def shade_cell(cell, fill="F2F2F2"):
    tcpr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), fill)
    tcpr.append(shd)


def fill_cell(cell, text, size=10.5, bold=False, east="宋体"):
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.line_spacing = 1.15
    run = p.add_run(text)
    set_run_font(run, size=size, bold=bold, east=east)


def add_table(doc, headers, rows, widths_cm):
    t = doc.add_table(rows=len(rows) + 1, cols=len(headers), style="Table Grid")
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for j, h in enumerate(headers):
        c = t.rows[0].cells[j]
        fill_cell(c, h, bold=True, east="黑体")
        shade_cell(c)
    for i, row in enumerate(rows):
        for j, v in enumerate(row):
            fill_cell(t.rows[i + 1].cells[j], v)
    for i, r in enumerate(t.rows):
        # 表头跨页重复 + 行禁止跨页拆分
        trpr = r._tr.get_or_add_trPr()
        cs = OxmlElement("w:cantSplit")
        trpr.append(cs)
        if i == 0:
            th = OxmlElement("w:tblHeader")
            trpr.append(th)
        for j, c in enumerate(r.cells):
            c.width = Cm(widths_cm[j])
    return t


# ---------- 报告头 ----------

def build_header(doc, exp_no, title):
    els = []
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.3
    run = p.add_run("《软件需求工程》实验报告")
    set_run_font(run, size=16, bold=True, east="黑体", ascii_f="Arial")
    els.append(p._p)

    t = doc.add_table(rows=4, cols=4, style="Table Grid")
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    info = [
        ("课程名称", "《软件需求工程》", "实验名称", title),
        ("班级", "【班级】", "姓名", "【姓名】"),
        ("学号", "【学号】", "指导教师", "【指导教师】"),
        ("实验日期", "2026 年 10 月 1 日", "成绩", ""),
    ]
    for i, row in enumerate(info):
        for j, v in enumerate(row):
            c = t.rows[i].cells[j]
            fill_cell(c, v, size=12, bold=(j % 2 == 0), east="黑体" if j % 2 == 0 else "宋体")
            if j % 2 == 0:
                shade_cell(c, "F7F7F7")
            c.width = Cm([2.6, 5.1, 2.6, 5.1][j])
        trpr = t.rows[i]._tr.get_or_add_trPr()
        trpr.append(OxmlElement("w:cantSplit"))
    els.append(t._tbl)

    sp = doc.add_paragraph()
    sp.paragraph_format.space_after = Pt(6)
    els.append(sp._p)

    # 移动到文档最前（保持顺序）
    from docx.document import Document as DocCls  # noqa
    body = doc.element.body
    for el in reversed(els):
        body.insert(0, el)


# ---------- 各实验"实验报告"内容 ----------

def report1(doc):
    body_para(doc, f"本实验选取“{EXP1_SOFTWARE}”作为分析对象。将该软件各模块的界面截图与功能名称列表输入 AI，"
                   "要求其自动生成每个功能的描述与分类，并与人工观察逐条比对、修正完善后填入表 1~表 9（见前文）。"
                   "此外，依据本实验要求，另选取重庆师范大学教务系统的“学生网上选课”功能作为用户体验分析对象，"
                   "由 AI 生成用户使用场景与潜在优缺点，与本人实际使用体验逐条比对核实后填入表 10，最后总结个人体会。")
    h3(doc, f"1. AI 辅助功能提取结果（{EXP1_SOFTWARE}）")
    body_para(doc, f"表 1~表 9 已按模块分类给出 {EXP1_SOFTWARE} 的功能清单、AI 生成的功能描述与人工核实的正确性判定。"
                   "AI 的提取结果整体准确，能够正确区分“优化清理”“软件管理”“快捷工具”“硬件检测”“设置”等模块归属；"
                   "人工比对后修正了两处表述：一是“一键清理”的描述需区分普通与深度两种模式，"
                   "二是“软件瘦身”在本软件中不含卸载预装应用（需 root）的能力，故改写为清理应用冗余文件，"
                   "以免与“系统瘦身/一键瘦身”功能混淆。")
    h3(doc, "2. 教务系统选课功能的用户使用场景")
    body_para(doc, "场景一（选课高峰期抢课）：每学期选课首日选课通道开放后，大量学生同时登录教务系统进入“网上选课”模块。"
                   "学生按课程名称、开课学院、上课时间等条件检索目标课程，查看课程简介、余量与容量后，"
                   "将意向课程加入“选课车”，调整志愿顺序后一次性提交；系统逐条校验学分上限、上课时间冲突与课程容量，并即时反馈选课结果。")
    body_para(doc, "场景二（补退选调整）：开学第一周补退选阶段，学生进入已选课程列表执行退课、换课操作。"
                   "换课时需先退掉原课程再抢占新课程名额，系统对“先退后选”的空窗风险不做保护，"
                   "学生需自行承担退课后无法选回的后果。")
    h3(doc, "3. 用户体验表（AI 生成内容经人工核实修正后填入）")
    caption(doc, "表 10　学生网上选课功能用户体验表", keep_next=True)
    add_table(
        doc,
        ["维度", "AI 生成内容", "人工核实与修正"],
        [
            ["使用场景",
             "选课开放首日高峰期，学生登录教务系统进入网上选课模块，按课程号/教师/时间检索课程，加入选课车并提交；系统实时校验学分上限、时间冲突与课程容量，结果即时反馈。",
             "主干属实。补充：补退选阶段需先退课后换课，系统对“先退后选”的空窗风险不做保护。"],
            ["操作步骤",
             "登录→进入选课模块→按条件筛选课程→查看余量→加入选课车→调整志愿顺序→提交选课→查看选课结果。",
             "与真实系统一致；人工补充：提交后需手动刷新页面才能看到最新选课结果。"],
            ["体验优点",
             "①课程检索条件丰富，支持开课学院、上课时间、学分等多维筛选；②“选课车”模式直观，可先统一挑选后一次性提交；③学分上限与时间冲突实时校验，避免误选。",
             "三条均成立，AI 概括与本人真实使用体验一致。"],
            ["潜在缺点",
             "①高峰期并发量大，页面加载慢、偶发提交超时；②选课结果反馈有延迟，需手动刷新；③容量与余量信息更新不及时，易出现“看似有余量实则已满”的误导；④缺少候补队列机制，落选后只能反复刷新捡漏。",
             "①②④与本人体验一致；③为 AI 合理推断。人工补充：换课“先退后选”存在退课后选不回来的风险，体验较差。"],
            ["改进建议",
             "引入候补队列与自动捡漏通知；高峰期对课程目录页做静态缓存并异步提交；容量变更时推送提醒；提供选课方案提交前预校验。",
             "建议可落地。人工补充：增加“先选后退”安全换课模式，避免退课后无法选回。"],
        ],
        [2.0, 6.7, 6.7],
    )
    h3(doc, "4. 个人体会")
    body_para(doc, "通过本次实验我体会到，AI 对成熟软件的功能描述与场景还原能力较强：只要把功能名称与界面信息输入清晰，"
                   "AI 生成的使用场景在主干流程上基本准确，可以直接作为需求分析的初稿，显著降低文档起步成本。"
                   "但 AI 的输出本质上是“合理推断”，例如它并不知道学校选课系统的真实并发瓶颈和“先退后选”风险，"
                   "必须由使用者以真实体验逐条核实修正，否则会产生似是而非的需求描述。")
    body_para(doc, "从需求工程角度看，用户体验表把“使用场景—优点—痛点—改进建议”结构化呈现，"
                   "是挖掘非功能性需求（性能、可用性）与改进需求的有效工具。本次实验让我认识到："
                   "AI 是效率放大器而不是需求来源，需求的真实性仍来自对真实用户与真实系统的观察，"
                   "“AI 起草 + 人工核实”的人机协同才是正确的工作方式。")
    h3(doc, "5. 实验亮点与创新")
    body_para(doc, "亮点一（技术路线）：采用“AI 批量提取 + 人工逐条核实”的双轨功能清单编制方法。"
                   "先用 AI 一次性生成 9 张功能表的描述与分类草稿，再由人工对照真实界面逐条判定正确性并修正表述，"
                   "把机械性的文字工作交给 AI、把判断权留给人，功能清单编制效率显著提升，"
                   "同时通过“正确性”列显式保留了人工复核的痕迹，使 AI 输出可审计、可追溯。")
    body_para(doc, "亮点二（实验设计）：将“功能清单（表 1~表 9）”与“用户体验表（表 10）”组合为完整分析链路——"
                   "前者自下而上枚举功能，后者围绕单一功能深挖场景、优缺点与改进建议。"
                   "两者互补，避免了只罗列功能而缺乏用户视角的常见问题；"
                   "用户体验表中的“人工核实与修正”列还专门标注了哪些是 AI 的合理推断、哪些经真实体验证伪，"
                   "为后续需求取舍提供了依据。")


def report2(doc):
    body_para(doc, "本小组选题为“绿循校园——校园闲置教材与物品循环流转系统”。以下按实验内容的三个步骤"
                   "（AI 用例提取→绘制与人工修正→AI 验证）完成用例建模，并对用例图配以充分的文字描述。")
    h3(doc, "1. AI 辅助用例提取")
    body_para(doc, "将选题需求描述（含市集检索与发布、碳积分与商城、循环度统计、订单履约、后台审核五部分）输入 AI，"
                   "要求输出参与者列表、用例列表、用例间关系与布局建议。AI 输出：参与者为注册用户、学生买家、学生卖家、"
                   "系统管理员四类；用例 14 个，覆盖浏览检索、发布闲置、预约履约、积分兑换、举报与后台治理；"
                   "并识别出“发布闲置”与“获得碳积分”、“完成流转”与“校验自提码/发放碳积分”之间存在包含关系。")
    h3(doc, "2. 人工修正与 AI 验证")
    body_para(doc, "人工修正三处：①AI 初稿将“登录”写作独立用例，因系统实际采用前端“身份选择器”承载登录语义，"
                   "修正为“选择当前身份（登录）”；②补充 AI 遗漏的“取消订单”用例，保证履约失败路径完整；"
                   "③修正关系方向——取消订单是对“发起预约意向”的扩展（«extend»，可选发生），"
                   "碳积分发放与自提码校验是“完成流转”的必选组成（«include»）。"
                   "修正后将用例图回传 AI 复检，AI 确认参与者泛化（学生买家/学生卖家→注册用户）与三类关系方向无误，"
                   "并建议将后台治理用例与前台用例分区布局，已在图 1 中采纳。")
    h3(doc, "3. 绿循校园系统总体用例图")
    picture(doc, ASSETS / "usecase.png", 5.2)
    caption(doc, "图 1　绿循校园系统总体用例图")
    h3(doc, "4. 用例图文字描述")
    body_para(doc, "各参与者及其职责如表 1 所示。", indent=True)
    caption(doc, "表 1　参与者及其职责", keep_next=True)
    add_table(
        doc,
        ["参与者", "与系统的关系", "主要职责（对应用例）"],
        [
            ["注册用户", "由买家/卖家泛化出的抽象参与者",
             "选择当前身份（登录）、浏览/检索闲置物品、查看环保先锋榜与学院排行、查看碳积分流水、取消订单、举报违规物品"],
            ["学生买家", "注册用户的特化", "发起预约意向、兑换积分商城礼品"],
            ["学生卖家", "注册用户的特化", "发布闲置物品（必然获得碳积分 +10）、确认预约（卖家）、确认完成流转"],
            ["系统管理员", "独立参与者",
             "物品下架/恢复上架、查看与处理违规举报、查看平台全局汇总数据"],
        ],
        [2.2, 3.6, 9.6],
    )
    body_para(doc, "用例分组描述：①市集交易组——浏览检索、发布闲置、发起预约、确认预约、完成流转、取消订单，"
                   "构成“发布→锁定→履约→退出”的交易主干；②积分激励组——获得碳积分、查看积分流水、兑换商城礼品，"
                   "将绿色行为转化为可审计的激励闭环；③合规治理组——举报违规物品、物品下架/恢复上架、处理举报、"
                   "查看平台汇总，为平台运营提供风险控制手段。")
    body_para(doc, "关系说明：①«include»——发布闲置必然包含“获得碳积分（+10）”；确认完成流转必然包含“校验自提码”"
                   "与“获得碳积分（+20）”，三者均为必选子流程，故用包含关系；②«extend»——取消订单是“发起预约意向”"
                   "的可选扩展，仅在用户主动放弃时发生，且发生时物品状态回滚为可预约；③泛化——学生买家与学生卖家继承"
                   "注册用户的全部用例，同一真实学生可兼任两个角色，与系统“同一账号既可发布也可预约”的设计一致。")
    h3(doc, "5. 核心用例规约（亮点）")
    body_para(doc, "以最核心的“确认完成流转”用例为例编写规约，见表 2。")
    caption(doc, "表 2　“确认完成流转”用例规约", keep_next=True)
    add_table(
        doc,
        ["条目", "内容"],
        [
            ["用例名称", "确认完成流转"],
            ["参与者", "买家或卖家（须为订单参与方）"],
            ["前置条件", "订单存在且状态为“待自提（confirmed）”；操作者为订单参与方"],
            ["基本流",
             "①参与方线下验货后点击“完成流转”；②系统校验操作者身份；③操作者输入自提码，系统与订单 pickup_code 比对；"
             "④订单状态更新为“已完成”；⑤物品状态更新为 completed、循环度 +1、减碳量按类别累加；"
             "⑥卖家碳积分 +20 并写入积分流水；⑦前端刷新统计大屏与个人中心"],
            ["备选流",
             "2a 非参与方操作：拒绝并返回 403；3a 自提码不正确：提示“自提码不正确”，允许重新输入；"
             "1a 订单状态非 confirmed：状态机拒绝扭转并返回中文原因（如“订单状态为「待自提」，不能执行该操作”）"],
            ["后置条件", "交易闭环完成：物品退出市集，全校循环度与减碳统计更新，卖家积分入账且流水可审计"],
        ],
        [3.0, 12.4],
    )
    h3(doc, "6. 用例与系统实现的一致性")
    body_para(doc, "本用例图并非纸面设计：图 1 中每个用例均可与系统真实接口一一对应，"
                   "如“发起预约意向”对应 POST /api/orders、“确认完成流转”对应 POST /api/orders/{id}/complete、"
                   "“物品下架/恢复上架”对应 /api/admin/items/{id}/offshelf 与 /restore。"
                   "需求模型与交付代码双向可追踪，避免了用例图与实现“两张皮”。")
    h3(doc, "7. 实验亮点与创新")
    body_para(doc, "亮点一（技术路线）：需求模型与可运行系统同源交付。本实验的用例并非为绘图而虚构，"
                   "而是直接取自本小组已实现并已通过测试的“绿循校园”系统：全部 14 个用例都能在代码中定位到对应接口，"
                   "碳积分 +10/+20、自提码 GC-XXXXXX、状态机扭转等业务规则均与真实实现一致，"
                   "真正做到了“需求—模型—代码”三向可追踪，这是纯文档式建模无法达到的。")
    body_para(doc, "亮点二（实验设计）：用「用例规约」补足图形表达的精度缺口。用例图只能表达“谁做什么”，"
                   "无法刻画前置条件、基本流、备选流与后置条件。为此本实验为最核心的“确认完成流转”用例补充了完整规约，"
                   "把自提码校验失败、非参与方操作、状态非法扭转三类异常路径全部写明，"
                   "并对应到实现中返回的中文错误提示，使模型具备直接指导开发与测试的精度。")


def report3(doc):
    body_para(doc, "本实验以本小组选题“绿循校园”为对象，按“AI 类抽取→人工对比修正→绘制类图”的步骤完成静态结构建模，"
                   "并对类图配以充分的文字描述。")
    h3(doc, "1. AI 辅助类抽取")
    body_para(doc, "将系统需求描述与实验二用例图输入 AI，要求识别候选类、属性、方法及类间关系。"
                   "AI 输出草稿包含六个实体类：User（用户）、Item（物品）、Order（订单）、PointLog（积分流水）、"
                   "Product（兑换礼品）、Report（违规举报）；识别出 User 与 Item 的“发布”关联、Item 与 Order 的“标的”"
                   "关联、User 与 Order 间的买家/卖家双重关联；方法层面给出 addPoints()、transition() 等建议。")
    h3(doc, "2. 人工对比修正与差异讨论")
    body_para(doc, "与人工设计对比，AI 草稿的差异及修正如下：①AI 曾将“碳积分账户”建模为独立类 Account，"
                   "人工分析认为积分仅是 User 的属性且必须以流水留痕，修正为 User.points 属性 + PointLog 流水类，"
                   "这也与数据库表结构一致；②AI 将减碳系数内联硬编码在 Item 方法中，人工修正为服务层常量集中定义"
                   "（CARBON_FACTOR：教材 2.5/考研 2.0/生活品 3.5 kg），避免魔法数字散落；"
                   "③AI 未体现 Order.sellerId 的冗余设计意图（冻结下单时的发布者），类图中予以保留并在职责说明中注明。"
                   "最终类图以人工修正稿为准。")
    h3(doc, "3. 绿循校园系统核心类图")
    picture(doc, ASSETS / "class.png", 5.9)
    caption(doc, "图 1　绿循校园系统核心类图")
    h3(doc, "4. 类图文字描述")
    body_para(doc, "各类的职责如表 1 所示。")
    caption(doc, "表 1　核心类职责说明", keep_next=True)
    add_table(
        doc,
        ["类名", "职责说明", "关键属性 / 方法"],
        [
            ["User", "平台账户，承载身份与碳积分余额",
             "points、role；addPoints() 统一记账并联动流水，isAdmin() 支撑后台权限校验"],
            ["Item", "闲置物品聚合根，携带循环度与减碳量两大核心指标",
             "cycleCount、carbonSaved、status；completeCycle() 完成一次流转"],
            ["Order", "交易履约单，维护订单状态机与自提码",
             "status、pickupCode；transition() 校验合法扭转，verifyPickupCode() 校验自提码"],
            ["PointLog", "碳积分账本，只增不改、可审计", "delta 正负表收支，reason 记录事由"],
            ["Product", "积分商城兑换品", "costPoints、stock；兑换时扣减积分与库存"],
            ["Report", "违规举报单，状态 open→resolved 单向流转", "reason、status"],
        ],
        [1.8, 5.2, 8.4],
    )
    body_para(doc, "关系与多重性说明：User–Item（1 对 0..*，发布）、User–PointLog（1 对 0..*，记账）、"
                   "Item–Order（1 对 0..*，标的）、User–Report（1 对 0..*，举报）、Item–Report（1 对 0..*，被举报）"
                   "均为普通关联；User–Order 因同一用户可兼作买家与卖家，以一条关联标注双重角色。"
                   "本系统实体间不存在继承与聚合：六个类是平行的业务实体，无需抽象基类；"
                   "PointLog、Report 虽逻辑上依附主实体，但拥有独立生命周期且按主键独立存取，"
                   "故以普通关联而非聚合表达——这与关系数据库外键的物理实现完全一致。")
    h3(doc, "5. 类图与数据持久层的一致性（亮点）")
    body_para(doc, "类图的每个属性都可在 schema.sql 数据字典中找到同名字段（驼峰对应下划线），"
                   "如 Item.cycleCount ↔ items.cycle_count、Order.pickupCode ↔ orders.pickup_code；"
                   "图中方法亦与实现对应（User.addPoints → database.add_points，Order.transition → 状态机 _transition）。"
                   "类图因此成为连接需求模型与物理设计的枢纽，实现“用例—类—表”三方相互可追踪。")
    body_para(doc, "为验证这一一致性而非仅作声明，本实验编写了校验脚本：自动解析 schema.sql 的建表语句提取全部字段，"
                   "再解析类图源文件提取各类属性，经驼峰—下划线转换后逐类比对，结果见表 2。")
    caption(doc, "表 2　类图属性与数据库字段一致性校验结果", keep_next=True)
    add_table(
        doc,
        ["类名", "对应数据表", "类属性数", "表字段数", "校验结果"],
        [
            ["User", "users", "6", "6", "✓ 完全一致"],
            ["Item", "items", "9", "9", "✓ 完全一致"],
            ["Order", "orders", "7", "7", "✓ 完全一致"],
            ["PointLog", "point_logs", "4", "4", "✓ 完全一致"],
            ["Product", "products", "5", "5", "✓ 完全一致"],
            ["Report", "reports", "5", "5", "✓ 完全一致"],
            ["合计", "6 张表", "36", "36", "6/6 类通过校验"],
        ],
        [2.2, 3.0, 2.2, 2.2, 5.8],
    )
    body_para(doc, "校验脚本首次运行时暴露出真实差异：初版类图遗漏了各表的 created_at（以及 items.description、"
                   "products.description/emoji、orders.updated_at）等字段，仅建模了业务关注的核心属性。"
                   "据此补齐类图属性后复检达到 6/6 完全一致。这说明静态结构模型若脱离物理设计独立维护，"
                   "极易随时间漂移；把“模型与建表脚本自动比对”纳入实验流程，可让类图始终与代码保持同步。")
    h3(doc, "6. 实验亮点与创新")
    body_para(doc, "亮点一（技术路线）：模型与物理设计的一致性可脚本化验证。不同于仅凭肉眼核对类图与数据表的常规做法，"
                   "本实验用脚本自动解析建表 DDL 与类图源文件并逐字段比对，把“一致性”从主观断言变成可复现的客观结论"
                   "（6/6 类通过），并借该校验发现并修正了初版类图的字段遗漏，体现了模型驱动与自动化校验相结合的技术路线。")
    body_para(doc, "亮点二（实验设计）：以 AI 草稿为对照组反推设计缺陷。实验先由 AI 生成类图草稿，"
                   "再与人工设计逐项对比，发现 AI 存在“把积分账户误建为独立类”“把减碳系数硬编码进方法”等问题，"
                   "据此确立了“积分作为属性 + 流水类留痕”“系数集中于服务层常量”的设计。"
                   "把 AI 输出当作反面对照而非最终答案，是本实验在设计方法上的一点创新。")


def report4(doc):
    body_para(doc, "本实验以本小组选题“绿循校园”的两个核心场景——“发起预约意向”与“线下验货后确认完成流转”——为对象，"
                   "按“AI 交互流程生成→绘制顺序图→AI 动态调整”的步骤完成动态交互建模，并配以充分的文字描述。")
    h3(doc, "1. AI 辅助交互流程生成")
    body_para(doc, "将两个场景的基本流文字输入 AI，要求输出参与对象、消息列表与顺序、生命线排列建议。"
                   "AI 给出的参与对象为：买家/卖家（执行者）、前端页面（Vue SPA）、API 服务（main.py）、SQLite 数据库；"
                   "生命线按“执行者→界面→服务→数据”自左向右排列，与系统四层架构一致；"
                   "消息序列覆盖请求、状态校验、写库、事务提交、响应与前端反馈各环节。")
    h3(doc, "2. 人工修正")
    body_para(doc, "人工修正两点：①AI 初稿把异常路径画成普通消息，人工改为 alt 分组框，"
                   "明确“物品不可预约/预约自购物品”“自提码不正确/非参与方”等分支的中文错误反馈，与真实接口行为一致；"
                   "②AI 将循环度、减碳量、积分三处更新画成三次独立提交，人工按实现修正为“同一事务提交”"
                   "（代码中共享连接最后统一 commit），避免读者误认为存在中间状态。")
    h3(doc, "3. 发起预约意向顺序图")
    picture(doc, ASSETS / "seq_reserve.png", 5.9)
    caption(doc, "图 1　“发起预约意向”顺序图")
    h3(doc, "4. 确认完成流转顺序图")
    picture(doc, ASSETS / "seq_complete.png", 5.9)
    caption(doc, "图 2　“确认完成流转”顺序图")
    h3(doc, "5. 顺序图文字描述")
    body_para(doc, "各对象的职责如表 1 所示，“确认完成流转”的关键消息如表 2 所示。")
    caption(doc, "表 1　参与对象及其职责", keep_next=True)
    add_table(
        doc,
        ["对象", "类型", "职责"],
        [
            ["买家 / 卖家", "执行者", "发起预约意向，或线下验货后确认完成流转"],
            ["前端页面（Vue SPA）", "边界对象", "表单交互、调用 API、Toast 反馈、刷新积分与排行数据"],
            ["API 服务（main.py）", "控制对象",
             "参数校验、状态机扭转（_transition）、自提码生成与比对、积分账务（add_points）、事务控制"],
            ["SQLite 数据库", "数据对象", "持久化订单/物品/积分流水，保证外键约束与事务一致性"],
        ],
        [3.4, 2.2, 9.8],
    )
    caption(doc, "表 2　“确认完成流转”关键消息说明", keep_next=True)
    add_table(
        doc,
        ["序号", "消息", "说明"],
        [
            ["1", "POST /api/orders/{id}/complete {user_id, pickup_code}", "前端提交操作者身份与自提码"],
            ["2", "SELECT 订单", "读取订单当前状态与自提码"],
            ["3", "403 / 400 错误响应", "非参与方（403）或自提码不正确（400）时短路返回，不产生任何写操作"],
            ["4", "UPDATE 订单 (status=completed)", "状态机合法扭转 confirmed→completed"],
            ["5", "UPDATE 物品 (completed, cycle_count+1, carbon_saved+估算值)", "循环度与减碳量联动更新"],
            ["6", "UPDATE 卖家 (points+20)、INSERT point_logs", "卖家积分入账并写入流水留痕"],
            ["7", "200 订单 JSON → 前端刷新", "返回完成后前端刷新统计大屏与个人中心数据"],
        ],
        [1.2, 7.6, 6.6],
    )
    h3(doc, "6. AI 动态调整：需求变更对交互设计的影响")
    body_para(doc, "按实验要求向 AI 描述一项变更需求：“预约发起后若 30 分钟内卖家未确认，订单自动取消并释放物品。”"
                   "AI 给出的调整建议为：新增“定时任务调度器”参与对象，以定时消息扫描过期订单，"
                   "向数据库发送 UPDATE orders SET status='cancelled' 及物品回滚消息，"
                   "并建议补充守卫条件 status='reserved' AND created_at < now()-30min。"
                   "由此体会到：一个看似局部的需求变更会沿交互链路传播——顺序图需新增对象与消息，"
                   "前端需增加订单倒计时提示，实现侧需引入定时任务与并发防护（避免与人工取消/完成操作竞争）。"
                   "需求变更分析必须以交互模型为落点逐环排查，这正是顺序图作为沟通工具的价值。")
    h3(doc, "7. 实验亮点与创新")
    body_para(doc, "亮点一（实验设计）：以“alt 分组框”显式建模异常路径，而非只画顺利流程。两张顺序图都把"
                   "“物品不可预约/预约自购物品”“自提码不正确/非参与方操作”等失败分支画进同一张图，"
                   "并标注接口真实返回的中文错误文案。由于异常分支在需求评审中最容易被忽略、在实现中最容易出错，"
                   "这种“正常流与异常流同图呈现”的画法使模型具备了直接驱动测试用例设计的能力。")
    body_para(doc, "亮点二（技术路线）：用 AI 做需求变更影响传播分析。实验末尾以“预约 30 分钟未确认则自动取消”"
                   "这一变更需求为输入，由 AI 推导其对交互设计的影响，得到需新增定时任务调度器参与对象、"
                   "新增过期订单扫描消息、前端增加倒计时提示、实现侧引入并发防护等连锁结论。"
                   "该演练验证了顺序图作为“变更影响分析工具”的价值——一处需求变更会沿消息链路逐环传播，"
                   "必须借助交互模型才能完整排查，而不是只改一处代码了事。")


def report5(doc):
    body_para(doc, "本实验以本小组选题“绿循校园”的订单履约全流程为对象，按“AI 流程分析→绘制活动图→AI 优化比较”"
                   "的步骤完成业务流程建模，并配以充分的文字描述。")
    h3(doc, "1. AI 流程分析")
    body_para(doc, "将订单履约场景文字输入 AI，要求输出活动图节点、分支条件与并行区域。AI 识别出："
                   "3 个判定节点（物品是否 available、卖家是否确认、自提码是否一致）、1 个循环结构"
                   "（自提码错误重新输入）、1 个并行区域（完成流转后的“状态与指标更新”与“积分入账”两条支路）"
                   "以及 3 条正常/异常终止路径。与人工分析结果一致，仅节点措辞略有差异，已按实现术语修正。")
    h3(doc, "2. 订单履约与流转确认活动图")
    picture(doc, ASSETS / "activity.png", 5.5)
    caption(doc, "图 1　订单履约与流转确认活动图")
    h3(doc, "3. 活动图文字描述")
    body_para(doc, "主要活动节点如表 1 所示。")
    caption(doc, "表 1　主要活动节点说明", keep_next=True)
    add_table(
        doc,
        ["节点", "类型", "说明"],
        [
            ["生成自提码 GC-XXXXXX", "动作", "服务端随机生成，订单创建时落库，用于线下履约防伪"],
            ["订单置为 reserved／物品同步锁定", "动作", "预约成功，物品退出可预约池，防止重复交易"],
            ["订单置为 confirmed（待自提）", "动作", "卖家确认后进入线下履约阶段"],
            ["买卖双方线下验货", "动作", "线下环节，系统不介入"],
            ["输入自提码并发起确认完成", "动作", "凭码确认，防止虚假完成"],
            ["状态更新/循环度+1/减碳累加", "并行分支 1", "与分支 2 无数据依赖，可并行执行"],
            ["卖家碳积分 +20／写入 point_logs", "并行分支 2", "与分支 1 汇合后同一事务提交"],
            ["物品回滚为 available", "异常路径动作", "订单取消时释放占用，保证资源不泄漏"],
        ],
        [5.6, 2.4, 7.4],
    )
    body_para(doc, "分支与合并说明：判定“物品状态为 available？”防止重复锁定；判定“卖家确认预约？”区分履约与取消"
                   "两条路径，取消支路必须将物品回滚为可预约；判定“自提码与订单 pickup_code 一致？”与循环回边构成"
                   "重试结构，只有校验通过才进入完成分支。并行区域说明：fork 之后两条支路分别处理交易状态与积分入账，"
                   "互不读取对方结果，逻辑上可并行；join 汇合后在同一 SQLite 事务中提交，"
                   "保证“指标更新”与“积分入账”要么同时生效、要么同时回滚。")
    h3(doc, "4. AI 优化：两种流程方案的比较（亮点）")
    body_para(doc, "请 AI 生成两种备选流程并比较其影响。方案 A（串行）：先完成状态与指标更新，再串行发放积分；"
                   "方案 B（并行，即图 1 采用）：以 fork/join 并行表达两条支路。比较结论："
                   "①可读性上，B 更直观地暴露“两件事互不依赖”这一设计事实；"
                   "②一致性上，两者等价，均须在同一事务中提交，活动图的并行不代表数据库层面的并发写；"
                   "③异常恢复上，B 的 join 点天然构成提交边界，回滚语义清晰。"
                   "系统最终采用“活动图并行表意 + 单事务串行实现”的组合，兼得模型表达力与实现确定性。"
                   "该比较也说明：活动图的并行/分支属于逻辑视角，落地时必须结合持久层事务机制复核，"
                   "这正是“AI 给出备选方案、人工做工程裁决”协同方式的价值所在。")
    h3(doc, "5. 实验亮点与创新")
    body_para(doc, "亮点一（实验设计）：并行区域与事务边界的分层表达。活动图用 fork/join 表达“状态指标更新”与"
                   "“积分入账”两条支路的逻辑并行，同时明确指出二者在实现中汇合于同一 SQLite 事务提交。"
                   "这一处理避免了初学者常见的误区——把活动图的并行直接等同于数据库层的并发写，"
                   "在建模层保留并行语义的同时守住了一致性底线，体现了业务模型与技术实现的分层思考。")
    body_para(doc, "亮点二（技术路线）：以多方案比较支撑流程决策。实验不止画出一张活动图，"
                   "而是请 AI 生成串行与并行两种备选流程，从可读性、一致性、异常恢复三个维度比较其影响，"
                   "最终采用“并行表意 + 单事务实现”的组合。把“AI 生成备选方案、人工按工程标准裁决”"
                   "作为流程设计的收口方式，是本实验在方法上的一点创新，也使流程设计结论有据可依。")


BUILDERS = {1: report1, 2: report2, 3: report3, 4: report4, 5: report5}


# ---------- 实验一：表 1~表 9 功能清单（自选软件：腾讯手机管家） ----------
EXP1_SOFTWARE = "腾讯手机管家"

EXP1_TABLES = [
    # 表 1 [优化清理]
    [["功能分类", "功能名称", "功能描述", "正确性"],
     ["优化清理", "一键优化", "综合扫描手机状态并一键优化，提升整体运行速度。", "是"],
     ["", "内存清理", "清理后台运行进程，释放运行内存。", "是"],
     ["", "垃圾清理", "清理应用缓存、系统垃圾与卸载残留文件。", "是"],
     ["", "自启管理", "限制应用开机自启动，减少后台资源占用。", "是"],
     ["", "隐私清理", "清理剪贴板、浏览记录等使用痕迹，保护隐私。", "是"]],
    # 表 2 [内存清理]
    [["功能分类", "功能名称", "功能描述", "正确性"],
     ["内存清理", "清理模式", "提供普通清理与深度清理两种模式，可自由切换。", "是"],
     ["", "白名单", "白名单内的应用在执行清理时不会被关闭。", "是"],
     ["", "一键加速", "一键结束后台进程，并实时显示可用内存变化。", "是"]],
    # 表 3 [软件管理]
    [["功能分类", "功能名称", "功能描述", "正确性"],
     ["软件管理", "软件卸载", "卸载手机中已安装的第三方应用。", "是"],
     ["", "软件升级", "检测并批量升级可更新的应用。", "是"],
     ["", "默认软件设置", "设置默认输入法、浏览器等常用应用。", "是"],
     ["", "安装包管理", "管理已下载的安装包，支持批量删除。", "是"],
     ["", "软件搬家", "在手机存储与 SD 卡之间迁移应用安装位置。", "是"],
     ["", "软件瘦身", "清理应用冗余文件，释放存储空间。", "是"]],
    # 表 4 [软件卸载]
    [["功能分类", "功能名称", "功能描述", "正确性"],
     ["软件卸载", "排序", "按名称、大小或安装时间对应用排序。", "是"],
     ["", "备份", "备份被卸载的应用，便于日后恢复。", "是"],
     ["", "卸载", "执行应用卸载操作。", "是"]],
    # 表 5 [系统瘦身]
    [["功能分类", "功能名称", "功能描述", "正确性"],
     ["系统瘦身", "回收站", "自动备份已卸载的预装应用，支持还原。", "是"],
     ["", "一键瘦身", "批量卸载可移除的预装系统应用。", "是"]],
    # 表 6 [快捷工具]
    [["功能分类", "功能名称", "功能描述", "正确性"],
     ["快捷工具", "存储分析", "查看内置存储与 SD 卡的空间占用情况。", "是"],
     ["", "定时任务", "定时执行内存清理、开关 WiFi 等操作。", "是"],
     ["", "铃声设置", "设置来电铃声与短信提示音。", "是"],
     ["", "手机设置", "快捷跳转至手机系统设置。", "是"],
     ["", "字体美化", "更换手机显示字体，美化界面。", "是"]],
    # 表 7 [硬件检测]
    [["功能分类", "功能名称", "功能描述", "正确性"],
     ["硬件检测", "立即评测", "对手机硬件性能进行评测并给出得分。", "是"],
     ["", "排行榜", "上传得分与其他机型进行对比。", "是"]],
    # 表 8 [设置]
    [["功能分类", "功能名称", "功能描述", "正确性"],
     ["设置", "禁用启动项", "安装新应用时提醒禁用其自启动权限。", "是"],
     ["", "软件搬家通知", "安装应用时提醒可将其移至 SD 卡。", "是"],
     ["", "开机时间通知", "在通知栏显示本次开机耗时。", "是"],
     ["", "添加桌面快捷方式", "在桌面添加应用快捷方式。", "是"],
     ["", "自动检测新版本", "自动检测并升级本软件。", "是"],
     ["", "绑定账号", "绑定社交账号以便同步数据。", "是"],
     ["", "自动上传评分", "自动上传评测得分参与排行榜。", "是"]],
    # 表 9 [其它]
    [["功能分类", "功能名称", "功能描述", "正确性"],
     ["其它", "联网升级", f"在线升级{EXP1_SOFTWARE}自身。", "是"],
     ["", "推荐好友", f"将{EXP1_SOFTWARE}推荐给好友。", "是"],
     ["", "提交意见", "提交用户反馈意见。", "是"],
     ["", "关于", "查看软件版本与相关信息。", "是"]],
]


def set_cell_text(cell, text):
    """改写单元格文字，保留首个 run 的格式，清除多余 run 与段落。"""
    p = cell.paragraphs[0]
    if p.runs:
        p.runs[0].text = text
        for r in p.runs[1:]:
            r._element.getparent().remove(r._element)
    else:
        p.add_run(text)
    for extra in cell.paragraphs[1:]:
        extra._element.getparent().remove(extra._element)


def replace_exp1_tables(doc):
    """将模板表 1~表 9 的内容替换为自选软件的功能清单（表头与分类结构保持一致）。
    按表头签名（功能分类/功能名称/功能描述/正确性）定位，避免误改信息表。"""
    targets = []
    for tbl in doc.tables:
        try:
            hdr = [c.text.strip() for c in tbl.rows[0].cells]
        except IndexError:
            continue
        if hdr[:4] == ["功能分类", "功能名称", "功能描述", "正确性"]:
            targets.append(tbl)
    for tbl, data in zip(targets, EXP1_TABLES):
        seen = set()
        for r, row in enumerate(data):
            for c, val in enumerate(row):
                cell = tbl.rows[r].cells[c]
                if cell._tc in seen:      # 纵向合并单元格的延续，跳过
                    continue
                seen.add(cell._tc)
                set_cell_text(cell, val)


# ---------- 模板清理：折叠连续空段 ----------
from docx.text.paragraph import Paragraph


def collapse_empty_paras(doc, max_consecutive=2):
    body = doc.element.body
    count = 0
    for el in list(body):
        if el.tag == qn("w:p"):
            p = Paragraph(el, doc)
            if p.text.strip() == "" and "graphicData" not in el.xml:
                count += 1
                if count > max_consecutive:
                    body.remove(el)
                continue
        count = 0


def strip_anchored_drawings(doc):
    """剥离封面遗留的浮动装饰元素。模板正文本无内联图片，
    因此锚定 DrawingML、VML(w:pict) 及其 mc:AlternateContent 兼容包装一并移除。"""
    W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    MC = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"
    body = doc.element.body
    for tag in (W + "drawing", W + "pict", MC + "AlternateContent"):
        for el in list(body.iter(tag)):
            parent = el.getparent()
            if parent is not None:
                parent.remove(el)


def build(exp_no):
    spec = EXPERIMENTS[exp_no]
    doc = docx.Document(str(TEMPLATE))

    # 1) 裁剪：仅保留该实验原文（目的要求+实验内容+“实验报告”标题）
    body = doc.element.body
    children = list(body)
    sectpr = children[-1]
    lo, hi = spec["keep"]
    keep = set(range(lo, hi + 1))
    for i, el in enumerate(children[:-1]):
        if i not in keep:
            body.remove(el)
    collapse_empty_paras(doc)
    strip_anchored_drawings(doc)
    if exp_no == 1:
        replace_exp1_tables(doc)

    # 2) 报告头
    build_header(doc, exp_no, spec["title"])

    # 3) 填写“实验报告”
    BUILDERS[exp_no](doc)

    # 4) 页眉（run 可能被拆分，需在段落级整体替换）
    hdr = doc.sections[0].header
    for p in hdr.paragraphs:
        full = "".join(r.text for r in p.runs)
        if "实验指导书" in full:
            new = full.replace("《软件需求工程》实验指导书", "《软件需求工程》实验报告")
            for r in p.runs:
                r.text = ""
            if p.runs:
                p.runs[0].text = new

    out = BASE / f"软件需求工程实验{'一二三四五'[exp_no - 1]}报告.docx"
    doc.save(str(out))
    print("saved", out.name)


if __name__ == "__main__":
    for n in EXPERIMENTS:
        build(n)
