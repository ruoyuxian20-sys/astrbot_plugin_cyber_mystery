"""赛博诡秘的图文卡片渲染。"""
from __future__ import annotations

import html as _html
import math
import re
import unicodedata

from .ascensions import PATHWAY_THEMES, pathway_visual_theme
from .narrative import NarrativeView


_KEY_KINDS = {"birth", "contact", "advance"}
_WARNING_KINDS = {"crisis", "madness", "ending"}

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
    """人生年鉴固定为一张超宽三栏图，不做自动分页。"""
    del max_lines, max_chars
    return [body_lines]


def _column_major_slices(items: list[str], columns: int = 3) -> list[list[str]]:
    """按列分配卡片：第一列从上到下读完，再进入下一列。"""
    if not items:
        return []
    columns = max(1, min(columns, len(items)))
    rows = (len(items) + columns - 1) // columns
    return [items[start : start + rows] for start in range(0, len(items), rows)]


def _balanced_column_slices(
    cards: list[str], weights: list[int], columns: int = 3
) -> list[list[str]]:
    """按预估渲染高度切成连续列，保持时间顺序并减少列尾大片空白。"""
    if not cards:
        return []
    columns = max(1, min(columns, len(cards)))
    if len(cards) <= columns:
        return [[card] for card in cards] + [[] for _ in range(columns - len(cards))]
    weights = list(weights[: len(cards)]) + [1] * max(0, len(cards) - len(weights))
    prefix = [0]
    for weight in weights:
        prefix.append(prefix[-1] + max(1, int(weight)))

    best: tuple[float, tuple[int, int]] | None = None
    best_split: tuple[int, int] | None = None
    total = prefix[-1]
    for first_end in range(1, len(cards) - 1):
        for second_end in range(first_end + 1, len(cards)):
            sums = (
                prefix[first_end],
                prefix[second_end] - prefix[first_end],
                total - prefix[second_end],
            )
            spread = max(sums) - min(sums)
            score = (max(sums) + spread * 0.35, spread)
            if best is None or score < best:
                best = score
                best_split = (first_end, second_end)
    if best_split is None:
        return _column_major_slices(cards, columns)
    first_end, second_end = best_split
    return [cards[:first_end], cards[first_end:second_end], cards[second_end:]]


def _column_major_html(
    cards: list[str], columns: int = 3, weights: list[int] | None = None
) -> str:
    """生成固定列数的纵向时间线。

    ``cards`` 已按人生年龄排序。先把第一列填满、再填第二列和第三列，
    这样读者在超宽图中始终从左上向左下阅读，再进入右侧下一列。
    """
    columns = max(1, columns)
    allocated = (
        _balanced_column_slices(cards, weights, columns)
        if weights is not None and columns == 3
        else _column_major_slices(cards, columns)
    )
    # 一张人生图固定是三栏；短人生也保留空栏，避免版式在不同结果之间跳变。
    allocated.extend([[] for _ in range(max(0, columns - len(allocated)))])
    columns_html = "".join(
        f'<div class="timeline-column">{"".join(column)}</div>'
        for column in allocated
    )
    return f'<div class="timeline">{columns_html}</div>'


def _safe_emphasis(value: object, kind: object = "") -> str:
    """把展示强调限定为受控 CSS 类，避免外部值进入 class 属性。"""
    emphasis = str(value or "")
    if emphasis in {"key", "normal", "warning"}:
        return emphasis
    if str(kind) in _WARNING_KINDS:
        return "warning"
    if str(kind) in _KEY_KINDS:
        return "key"
    return "normal"


def _pathway_class(pathway_key: object) -> str:
    key = str(pathway_key or "")
    return f"pathway-{key}" if key in PATHWAY_THEMES else "pathway-unknown"


def _ascension_class(kind: object) -> str:
    value = str(kind or "")
    allowed = {
        "ascension_9": "ascension-low ascension-seq9",
        "ascension_8": "ascension-low ascension-seq8",
        "ascension_7": "ascension-low ascension-seq7",
        "ascension_6": "ascension-low ascension-seq6",
        "ascension_5": "ascension-low ascension-seq5",
        "ascension_4": "ascension-seq4",
        "ascension_3": "ascension-seq3",
        "ascension_2": "ascension-seq2",
        "ascension_1": "ascension-seq1",
        "ascension_0_god": "ascension-seq0-god",
        "ascension_0_adjacent_seq0_devour": "ascension-seq0-adjacent-devour",
        "ascension_0_source_essence_devour": "ascension-seq0-source-devour",
        "ascension_0_outer_terminus": "ascension-seq0-outer-terminus",
        "ascension_0_outer_terminus_source_essence_devour": "ascension-seq0-outer-terminus ascension-seq0-source-devour",
    }
    return allowed.get(value, "")


