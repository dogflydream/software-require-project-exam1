# -*- coding: utf-8 -*-
"""生成实验报告汇总版：完整保留《实验指导书》原文与版式，
在每篇实验的“实验报告”要求段之后填入对应成果内容（与单行本一致）。"""
import sys
from pathlib import Path

import docx
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

sys.path.insert(0, str(Path(__file__).parent))
from build_reports import (  # noqa: E402
    BUILDERS, collapse_empty_paras, fill_cell, set_run_font, shade_cell,
    replace_exp1_tables, TEMPLATE, report1, report2, report3, report4, report5,
)

BASE = Path(__file__).parent
BUILDERS_ALL = {1: report1, 2: report2, 3: report3, 4: report4, 5: report5}

INSTR_MARKS = {
    1: "针对“重庆师范大学教务系统”",
    2: "画出用例图",
    3: "画出类图",
    4: "画出顺序图",
    5: "画出活动图",
}


def info_table(doc):
    """总信息表（置于封面之后、实验一之前）。"""
    t = doc.add_table(rows=4, cols=4, style="Table Grid")
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    info = [
        ("课程名称", "《软件需求工程》", "选题名称", "绿循校园——校园闲置教材与物品循环流转系统"),
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
            c.width = Cm([2.6, 4.3, 2.6, 6.4][j])
        trpr = t.rows[i]._tr.get_or_add_trPr()
        trpr.append(OxmlElement("w:cantSplit"))
    return t


def body_children(doc):
    """正文子元素（排除末尾 sectPr）。"""
    return [el for el in doc.element.body if el.tag != qn("w:sectPr")]


def build():
    doc = docx.Document(str(TEMPLATE))
    collapse_empty_paras(doc)
    replace_exp1_tables(doc)
    body = doc.element.body

    # 1) 定位五个“实验报告”要求段与“实验一”标题段
    from docx.text.paragraph import Paragraph
    paras = [Paragraph(el, doc) for el in body if el.tag == qn("w:p")]
    instr = {}
    exp1_p = None
    for p in paras:
        txt = p.text.strip()
        for n, mark in INSTR_MARKS.items():
            if txt.startswith(mark) or mark in txt[:30]:
                instr.setdefault(n, p)
        if exp1_p is None and txt.startswith("实验一"):
            exp1_p = p

    # 2) 总信息表插入到“实验一”标题之前；信息表前加分页符，保证封面独立成页
    from docx.enum.text import WD_BREAK
    tbl_el = info_table(doc)._tbl
    body.remove(tbl_el)
    pb = doc.add_paragraph()
    pb.add_run().add_break(WD_BREAK.PAGE)
    body.remove(pb._p)
    exp1_p._p.addprevious(pb._p)
    exp1_p._p.addprevious(tbl_el)
    spacer = doc.add_paragraph()
    spacer.paragraph_format.space_after = Pt(6)
    body.remove(spacer._p)
    exp1_p._p.addprevious(spacer._p)

    # 3) 在每个“实验报告”要求段之后填入对应内容。
    #    构建器一律向文档尾部追加，故新增元素 = 插入后尾部多出的部分（不做 id 比对，
    #    避免 lxml 代理对象地址复用导致既有元素被误判为新元素而搬走）。
    for n, builder in BUILDERS_ALL.items():
        p = instr[n]
        n_before = len(body_children(doc))
        builder(doc)
        new_els = body_children(doc)[n_before:]
        for el in reversed(new_els):
            p._p.addnext(el)

    # 4) 页眉与封面标题：指导书 → 实验报告
    for sec in doc.sections:
        for p in sec.header.paragraphs:
            full = "".join(r.text for r in p.runs)
            if "实验指导书" in full:
                new = full.replace("《软件需求工程》实验指导书", "《软件需求工程》实验报告")
                for r in p.runs:
                    r.text = ""
                if p.runs:
                    p.runs[0].text = new
    for t_el in body.iter(qn("w:t")):
        if t_el.text and "实验指导书" in t_el.text:
            t_el.text = t_el.text.replace("实验指导书", "实验报告")

    out = BASE / "软件需求工程实验报告汇总（实验一至实验五）.docx"
    doc.save(str(out))
    print("saved", out.name)


if __name__ == "__main__":
    build()
