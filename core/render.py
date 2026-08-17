"""赛博诡秘的图文卡片渲染。"""
from __future__ import annotations

import html as _html


_KIND_CLASS = {
    "birth": "line-birth",
    "youth": "line-youth",
    "contact": "line-key",
    "advance": "line-key",
    "acting": "line-acting",
    "crisis": "line-crisis",
    "madness": "line-crisis",
    "meta": "line-meta",
    "climb": "",
    "ending": "line-key",
}

_TALENT_EFFECTS = {
    "contact_bonus": "非凡接触",
    "acting_bonus": "扮演消化",
    "madness_resist": "疯狂抗性",
    "luck": "命运眷顾",
    "start_madness": "初始疯狂",
    "outer_chance": "星空注视",
}


def _esc(value: object) -> str:
    """HTML 转义，防止文本破坏卡片。"""
    return _html.escape(str(value or ""), quote=True)


def _chunk_lines(
    body_lines: list[tuple[str, str]], max_lines: int = 36, max_chars: int = 3600
) -> list[list[tuple[str, str]]]:
    """优先使用横向网格；仅在内容极多时才分页。"""
    chunks: list[list[tuple[str, str]]] = []
    current: list[tuple[str, str]] = []
    chars = 0
    for line in body_lines:
        length = len(line[1])
        if current and (len(current) >= max_lines or chars + length > max_chars):
            chunks.append(current)
            current = []
            chars = 0
        current.append(line)
        chars += length
    if current:
        chunks.append(current)
    return chunks or [[]]


