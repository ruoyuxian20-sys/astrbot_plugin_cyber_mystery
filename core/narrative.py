"""人生结果的叙事整理层。

模拟引擎保留完整、可复现的原始事件轨迹；本模块只负责把它整理成适合
群聊阅读的章节化摘要，供纯文本和图卡共同使用。
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from . import events as events_mod
from . import pathways as pathways_mod


CHILDHOOD = "童年与征兆"
CONTACT = "非凡接触"
ASCENSION = "序列攀升"
CONSEQUENCE = "代价与终局"


@dataclass(frozen=True)
class NarrativeBlock:
    """一块可直接展示的章节正文。"""

    chapter: str
    kind: str
    age_label: str
    text: str
    emphasis: str  # key / normal / warning


@dataclass(frozen=True)
class NarrativeView:
    """纯文本和 HTML 渲染器共享的完整展示模型。"""

    header_lines: tuple[str, ...]
    blocks: tuple[NarrativeBlock, ...]
    stats: dict[str, int | float | str]
    ending_title: str
    ending_text: str
    seq_note: str
    footer: str


_SPACE_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"([，。！？；：])\1+")
_KEY_KINDS = {"birth", "contact", "advance", "crisis", "madness", "ending"}


def _clean_text(text: object, limit: int) -> str:
    value = str(text or "").replace("\r", " ").replace("\n", "；")
    value = _SPACE_RE.sub(" ", value).strip()
    value = _PUNCT_RE.sub(r"\1", value)
    if len(value) <= limit:
        return value
    return value[: max(1, limit - 1)].rstrip(" ，。；：") + "…"


def _age_label(ages: Iterable[int | None]) -> str:
    values = sorted({int(age) for age in ages if age is not None})
    if not values:
        return ""
    if len(values) == 1:
        return f"{values[0]}岁"
    return f"{values[0]}–{values[-1]}岁"


def _chapter(kind: str, text: str, contact_seen: bool) -> str:
    if kind in {"birth", "youth"}:
        return CHILDHOOD
    if kind == "contact":
        return CONTACT
    if kind == "advance":
        if any(word in text for word in ("饮下", "踏入", "接触", "魔药入喉")):
            return CONTACT
        if any(word in text for word in ("登临", "序列0", "旧日", "最后的仪式")):
            return CONSEQUENCE
        return ASCENSION
    if kind in {"crisis", "madness", "ending"}:
        return CONSEQUENCE
    if kind == "meta" and not contact_seen:
        return CONTACT
    return ASCENSION if contact_seen else CHILDHOOD


def _emphasis(kind: str) -> str:
    if kind in {"crisis", "madness", "ending"}:
        return "warning"
    if kind in {"birth", "contact", "advance"}:
        return "key"
    return "normal"


def _merge_texts(texts: list[str], limit: int, omitted: int = 0) -> str:
    cleaned = [_clean_text(text, limit) for text in texts if text]
    if not cleaned:
        return ""
    result = "；".join(cleaned[:2])
    extra = max(0, len(cleaned) - 2) + omitted
    if extra:
        result += f"（另有{extra}段经历）"
    return _clean_text(result, limit)


def _make_block(
    chapter: str,
    kind: str,
    ages: list[int | None],
    texts: list[str],
    emphasis: str | None = None,
    omitted: int = 0,
) -> NarrativeBlock:
    limit = 220 if (emphasis or _emphasis(kind)) != "normal" else 140
    return NarrativeBlock(
        chapter=chapter,
        kind=kind,
        age_label=_age_label(ages),
        text=_merge_texts(texts, limit, omitted),
        emphasis=emphasis or _emphasis(kind),
    )


def _compact_blocks(blocks: list[NarrativeBlock]) -> list[NarrativeBlock]:
    """先压到约 24 块，极端情况下最多保留约 30 块，不丢关键块。"""

    def merge_pair(left: NarrativeBlock, right: NarrativeBlock) -> NarrativeBlock:
        ages: list[int] = []
        for label in (left.age_label, right.age_label):
            ages.extend(int(x) for x in re.findall(r"\d+", label))
        return _make_block(
            left.chapter,
            "summary",
            ages,
            [left.text, right.text],
            "normal",
        )

    def merge_at(left_index: int, right_index: int) -> None:
        left = blocks[left_index]
        right = blocks[right_index]
        blocks[left_index] = merge_pair(left, right)
        del blocks[right_index]

    def merge_adjacent(target: int) -> None:
        while len(blocks) > target:
            pair_index = next(
                (
                    i
                    for i in range(len(blocks) - 1)
                    if blocks[i].kind != "acting"
                    and blocks[i + 1].kind != "acting"
                    and blocks[i].emphasis == blocks[i + 1].emphasis == "normal"
                    and blocks[i].chapter == blocks[i + 1].chapter
                ),
                None,
            )
            if pair_index is None:
                pair_index = next(
                    (
                        i
                        for i in range(len(blocks) - 1)
                        if blocks[i].kind != "acting"
                        and blocks[i + 1].kind != "acting"
                        and blocks[i].emphasis == blocks[i + 1].emphasis == "normal"
                    ),
                    None,
                )
            if pair_index is None:
                return
            merge_at(pair_index, pair_index + 1)

    def merge_separated_normals(target: int) -> None:
        """关键块过密时，合并同章节的远距离普通块，关键块原样保留。"""
        while len(blocks) > target:
            normal_indices = [
                i
                for i, block in enumerate(blocks)
                if block.emphasis == "normal" and block.kind != "acting"
            ]
            if len(normal_indices) < 2:
                return
            pair: tuple[int, int] | None = None
            for left, right in zip(normal_indices, normal_indices[1:]):
                if blocks[left].chapter == blocks[right].chapter:
                    pair = (left, right)
                    break
            if pair is None:
                pair = (normal_indices[0], normal_indices[1])
            merge_at(*pair)

    merge_adjacent(24)
    merge_separated_normals(30)
    return blocks


def _seq_note(result: dict, pathway: dict | None) -> str:
    category = result.get("category")
    seq = result.get("final_seq")
    if category == "eldritch":
        return "最终序列：常理之外（旧日）"
    if category == "god" and pathway:
        return f"最终序列：0 · {pathways_mod.seq0_name(pathway)}（登神）"
    if seq is None:
        return "最终序列：无（凡人）"
    note = f"最终序列：序列{seq}"
    if pathway and pathway.get("sequences") and seq in pathway["sequences"]:
        note += f" · {pathway['sequences'][seq]}"
    return note


def summarize_life(result: dict, player: str = "") -> NarrativeView:
    """将完整模拟结果整理成稳定、可读且不改变原结果的展示模型。"""
    origin = events_mod.ORIGINS[result["origin_key"]]
    talent = events_mod.TALENTS[result["talent_key"]]
    pathway = pathways_mod.get_pathway(result["pathway_key"]) if result.get("pathway_key") else None
    header: list[str] = [f"【出身】{origin['name']}", f"【天赋】{talent['name']}——{talent['desc']}"]
    if pathway:
        header.append(f"【途径】{pathway['name']}（{pathway.get('faction', '')}）")

    blocks: list[NarrativeBlock] = []
    pending_kind: str | None = None
    pending_chapter: str | None = None
    pending_ages: list[int | None] = []
    pending_texts: list[str] = []
    contact_seen = False
    acting_counts = {"得法": 0, "尚可": 0, "失当": 0}
    acting_ages: list[int | None] = []
    acting_texts: list[str] = []
    acting_insert_at: int | None = None

    def flush_pending() -> None:
        nonlocal pending_kind, pending_chapter, pending_ages, pending_texts
        if pending_kind and pending_chapter and pending_texts:
            blocks.append(
                _make_block(
                    pending_chapter,
                    pending_kind,
                    pending_ages,
                    pending_texts,
                    "normal",
                    max(0, len(pending_texts) - 2),
                )
            )
        pending_kind = None
        pending_chapter = None
        pending_ages = []
        pending_texts = []

    for line in result.get("lines", []):
        kind = str(line.get("kind", "meta"))
        text = _clean_text(line.get("text", ""), 220)
        age = line.get("age")
        if kind == "contact":
            contact_seen = True
        chapter = _chapter(kind, text, contact_seen)
        if kind == "acting":
            if "得法" in text:
                acting_counts["得法"] += 1
            elif "尚可" in text:
                acting_counts["尚可"] += 1
            else:
                acting_counts["失当"] += 1
            flush_pending()
            if acting_insert_at is None:
                acting_insert_at = len(blocks)
            acting_ages.append(age)
            acting_texts.append(text)
            continue

        is_key = kind in _KEY_KINDS
        if not is_key and kind in {"youth", "climb", "meta"}:
            if pending_kind == "summary" and pending_chapter == chapter:
                pending_ages.append(age)
                pending_texts.append(text)
            else:
                flush_pending()
                pending_kind, pending_chapter = "summary", chapter
                pending_ages, pending_texts = [age], [text]
            continue

        flush_pending()
        if (
            kind in {"crisis", "madness"}
            and blocks
            and blocks[-1].emphasis == "warning"
            and blocks[-1].chapter == chapter
            and blocks[-1].age_label == _age_label([age])
        ):
            previous = blocks[-1]
            blocks[-1] = _make_block(
                chapter,
                "crisis",
                [age],
                [previous.text, text],
                "warning",
            )
        else:
            blocks.append(_make_block(chapter, kind, [age], [text]))

    flush_pending()

    # 全人生的扮演记录统一显示为一个可读的统计摘要，同时保留代表性文案。
    if acting_texts:
        counts = "、".join(
            f"{key}{value}次" for key, value in acting_counts.items() if value
        )
        acting_block = _make_block(
            ASCENSION,
            "acting",
            acting_ages,
            [f"扮演记录：{counts}"] + acting_texts[:2],
            "normal",
        )
        blocks.insert(acting_insert_at if acting_insert_at is not None else len(blocks), acting_block)

    blocks = _compact_blocks(blocks)
    category = str(result.get("category", ""))
    stats: dict[str, int | float | str] = {
        "score": int(result.get("score", 0)),
        "age": int(result.get("age", 0)),
        "madness_peak": int(result.get("madness_peak", 0)),
        "acting_perfect": int(result.get("acting_perfect", 0)),
        "category": category,
        "final_seq": "凡人" if result.get("final_seq") is None else str(result.get("final_seq")),
        "block_count": len(blocks),
    }
    if result.get("seed") is not None:
        stats["seed"] = str(result["seed"])
    stats["title"] = str(result.get("title", ""))
    if player:
        stats["player"] = player

    footer = f"人生评分：{stats['score']} / 100 · 称号「{result.get('title', '')}」"
    if player:
        footer += f" · {player}"
    if result.get("seed") is not None:
        footer += f" · 种子 {result['seed']}"

    return NarrativeView(
        header_lines=tuple(header),
        blocks=tuple(blocks),
        stats=stats,
        ending_title=str(result.get("ending_title", "")),
        ending_text=_clean_text(result.get("ending_text", ""), 280),
        seq_note=_seq_note(result, pathway),
        footer=footer,
    )


def format_narrative(view: NarrativeView) -> str:
    """把叙事模型渲染为纯文本；与图卡共用相同 blocks。"""
    out = ["🌫️ 诡秘人生 · 第五纪", ""]
    out.extend(view.header_lines)
    out.append("")
    out.append(
        f"【人生摘要】活到 {view.stats.get('age', 0)} 岁 · "
        f"评分 {view.stats.get('score', 0)} · 疯狂峰值 {view.stats.get('madness_peak', 0)} · "
        f"完美扮演 {view.stats.get('acting_perfect', 0)} 次"
    )
    current = None
    for block in view.blocks:
        if block.chapter != current:
            current = block.chapter
            out.extend(["", f"◆ {current}"])
        prefix = f"{block.age_label} " if block.age_label else ""
        out.append(f"{prefix}{block.text}")
    out.extend(["", f"【结局】{view.ending_title}", view.ending_text, view.seq_note, view.footer])
    return "\n".join(out)