def _sequence_text_html(text: object, kind: object, pathway_key: object = "") -> str:
    """转义正文后高亮晋升场景中的序列名称。"""
    escaped = _esc(text)
    kind_text = str(kind or "")
    if not kind_text.startswith("ascension_"):
        return escaped
    match = re.match(r"ascension_(\d+)", kind_text)
    if not match:
        return escaped
    try:
        from . import pathways as pathways_mod

        pathway = pathways_mod.get_pathway(str(pathway_key))
        name = pathways_mod.seq_name(pathway, int(match.group(1)))
    except (KeyError, TypeError, ValueError):
        return escaped
    escaped_name = _esc(name)
    return escaped.replace(
        f"「{escaped_name}」",
        f'「<span class="sequence-name">{escaped_name}</span>」',
        1,
    )


def _sequence_note_html(text: object) -> str:
    escaped = _esc(text)
    return re.sub(
        r"【([^】]{1,48})】",
        r'<span class="sequence-name">\1</span>',
        escaped,
    )


def _estimated_block_weight(block: object) -> int:
    """估算一个正文块在单栏中的高度，用于连续分栏平衡。"""
    text = str(getattr(block, "text", "") or "")
    units = sum(
        2 if unicodedata.east_asian_width(char) in {"W", "F"} else 1
        for char in text
    )
    # 三栏单栏宽度约 450px，18px 字体每行约 23 个汉字；卡片本身还需要
    # 元信息、内边距和段落间距，因此给每块一个固定基础高度。
    line_count = max(1, math.ceil(units / 44))
    return 64 + line_count * 30


def _theme_css() -> str:
    """由受控目录生成途径主题 CSS；不接受用户文本作为 CSS 输入。"""
    rules: list[str] = []
    for key, theme in PATHWAY_THEMES.items():
        rules.append(
            f".pathway-{key} {{ --path-accent:{theme['accent']}; --path-soft:{theme['accent_soft']}; "
            f"--path-border:{theme['border']}; --path-glow:{theme['glow']}; }}"
        )
    return "\n  ".join(rules)


def _narrative_blocks_html(view: NarrativeView) -> str:
    """按 ``view.blocks`` 的原始时间顺序输出年龄段落。

    ``chapter`` 和 ``kind`` 只供叙事层内部归类，绝不参与排序或显示；否则
    同一人生会被重新拼成章节列表，破坏按年龄推进的短篇阅读感。
    """
    pathway_key = view.stats.get("pathway_key", "")
    cards = [
        f'''<article class="nblock {_pathway_class(pathway_key)} {_ascension_class(block.kind)} emphasis-{_safe_emphasis(block.emphasis, block.kind)}">
  <div class="block-meta"><span class="block-age">{_esc(block.age_label)}</span></div>
  <div class="block-text">{_sequence_text_html(block.text, block.kind, pathway_key)}</div>
</article>'''
        for block in view.blocks
    ]
    if not cards:
        cards.append(
            '<article class="nblock emphasis-normal"><div class="block-text">雾中没有留下可辨认的文字。</div></article>'
        )
    return _column_major_html(cards, weights=[_estimated_block_weight(block) for block in view.blocks])


def _legacy_blocks_html(body_lines: list[tuple[str, str]]) -> str:
    """旧接口也沿用单图三栏，但不把内部事件类型展示给用户。"""
    cards = [
        f'''<article class="nblock emphasis-{_safe_emphasis("", kind)}">
  <div class="block-text">{_esc(text)}</div>
</article>'''
        for kind, text in body_lines
    ]
    if not cards:
        cards.append(
            '<article class="nblock emphasis-normal"><div class="block-text">雾中没有留下可辨认的文字。</div></article>'
        )
    return _column_major_html(cards)