def build_life_html(
    header_lines: list[str],
    body_lines: list[tuple[str, str]],
    ending_title: str,
    ending_text: str,
    seq_note: str,
    footer: str,
    *,
    page: int = 1,
    total_pages: int = 1,
    show_ending: bool = True,
) -> str:
    """渲染一页高分辨率、易阅读的人生年鉴卡片。"""
    header_html = "\n".join(
        f'<div class="hline">{_esc(line)}</div>' for line in header_lines
    )
    body_html = "\n".join(
        f'<div class="line {_KIND_CLASS.get(kind, "")}">{_esc(text)}</div>'
        for kind, text in body_lines
    ) or '<div class="line line-meta">雾中没有留下可辨认的文字。</div>'
    ending_html = ""
    if show_ending:
        ending_html = f'''<div class="ending">【结局】{_esc(ending_title)}</div>
  <div class="etext">{_esc(ending_text)}</div>
  <div class="note">{_esc(seq_note)}</div>
  <div class="footer">{_esc(footer)}</div>'''
    else:
        ending_html = '<div class="continue">灰雾仍在翻涌，下一页继续。</div>'
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    width: 1520px; padding: 32px; color: #e7dfca;
    font-family: "Noto Sans SC", "Microsoft YaHei", serif;
    background: radial-gradient(circle at 12% 10%, rgba(143, 92, 190, .24), transparent 32%),
      radial-gradient(circle at 88% 90%, rgba(33, 109, 146, .22), transparent 35%),
      linear-gradient(145deg, #080b14, #171426 52%, #08121b);
  }}
  .card {{ border: 1px solid rgba(222, 190, 108, .58); border-radius: 24px; padding: 30px 34px;
    background: rgba(8, 11, 19, .86); box-shadow: 0 0 70px rgba(126, 83, 188, .2), inset 0 0 60px rgba(35, 23, 68, .24); }}
  .top {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;
    padding-bottom: 16px; border-bottom: 1px solid rgba(222, 190, 108, .35); }}
  .title {{ font-size: 38px; font-weight: 800; letter-spacing: 7px; color: #f0ce7c; text-shadow: 0 0 20px rgba(240, 206, 124, .32); }}
  .page {{ font-size: 15px; letter-spacing: 2px; color: #a99abf; }}
  .hline {{ font-size: 18px; line-height: 1.5; color: #c7ba9b; margin: 5px 0; padding-left: 13px; border-left: 3px solid rgba(222, 190, 108, .35); }}
  .sep {{ height: 1px; margin: 18px 0 14px; background: linear-gradient(90deg, transparent, rgba(222,190,108,.65), transparent); }}
  .timeline {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 11px; }}
  .line {{ font-size: 18.5px; line-height: 1.58; word-break: break-word; color: #ddd5c4; margin: 0; padding: 10px 12px 10px 15px;
    border-left: 4px solid rgba(222, 190, 108, .46); border-radius: 0 10px 10px 0; background: linear-gradient(90deg, rgba(222, 190, 108, .10), transparent 88%); }}
  .line-birth {{ color: #c9d2e9; border-left-color: #8499c8; }}
  .line-youth {{ color: #b8c5df; border-left-color: #8797bd; }}
  .line-key {{ color: #f0dba0; border-left-color: #e2b95e; }}
  .line-key::before {{ content: "◈ "; color: #e2b95e; }}
  .line-acting {{ color: #b8d9a9; border-left-color: #89bb7b; }}
  .line-acting::before {{ content: "✧ "; color: #89bb7b; }}
  .line-crisis {{ color: #e4ad9d; border-left-color: #c46a57; }}
  .line-crisis::before {{ content: "☠ "; color: #c46a57; }}
  .line-meta {{ color: #baadd4; border-left-color: #9882bb; font-style: italic; }}
  .line-meta::before {{ content: "☾ "; color: #9882bb; }}
  .ending {{ margin-top: 22px; padding: 14px 0; text-align: center; font-size: 27px; font-weight: 800; letter-spacing: 4px; color: #f0ce7c; border-top: 1px solid rgba(222,190,108,.4); border-bottom: 1px solid rgba(222,190,108,.4); }}
  .etext {{ margin: 13px 14px 0; font-size: 20px; line-height: 1.7; color: #e4dccd; text-align: center; }}
  .note {{ margin-top: 16px; font-size: 18px; color: #c9ba9b; text-align: center; }}
  .footer {{ margin-top: 19px; padding-top: 14px; font-size: 15px; color: #a79eae; text-align: center; border-top: 1px dashed rgba(222,190,108,.32); }}
  .continue {{ margin-top: 24px; padding-top: 16px; color: #a99abf; text-align: center; font-size: 17px; letter-spacing: 2px; border-top: 1px dashed rgba(222,190,108,.3); }}
</style>
</head>
<body><div class="card">
  <div class="top"><div class="title">🌫️ 诡秘人生 · 第五纪</div><div class="page">人生年鉴 · {page} / {total_pages}</div></div>
  {header_html}<div class="sep"></div><section class="timeline">{body_html}</section>
  {ending_html}
</div></body></html>"""


def build_life_html_pages(
    header_lines: list[str],
    body_lines: list[tuple[str, str]],
    ending_title: str,
    ending_text: str,
    seq_note: str,
    footer: str,
) -> list[str]:
    """生成多页人生年鉴；每页保持可读字号和有限高度。"""
    chunks = _chunk_lines(body_lines)
    total = len(chunks)
    return [
        build_life_html(
            header_lines,
            chunk,
            ending_title,
            ending_text,
            seq_note,
            footer,
            page=index,
            total_pages=total,
            show_ending=index == total,
        )
        for index, chunk in enumerate(chunks, 1)
    ]


def _talent_tags(item: dict) -> str:
    tags: list[str] = []
    for key, label in _TALENT_EFFECTS.items():
        value = item.get(key)
        if value in (None, 0, False):
            continue
        if key == "start_madness":
            tags.append(f"{label} +{value}")
        else:
            tags.append(f"{label} {float(value):+.0%}")
    if item.get("watched"):
        tags.append("被高处注视")
    biases = item.get("pathway_bias") or []
    if biases:
        tags.append("倾向 " + " / ".join(biases[:3]))
    return "".join(f'<span class="tag">{_esc(tag)}</span>' for tag in tags) or '<span class="tag">命运尚未显露</span>'


def build_choice_html_pages(
    kind: str, title: str, items: dict[str, dict], page_size: int = 8
) -> list[str]:
    """生成出身或天赋选择图卡；两种选择使用不同的视觉语言。"""
    records = list(items.values())
    pages = [records[i:i + page_size] for i in range(0, len(records), page_size)] or [[]]
    is_origin = kind == "origin"
    eyebrow = "雾都档案 · 身份卷宗" if is_origin else "灵性档案 · 命运回响"
    total = len(pages)
    output: list[str] = []
    for page, records_on_page in enumerate(pages, 1):
        card_html = []
        start = (page - 1) * page_size
        for offset, item in enumerate(records_on_page, 1):
            if is_origin:
                money = "🪙" * int(item.get("money", 0)) or "—"
                danger = "⚠" * int(item.get("danger", 0)) or "—"
                details = (
                    f'<div class="region">{_esc(item.get("region", "未知地域"))}</div>'
                    f'<div class="stats"><span>财力 {money}</span><span>风险 {danger}</span></div>'
                )
            else:
                details = f'<div class="tags">{_talent_tags(item)}</div>'
            card_html.append(
                f'''<article class="option"><div class="index">{start + offset:02d}</div>
  <div class="name">{_esc(item.get("name"))}</div>{details}
  <div class="desc">{_esc(item.get("desc"))}</div></article>'''
            )
        background = (
            "radial-gradient(circle at 8% 8%, rgba(57, 139, 184, .35), transparent 30%), radial-gradient(circle at 90% 94%, rgba(211, 150, 69, .18), transparent 36%), linear-gradient(145deg, #07121d, #112536)"
            if is_origin
            else "radial-gradient(circle at 10% 12%, rgba(198, 75, 172, .28), transparent 30%), radial-gradient(circle at 92% 86%, rgba(65, 201, 197, .22), transparent 34%), linear-gradient(145deg, #180b21, #241334)"
        )
        accent = "#8cd5ed" if is_origin else "#f0a7e7"
        option_background = (
            "linear-gradient(125deg, rgba(23, 72, 91, .68), rgba(12, 22, 36, .80))"
            if is_origin
            else "linear-gradient(125deg, rgba(83, 29, 87, .66), rgba(29, 18, 47, .84))"
        )
        output.append(f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ width: 1060px; padding: 34px; color: #e9e5dc; font-family: "Noto Sans SC", "Microsoft YaHei", serif; background: {background}; }}
  .sheet {{ padding: 34px; border-radius: 26px; border: 1px solid {accent}; background: rgba(8, 13, 21, .78); box-shadow: 0 0 68px rgba(0,0,0,.28); }}
  .head {{ display:flex; justify-content:space-between; align-items:flex-end; padding-bottom:18px; border-bottom:1px solid rgba(255,255,255,.2); }}
  .eyebrow {{ font-size:16px; letter-spacing:3px; color: {accent}; }} h1 {{ margin-top:7px; font-size:35px; letter-spacing:5px; color:#fff5d6; }} .page {{ font-size:15px; color:#c2bacd; letter-spacing:2px; }}
  .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-top:22px; }}
  .option {{ position:relative; min-height:174px; padding:19px 20px 17px 25px; overflow:hidden; border-radius:16px; border:1px solid {accent}; background: {option_background}; }}
  .index {{ position:absolute; right:17px; top:13px; font-size:16px; font-weight:700; letter-spacing:2px; color:{accent}; }} .name {{ padding-right:50px; font-size:24px; font-weight:800; color:#fff2cf; }}
  .region {{ margin-top:5px; font-size:15px; color:{accent}; }} .stats {{ display:flex; gap:18px; margin-top:12px; font-size:16px; color:#edddaa; }}
  .desc {{ margin-top:11px; padding-top:10px; border-top:1px solid rgba(255,255,255,.13); font-size:17px; line-height:1.55; color:#dedbe3; }}
  .tags {{ display:flex; flex-wrap:wrap; gap:6px; margin-top:10px; }} .tag {{ padding:3px 8px; border-radius:99px; font-size:13px; color:#f8ddf2; border:1px solid {accent}; background:rgba(190, 78, 174, .16); }}
  .tip {{ margin-top:20px; padding-top:15px; border-top:1px dashed rgba(255,255,255,.22); text-align:center; font-size:17px; letter-spacing:1px; color:#ded6c8; }}
</style></head><body><main class="sheet">
  <header class="head"><div><div class="eyebrow">{eyebrow}</div><h1>{_esc(title)}</h1></div><div class="page">第 {page} / {total} 页</div></header>
  <section class="grid">{' '.join(card_html)}</section><div class="tip">回复 <b>/诡秘 选 编号</b>、名称或 <b>随机</b> 选择命运</div>
</main></body></html>""")
    return output