def _stats_html(
    stats: dict[str, int | float | str], seq_note: str = ""
) -> str:
    final_seq = ""
    if seq_note:
        final_seq = seq_note.removeprefix("最终序列：").strip()
    if not final_seq:
        final_seq = str(stats.get("final_seq", "凡人"))
        if final_seq.isdigit():
            final_seq = f"序列{final_seq}"
    labels = (
        ("人生", f"{stats.get('age', 0)} 岁"),
        ("最终序列", final_seq),
        ("评分", f"{stats.get('score', 0)} / 100"),
        ("疯狂峰值", str(stats.get("madness_peak", 0))),
        ("完美扮演", f"{stats.get('acting_perfect', 0)} 次"),
    )
    return "".join(
        f'<div class="stat"><span>{_esc(label)}</span><b>{_esc(value)}</b></div>'
        for label, value in labels
    )


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
    narrative: NarrativeView | None = None,
) -> str:
    """渲染单张高分辨率人生年鉴；旧参数保留以兼容外部调用。"""
    if narrative is not None:
        header_lines = list(narrative.header_lines)
        ending_title = narrative.ending_title
        ending_text = narrative.ending_text
        seq_note = narrative.seq_note
        footer = narrative.footer
        body_html = _narrative_blocks_html(narrative)
        header_html = "\n".join(
            f'<div class="hline">{_esc(line)}</div>' for line in header_lines
        )
        stats_html = _stats_html(narrative.stats, narrative.seq_note)
    else:
        header_html = "\n".join(
            f'<div class="hline">{_esc(line)}</div>' for line in header_lines
        )
        body_html = _legacy_blocks_html(body_lines)
        stats_html = ""
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    width: 1520px; padding: 22px; color: #e7dfca;
    font-family: "Noto Sans SC", "Microsoft YaHei", serif;
    background: radial-gradient(circle at 12% 10%, rgba(143, 92, 190, .24), transparent 32%),
      radial-gradient(circle at 88% 90%, rgba(33, 109, 146, .22), transparent 35%),
      linear-gradient(145deg, #080b14, #171426 52%, #08121b);
  }}
  .card {{ border: 1px solid rgba(222, 190, 108, .58); border-radius: 20px; padding: 20px 26px;
    background: rgba(8, 11, 19, .86); box-shadow: 0 0 70px rgba(126, 83, 188, .2), inset 0 0 60px rgba(35, 23, 68, .24); }}
  .top {{ display:flex; align-items:baseline; gap:12px; margin-bottom:7px; padding-bottom:8px; border-bottom:1px solid rgba(222,190,108,.28); }}
  .eyebrow {{ font-size:13px; letter-spacing:3px; color:#b7a77f; text-transform:uppercase; }}
  .title {{ font-size:28px; font-weight:800; letter-spacing:4px; color:#f0ce7c; text-shadow:0 0 14px rgba(240,206,124,.25); }}
  .identity {{ display:flex; flex-wrap:wrap; gap:5px 16px; align-items:center; min-height:24px; }}
  .hline {{ font-size:15px; line-height:1.35; color:#c7ba9b; margin:0; padding-left:8px; border-left:2px solid rgba(222,190,108,.3); }}
  .sep {{ height:1px; margin:8px 0 9px; background:linear-gradient(90deg, transparent, rgba(222,190,108,.55), transparent); }}
  .stats {{ display:grid; grid-template-columns:repeat(5, minmax(0, 1fr)); gap:6px; margin:7px 0 5px; }}
  .stat {{ padding:5px 8px; border:1px solid rgba(222,190,108,.18); border-radius:8px; background:rgba(222,190,108,.05); }}
  .stat span {{ display:block; font-size:11px; color:#a99f93; }} .stat b {{ display:block; margin-top:1px; font-size:15px; color:#f0dba0; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
  .timeline {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 11px; align-items: start; }}
  .timeline-column {{ display:flex; flex-direction:column; gap:11px; min-width:0; }}
  {_theme_css()}
  .nblock {{ min-width:0; font-size: 18px; line-height: 1.64; word-break: break-word; color: #ddd5c4; margin: 0; padding: 12px 14px 12px 16px;
    border: 1px solid rgba(222, 190, 108, .19); border-left: 4px solid rgba(222, 190, 108, .42); border-radius: 0 11px 11px 0;
    background: linear-gradient(90deg, rgba(222, 190, 108, .075), rgba(10, 14, 24, .12) 88%); }}
  .nblock.emphasis-key {{ color:#f0dfad; border-color:rgba(235, 199, 105, .48); border-left-color:#e2b95e;
    background:linear-gradient(90deg, rgba(222,190,108,.18), rgba(222,190,108,.035) 88%); box-shadow:inset 0 0 20px rgba(222,190,108,.035); }}
  .nblock.emphasis-warning {{ color:#ebbaaa; border-color:rgba(201, 105, 82, .45); border-left-color:#cf715b;
    background:linear-gradient(90deg, rgba(179,93,74,.21), rgba(85,31,41,.04) 88%); }}
  .nblock[class*="pathway-"] {{ border-left-color:var(--path-border, rgba(222,190,108,.42)); }}
  .nblock.ascension-seq4, .nblock.ascension-seq3, .nblock.ascension-seq2, .nblock.ascension-seq1 {{
    color:var(--path-accent, #f0dfad); border-color:var(--path-border, rgba(222,190,108,.48));
    background:linear-gradient(105deg, var(--path-soft, rgba(222,190,108,.16)), rgba(10,14,24,.1) 86%);
    box-shadow:inset 0 0 24px var(--path-glow, rgba(222,190,108,.08));
  }}
  .nblock.ascension-low {{
    color: #e1d9c5; border-color: rgba(178, 154, 111, .38);
    background: linear-gradient(105deg, var(--path-soft, rgba(178,154,111,.10)), rgba(10,14,24,.10) 86%);
  }}
  .nblock.ascension-low .block-age {{ color: var(--path-accent, #d8bd83); }}
  .nblock.ascension-seq9 {{ border-left-width: 5px; }}
  .nblock.ascension-seq8 {{ border-left-width: 5px; opacity: .98; }}
  .nblock.ascension-seq7 {{ border-left-width: 5px; opacity: .99; }}
  .nblock.ascension-seq6 {{ border-left-width: 5px; }}
  .nblock.ascension-seq5 {{ border-left-width: 6px; }}
  .nblock.ascension-seq4::before {{ content:"半神 · "; color:var(--path-accent, #e2b95e); font-weight:800; }}
  .nblock.ascension-seq3::before {{ content:"天使 · "; color:var(--path-accent, #e2b95e); font-weight:800; }}
  .nblock.ascension-seq2::before {{ content:"权柄 · "; color:var(--path-accent, #e2b95e); font-weight:800; }}
  .nblock.ascension-seq1::before {{ content:"唯一性 · "; color:var(--path-accent, #e2b95e); font-weight:800; }}
  .nblock.ascension-seq0-god {{ border:2px solid var(--path-border, #e2b95e); background:radial-gradient(circle at 50% 0%, var(--path-soft, rgba(222,190,108,.22)), transparent 72%); box-shadow:0 0 28px var(--path-glow, rgba(222,190,108,.2)); }}
  .nblock.ascension-seq0-adjacent-devour {{ border:2px double var(--path-border, #d6b8ff); background:linear-gradient(115deg, var(--path-soft, rgba(150,90,180,.24)), rgba(70,30,90,.18), rgba(20,15,35,.28)); box-shadow:inset 8px 0 0 rgba(210,110,220,.15), inset -8px 0 0 rgba(80,170,220,.12); }}
  .nblock.ascension-seq0-source-devour {{ border:2px solid #8d68aa; background:radial-gradient(ellipse at 50% 40%, rgba(190,70,180,.2), rgba(8,8,20,.82) 74%); box-shadow:inset 0 0 34px rgba(10,0,30,.9), 0 0 18px var(--path-glow, rgba(180,70,190,.25)); }}
  .nblock.ascension-seq0-outer-terminus {{ border:2px dashed var(--path-border, #9d82c7); background:linear-gradient(130deg, rgba(20,14,40,.82), var(--path-soft, rgba(130,70,170,.2)), rgba(5,12,25,.9)); box-shadow:0 0 22px var(--path-glow, rgba(180,70,190,.2)); }}
  .block-meta {{ display:flex; align-items:center; min-height:19px; margin-bottom:5px; font-size:14px; letter-spacing:1px; color:#c1ad76; }}
  .emphasis-warning .block-meta {{ color:#db9582; }}
  .block-age {{ font-weight:800; }}
  .block-text {{ color:inherit; white-space:pre-wrap; }}
  .sequence-name {{ display:inline-block; padding:0 5px; margin:0 1px; border-radius:5px;
    color:#fff4c9; font-weight:900; letter-spacing:.5px; border:1px solid var(--path-border, rgba(222,190,108,.72));
    background:linear-gradient(180deg, var(--path-soft, rgba(222,190,108,.24)), rgba(222,190,108,.08));
    box-shadow:0 0 10px var(--path-glow, rgba(222,190,108,.18)); }}
  .ending-strip {{ display:flex; justify-content:space-between; align-items:baseline; gap:18px; margin-top:14px; padding:7px 10px; border-top:1px solid rgba(222,190,108,.38); border-bottom:1px solid rgba(222,190,108,.32); background:rgba(222,190,108,.045); }}
  .ending {{ font-size:21px; font-weight:800; letter-spacing:2px; color:#f0ce7c; }}
  .ending-seq {{ font-size:14px; color:#c9ba9b; text-align:right; }}
  .etext {{ margin:7px 10px 0; font-size:16px; line-height:1.48; color:#e4dccd; text-align:left; }}
  .footer {{ margin-top:8px; padding-top:7px; font-size:12px; color:#a79eae; text-align:center; border-top:1px dashed rgba(222,190,108,.25); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
</style>
</head>
<body><div class="card">
  <div class="top"><div class="eyebrow">第五纪 · 人生年鉴</div><div class="title">🌫️ 诡秘人生</div></div>
  <div class="identity">{header_html}</div><div class="stats">{stats_html}</div><div class="sep"></div>{body_html}
  <div class="ending-strip"><div class="ending">【结局】{_esc(ending_title)}</div><div class="ending-seq">{_sequence_note_html(seq_note)}</div></div>
  <div class="etext">{_esc(ending_text)}</div>
  <div class="footer">{_esc(footer)}</div>
</div></body></html>"""


def build_life_html_pages(
    header_lines: list[str] | None = None,
    body_lines: list[tuple[str, str]] | None = None,
    ending_title: str = "",
    ending_text: str = "",
    seq_note: str = "",
    footer: str = "",
    *,
    narrative: NarrativeView | None = None,
) -> list[str]:
    """兼容旧接口，但始终返回单张人生图。"""
    return [
        build_life_html(
            header_lines or [],
            body_lines or [],
            ending_title,
            ending_text,
            seq_note,
            footer,
            narrative=narrative,
        )
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
    kind: str, title: str, items: dict[str, dict], page_size: int = 16
) -> list[str]:
    """生成超宽四栏选择图卡；16 个选项优先收纳到一张图。"""
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
  body {{ width: 1520px; padding: 28px; color: #e9e5dc; font-family: "Noto Sans SC", "Microsoft YaHei", serif; background: {background}; }}
  .sheet {{ padding: 27px; border-radius: 24px; border: 1px solid {accent}; background: rgba(8, 13, 21, .78); box-shadow: 0 0 68px rgba(0,0,0,.28); }}
  .head {{ display:flex; justify-content:space-between; align-items:flex-end; padding-bottom:15px; border-bottom:1px solid rgba(255,255,255,.2); }}
  .eyebrow {{ font-size:15px; letter-spacing:3px; color: {accent}; }} h1 {{ margin-top:5px; font-size:32px; letter-spacing:4px; color:#fff5d6; }} .page {{ font-size:15px; color:#c2bacd; letter-spacing:2px; }}
  .grid {{ display:grid; grid-template-columns:repeat(4, minmax(0, 1fr)); gap:12px; margin-top:18px; }}
  .option {{ position:relative; min-height:157px; padding:15px 15px 14px 17px; overflow:hidden; border-radius:14px; border:1px solid {accent}; background: {option_background}; }}
  .index {{ position:absolute; right:13px; top:10px; font-size:14px; font-weight:700; letter-spacing:2px; color:{accent}; }} .name {{ padding-right:42px; font-size:20px; font-weight:800; color:#fff2cf; }}
  .region {{ margin-top:4px; font-size:13px; color:{accent}; }} .stats {{ display:flex; gap:11px; margin-top:8px; font-size:14px; color:#edddaa; }}
  .desc {{ margin-top:8px; padding-top:8px; border-top:1px solid rgba(255,255,255,.13); font-size:15px; line-height:1.5; color:#dedbe3; }}
  .tags {{ display:flex; flex-wrap:wrap; gap:4px; margin-top:8px; }} .tag {{ padding:2px 6px; border-radius:99px; font-size:11.5px; color:#f8ddf2; border:1px solid {accent}; background:rgba(190, 78, 174, .16); }}
  .tip {{ margin-top:15px; padding-top:12px; border-top:1px dashed rgba(255,255,255,.22); text-align:center; font-size:16px; letter-spacing:1px; color:#ded6c8; }}
</style></head><body><main class="sheet">
  <header class="head"><div><div class="eyebrow">{eyebrow}</div><h1>{_esc(title)}</h1></div><div class="page">第 {page} / {total} 页</div></header>
  <section class="grid">{' '.join(card_html)}</section><div class="tip">回复 <b>/诡秘 选 编号</b>、名称或 <b>随机</b> 选择命运</div>
</main></body></html>""")
    return output
