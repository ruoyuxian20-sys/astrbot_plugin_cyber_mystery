"""人生结果的叙事整理层。

模拟引擎负责留下完整、可复现的事件轨迹。本模块不参与随机过程，只把
``result["lines"]`` 编译成按年龄推进的第二人称短篇，供纯文本和图卡共享。
原始轨迹始终保留在结果中；这里的取舍只发生在展示层。
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from . import events as events_mod
from . import pathways as pathways_mod


# ``chapter`` 仍保留在展示模型里，供渲染器决定色彩和层次；它不是正文的一部分。
CHILDHOOD = "童年与征兆"
CONTACT = "非凡接触"
ASCENSION = "序列攀升"
CONSEQUENCE = "代价与终局"


@dataclass(frozen=True)
class NarrativeBlock:
    """一段可直接展示的、按年龄阅读的叙事正文。"""

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


_SPACE_RE = re.compile(r"[ \t\f\v\u3000]+")
_LINEBREAK_RE = re.compile(r"(?:\r\n|\r|\n)+")
_PUNCT_RE = re.compile(r"([，。！？；：])\1+")
_DEBUG_FRAGMENT_RE = re.compile(
    r"(?:（?\s*另有\s*\d+\s*段经历\s*）?|\b(?:summary|advance)\b)",
    re.IGNORECASE,
)
_ACTING_RE = re.compile(r"^\s*扮演(?P<result>得法|尚可|失当)\s*[：:]\s*(?P<body>.+?)\s*$")

_WARNING_KINDS = {"crisis", "madness", "ending"}
_HARD_ANCHOR_KINDS = {
    "birth",
    "contact",
    "advance",
    "crisis",
    "madness",
    "ending",
    "meta",
    # 引擎中的 meta 都是结构性转折：二次接触、外神配方、高处注视、退隐等。
    "meta",
}
_SOFT_EVENT_KINDS = {"acting", "climb", "youth"}
_KIND_PRIORITY = {
    "ending": 90,
    "madness": 80,
    "crisis": 70,
    "advance": 60,
    "contact": 50,
    "birth": 45,
    "acting": 40,
    "meta": 35,
    "climb": 20,
    "youth": 10,
}
_NARRATIVE_WORDS = {
    "梦": 2,
    "封印": 3,
    "注视": 3,
    "星空": 3,
    "污染": 3,
    "仪式": 3,
    "审判": 3,
    "组织": 2,
    "低语": 2,
    "灰雾": 3,
    "命运": 2,
    "教会": 2,
    "灵界": 2,
    "神话": 3,
    "历史": 2,
    "怪物": 2,
    "镜": 2,
    "影子": 2,
    "门": 1,
    "血": 1,
    "星": 1,
}
_HIGH_META_WORDS = ("星空", "高处", "注视", "灰雾", "旧日", "心跳")
_RAW_TRANSITION_PREFIXES = (
    "然而",
    "但",
    "可是",
    "可",
    "不过",
    "直到",
    "随后",
    "不久后",
    "多年以后",
    "多年后",
    "在那之后",
    "接下来",
    "到最后",
    "真正的变化",
    "魔药入喉",
    "仪式没有停下",
    "登神的仪式",
    "岁月与旧伤",
    "非凡世界的大门",
    "命运第二次敲响",
)


@dataclass(frozen=True)
class _Event:
    """清洗后的原始事件；``index`` 用于稳定地维持模拟顺序。"""

    index: int
    kind: str
    age: int | None
    text: str
    pathway_key: str = ""
    sequence: int | None = None
    ascension_mode: str = ""
    visual_theme: str = ""


@dataclass(frozen=True)
class _AgeGroup:
    """同一年龄的原始事件，顺序与引擎输出完全一致。"""

    index: int
    age: int | None
    events: tuple[_Event, ...]


@dataclass(frozen=True)
class _TimelineUnit:
    """最终会渲染成一个段落的时间线单元。"""

    index: int
    ages: tuple[int | None, ...]
    events: tuple[_Event, ...]
    is_anchor: bool


def _clean_text(text: object, limit: int | None = None) -> str:
    """清理展示用文本，保留句子边界而不把换行压成分号。"""
    value = str(text or "")
    value = _LINEBREAK_RE.sub("。", value)
    # 旧版本把多条经历串成分号；新正文统一以句号切开，避免日志式节奏。
    value = value.replace("；", "。").replace(";", "。")
    value = _SPACE_RE.sub(" ", value)
    value = _DEBUG_FRAGMENT_RE.sub("", value)
    value = _PUNCT_RE.sub(r"\1", value)
    value = re.sub(r"\s*([，。！？：])\s*", r"\1", value).strip()
    value = re.sub(r"(?:。\s*){2,}", "。", value)
    if limit is not None and len(value) > limit:
        return value[: max(1, limit - 1)].rstrip(" ，。；：") + "…"
    return value


def _sentence(text: str) -> str:
    """让片段成为可平滑拼接的句子。"""
    value = _clean_text(text)
    if not value:
        return ""
    if value[-1] not in "。！？…":
        value += "。"
    return value


def _coerce_age(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _age_label(ages: Iterable[int | None]) -> str:
    """统一输出模拟器特征明显的年龄节。"""
    values = sorted({age for age in ages if age is not None})
    if not values:
        return ""
    if len(values) == 1:
        return f"【{values[0]}岁】"
    return f"【{values[0]}–{values[-1]}岁】"


def _acting_result(event: _Event) -> tuple[str | None, str]:
    """去掉“扮演得法：”这类面板标签，保留它实际描述的经历。"""
    match = _ACTING_RE.match(event.text)
    if not match:
        return None, _sentence(event.text)
    result = match.group("result")
    body = match.group("body")
    # 扮演文案经常重复同一组机制性表达；压缩为更像小说的短句，同时不改变
    # “成功/勉强/失当”以及疯狂、消化、角色与自我等事实。
    replacements = (
        ("你与这一序列的真名产生了共鸣，疯狂如潮水般退去", "你与序列真名共鸣，疯狂退潮"),
        ("你在角色与自我之间找到了完美的平衡点", "你在角色与自我间找到平衡"),
        ("你终于让角色成为工具，而非让自己成为角色的囚徒", "你终于让角色成为工具，而非角色的囚徒"),
        ("你在一瞬间理解了序列的本质，魔药温顺得像驯服的星火", "你看穿序列本质，魔药归于温顺"),
        ("你彻底理解了这一序列的真义，魔药温顺地融入血脉", "你悟透序列真义，魔药融入血脉"),
        ("所有细节都在正确的位置上，魔药安静地承认了你", "细节归位，魔药承认了你"),
        ("魔药的力量被完全消化，你从未如此清醒", "魔药完全消化，你前所未有地清醒"),
        ("魔药缓慢消化，但那股躁动仍潜伏在血管深处", "魔药缓慢消化，躁动仍伏在血管深处"),
        ("魔药仍在深处翻涌，你靠着惯性走完了今天", "魔药翻涌，你勉强走完今天"),
        ("消化在推进，只是偶尔你会忘记自己原本的性格", "消化推进，你偶尔忘了原本的性格"),
        ("你维持着微妙的平衡，如履薄冰但尚在正轨", "你维持微妙平衡，仍在正轨"),
        ("你记得该做什么，只是偶尔会怀疑做事的人究竟是谁", "你记得该做什么，却偶尔怀疑自己是谁"),
    )
    for old, new in replacements:
        body = body.replace(old, new)
    return result, _sentence(body)


def _event_limit(event: _Event) -> int:
    """为不同叙事权重设置展示长度，保留事实开头并避免卡片被长句撑高。"""
    if event.kind == "birth":
        return 90
    if event.kind in {"youth", "climb"}:
        return 92
    if event.kind == "contact":
        return 132
    if event.kind == "advance":
        if event.sequence is not None and event.sequence == 0:
            return 460
        if event.sequence is not None and event.sequence <= 4:
            return 340
        if event.sequence is not None and event.sequence <= 9:
            # 低序列也保留完整的途径经历，避免人生前半程只剩一句升级日志。
            return 240
        # 晋升与登神文案承载结局事实，给仪式高潮更多空间；普通晋升保持短促。
        return 165 if any(word in event.text for word in ("仪式", "源质", "圣者", "旧日", "常理之外")) else 82
    if event.kind == "acting":
        return 96
    if event.kind in {"crisis", "madness"}:
        return 98
    if event.kind == "ending":
        return 150
    return 112


def _event_sentence(event: _Event) -> str:
    if event.kind == "acting":
        _, text = _acting_result(event)
        return _sentence(_clean_text(text, _event_limit(event)))
    return _sentence(_clean_text(event.text, _event_limit(event)))


def _normal_value(event: _Event) -> int:
    """为普通素材评分，优先选择能形成伏笔、因果或途径质感的经历。"""
    score = 1 if event.kind == "climb" else 0
    for word, weight in _NARRATIVE_WORDS.items():
        if word in event.text:
            score += weight
    if any(word in event.text for word in ("第一次", "终于", "从此", "代价", "另一")):
        score += 1
    return score


def _group_events(lines: object) -> list[_AgeGroup]:
    """按原始顺序和年龄聚合；不会排序或改写模拟轨迹。"""
    groups: list[_AgeGroup] = []
    current_age: int | None | object = object()
    current_index = 0
    current_events: list[_Event] = []

    if isinstance(lines, (str, bytes)):
        source = []
    else:
        try:
            source = iter(lines)  # type: ignore[arg-type]
        except TypeError:
            source = iter(())

    for index, raw_line in enumerate(source):
        if not isinstance(raw_line, dict):
            continue
        text = _clean_text(raw_line.get("text", ""))
        if not text:
            continue
        age = _coerce_age(raw_line.get("age"))
        sequence = raw_line.get("sequence")
        try:
            sequence = int(sequence) if sequence is not None else None
        except (TypeError, ValueError):
            sequence = None
        event = _Event(
            index,
            str(raw_line.get("kind", "meta") or "meta"),
            age,
            text,
            str(raw_line.get("pathway_key", "") or ""),
            sequence,
            str(raw_line.get("ascension_mode", "") or ""),
            str(raw_line.get("visual_theme", "") or ""),
        )
        if current_events and age != current_age:
            groups.append(_AgeGroup(current_index, current_age, tuple(current_events)))
            current_events = []
        if not current_events:
            current_age = age
            current_index = index
        current_events.append(event)

    if current_events:
        groups.append(_AgeGroup(current_index, current_age, tuple(current_events)))
    return groups


def _is_hard_anchor(event: _Event) -> bool:
    return event.kind in _HARD_ANCHOR_KINDS or any(
        word in event.text for word in _HIGH_META_WORDS
    )


def _is_anchor(event: _Event) -> bool:
    """兼容旧调用名：硬锚点决定间隔边界，扮演属于可选普通素材。"""
    return _is_hard_anchor(event)


def _soft_priority(event: _Event) -> int:
    """为晋升间隔内的普通事件评分；分数只用于选择，不改变显示顺序。"""
    score = _normal_value(event)
    if event.kind == "acting":
        result, _ = _acting_result(event)
        score += {"失当": 7, "得法": 5, "尚可": 3}.get(result or "", 2)
    elif event.kind == "climb":
        score += 2
    elif event.kind == "youth":
        score += 1
    return score


def _select_interval_events(groups: list[_AgeGroup], limit: int = 4) -> list[_Event]:
    """从一个晋升间隔中择优选取最多 ``limit`` 条普通事件。

    选择阶段保证尽量覆盖扮演、途径经历和成长素材；最终仍按原始事件索引
    排序，因此正文不会出现“先总结、后倒叙”的问题。
    """
    candidates = [
        event
        for group in groups
        for event in group.events
        if not _is_hard_anchor(event) and event.kind in _SOFT_EVENT_KINDS
    ]
    if not candidates:
        return []

    selected: list[_Event] = []
    # 先保证不同叙事功能尽量都有代表：扮演、途径/能力、成长。
    for kind in ("acting", "climb", "youth"):
        pool = [event for event in candidates if event.kind == kind]
        if pool:
            selected.append(max(pool, key=lambda event: (_soft_priority(event), -event.index)))
    selected_indexes = {event.index for event in selected}
    remaining = sorted(
        (event for event in candidates if event.index not in selected_indexes),
        key=lambda event: (_soft_priority(event), -event.index),
        reverse=True,
    )
    for event in remaining:
        if len(selected) >= limit:
            break
        selected.append(event)
    return sorted(selected[:limit], key=lambda event: event.index)


def _timeline_units(groups: list[_AgeGroup]) -> list[_TimelineUnit]:
    """保留硬锚点，并把晋升间隔中的普通素材逐条展开为独立年龄块。"""
    units: list[_TimelineUnit] = []
    ordinary_buffer: list[_AgeGroup] = []

    def flush_ordinary() -> None:
        nonlocal ordinary_buffer
        for event in _select_interval_events(ordinary_buffer, limit=4):
            units.append(
                _TimelineUnit(
                    index=event.index,
                    ages=(event.age,),
                    events=(event,),
                    is_anchor=False,
                )
            )
        ordinary_buffer = []

    for group in groups:
        hard_events = [event for event in group.events if _is_hard_anchor(event)]
        soft_events = [event for event in group.events if not _is_hard_anchor(event)]
        if hard_events:
            flush_ordinary()
            # 同一年龄的扮演/途径经历也独立保留，并按原始索引与晋升事件交错。
            selected_soft = _select_interval_events(
                [_AgeGroup(group.index, group.age, tuple(soft_events))], limit=4
            )
            for event in sorted((*hard_events, *selected_soft), key=lambda item: item.index):
                units.append(
                    _TimelineUnit(
                        index=event.index,
                        ages=(event.age,),
                        events=(event,),
                        is_anchor=_is_hard_anchor(event),
                    )
                )
        else:
            ordinary_buffer.append(group)
    flush_ordinary()
    return units


def _dominant_kind(events: Iterable[_Event]) -> str:
    values = tuple(events)
    if not values:
        return "meta"
    ascension_events = [
        event
        for event in values
        if event.kind == "advance"
        and event.sequence is not None
        and 0 <= event.sequence <= 9
    ]
    ascension = ascension_events[-1] if ascension_events else None
    if ascension is not None:
        if ascension.sequence == 0:
            modes = [
                event.ascension_mode
                for event in ascension_events
                if event.ascension_mode
            ]
            if len(set(modes)) > 1:
                normalized = ["god" if mode == "standard_god" else mode for mode in dict.fromkeys(modes)]
                return "ascension_0_" + "_".join(normalized)
            mode = (
                "god"
                if ascension.ascension_mode == "standard_god"
                else ascension.ascension_mode
            )
            return f"ascension_0_{mode}"
        return f"ascension_{ascension.sequence}"
    return max(values, key=lambda event: (_KIND_PRIORITY.get(event.kind, 0), -event.index)).kind


def _emphasis(events: Iterable[_Event]) -> str:
    values = tuple(events)
    if any(event.kind in _WARNING_KINDS for event in values):
        return "warning"
    if any(event.kind in {"birth", "contact", "advance", "meta"} for event in values):
        return "key"
    return "normal"


def _chapter(events: Iterable[_Event], contact_seen: bool) -> str:
    values = tuple(events)
    kinds = {event.kind for event in values}
    texts = "".join(event.text for event in values)
    if kinds & _WARNING_KINDS:
        return CONSEQUENCE
    if "birth" in kinds or ("youth" in kinds and not contact_seen):
        return CHILDHOOD
    if "contact" in kinds or ("meta" in kinds and not contact_seen):
        return CONTACT
    if any(word in texts for word in ("登神", "旧日", "急流勇退", "常理之外")):
        return CONSEQUENCE
    return ASCENSION if contact_seen else CHILDHOOD


def _take_connector(
    state: dict[str, object], key: str, variants: tuple[str, ...]
) -> str:
    """按出现次数轮换连接词，不调用随机数，且同一种子始终得到同样文本。"""
    counters = state.setdefault("connector_counts", {})
    if not isinstance(counters, dict):
        counters = {}
        state["connector_counts"] = counters
    count = int(counters.get(key, 0))
    counters[key] = count + 1
    previous = str(state.get("last_connector", ""))
    used_in_unit = state.get("unit_connectors", set())
    if not isinstance(used_in_unit, set):
        used_in_unit = set()
        state["unit_connectors"] = used_in_unit
    # 不同类别可能共享同一个短语（例如“危机的余波仍在”）。全局记住上一
    # 个连接词，避免同一年龄段出现“余波仍在……余波仍在”的机械回声。
    for offset in range(len(variants)):
        candidate = variants[(count + offset) % len(variants)]
        if (candidate != previous and candidate not in used_in_unit) or len(variants) == 1:
            state["last_connector"] = candidate
            used_in_unit.add(candidate)
            if offset:
                counters[key] = count + offset + 1
            return candidate
    state["last_connector"] = variants[count % len(variants)]
    used_in_unit.add(state["last_connector"])
    return state["last_connector"]


def _explicit_transition(text: str) -> bool:
    """原始文案已经包含转折/升级时，不再套一层同义连接词。"""
    return text.startswith(_RAW_TRANSITION_PREFIXES + (
        "你完成了最后的仪式",
        "你抵达了外神途径",
        "你吞下相邻途径",
    ))


def _acting_connector(event: _Event, state: dict[str, object]) -> str:
    result, _ = _acting_result(event)
    if result == "得法":
        return _take_connector(
            state,
            "acting_good",
            ("经过试探，", "你摸到了相处的尺度，", "这一次，", "磨合之后，"),
        )
    if result == "尚可":
        return _take_connector(
            state,
            "acting_ok",
            ("你勉强守住边界，", "你继续与它周旋，", "你维持着摇晃的平衡，", "表面的平静尚未破碎，"),
        )
    return _take_connector(
        state,
        "acting_bad",
        ("但代价很快显现：", "边界开始松动：", "然而，魔药留下了裂缝：", "你听见了代价的回声："),
    )


def _crisis_connector(event: _Event, state: dict[str, object]) -> str:
    warning_count = int(state.get("warning_count", 0))
    if warning_count == 0:
        return "然而，"
    return _take_connector(
        state,
        "warning_bridge",
        ("余波未平，", "裂缝沿着魔药蔓延，", "危险再次逼近：", "理智又被推向边缘："),
    )


def _advance_connector(
    previous: _Event | None, current: _Event, state: dict[str, object]
) -> str:
    # 高序列文案自身已经带有“魔药入喉 / 仪式没有停下”等承接语，直接相连
    # 比“随后，仪式没有停下”更像短篇，而不是事件清单。
    if previous is not None and previous.kind == "advance" and _explicit_transition(current.text):
        return ""
    if previous is not None and previous.kind == "contact":
        return "由此，"
    if previous is not None and previous.kind == "advance":
        return _take_connector(
            state,
            "advance_chain",
            ("紧接着，", "下一道门打开，", "晋升没有停下，"),
        )
    if _explicit_transition(current.text):
        return ""
    return _take_connector(
        state,
        "advance",
        ("随后，", "再进一步，", "力量继续攀升，", "又一道门打开，"),
    )


def _first_intro(unit: _TimelineUnit, state: dict[str, object]) -> str:
    """确定性连接句：只表达时间、因果和情绪，不捏造事件事实。"""
    first = unit.events[0]
    if first.kind == "birth":
        return ""
    if first.kind == "contact":
        return "直到这一年，"
    if first.kind == "ending":
        return "到最后，"
    if first.kind == "crisis":
        return _crisis_connector(first, state)
    if first.kind == "madness":
        return _take_connector(
            state,
            "madness",
            ("但力量的另一面很快显现：", "可失控的征兆已逼近：", "然而，理智开始出现裂缝："),
        )
    if first.kind == "advance":
        return _advance_connector(None, first, state)
    if first.kind == "acting":
        return _acting_connector(first, state)
    if first.kind == "meta":
        if "非凡世界的大门" in first.text:
            return "你等了很久，"
        if "急流勇退" in first.text:
            return "到最后，"
        if any(word in first.text for word in _HIGH_META_WORDS):
            return _take_connector(
                state,
                "high_meta",
                ("与此同时，", "就在这时，", "远处的注视也随之落下，"),
            )
        return _take_connector(state, "meta", ("多年以后，", "后来，", "在那之后，"))
    if state.get("has_power") and state.get("warning_seen"):
        if not state.get("warning_bridge_used"):
            state["warning_bridge_used"] = True
            return "第一次失败让你明白，代价已经开始。"
        return _take_connector(
            state,
            "after_warning",
            ("你带着那道裂缝向前，", "风暴尚未远去，你继续前行，", "伤口尚未愈合，", "那场动荡仍未放过你，"),
        )
    if state.get("has_power"):
        return _take_connector(
            state,
            "powered_ordinary",
            ("接下来的几年里，", "力量刚刚苏醒，你仍在学习如何使用它，", "在最初的磨合中，", "你沿着这条新道路继续前行，"),
        )
    return _take_connector(state, "ordinary", ("此后的几年里，", "接下来的岁月里，", "随后几年，"))


def _bridge(previous: _Event, current: _Event, state: dict[str, object]) -> str:
    """把同龄事件从并列日志改写为有因果的句流。"""
    if current.kind == "contact":
        return "直到这一天，"
    if current.kind == "advance":
        return _advance_connector(previous, current, state)
    if current.kind == "crisis":
        return _crisis_connector(current, state)
    if current.kind == "madness":
        return _take_connector(
            state,
            "madness",
            ("可失控的征兆很快逼近：", "但理智的裂缝开始扩大：", "然而，梦境已经不再属于你："),
        )
    if current.kind == "ending":
        return "到最后，"
    if current.kind == "acting":
        return _acting_connector(current, state)
    if current.kind == "meta":
        if "急流勇退" in current.text:
            return "到最后，"
        return _take_connector(
            state,
            "meta_bridge",
            ("与此同时，", "而在更高处，", "就在这时，"),
        )
    if int(state.get("warning_count", 0)):
        return _take_connector(
            state,
            "ordinary_bridge",
            ("后来，", "阴影仍在身后，", "在那之后，"),
        )
    return _take_connector(state, "ordinary_bridge", ("后来，", "再往后，", "与此同时，"))


def _prepend(prefix: str, text: str) -> str:
    if not prefix:
        return text
    # 部分事件原文已经带有相同的主语/转折（例如“你维持着……”或
    # “余波未平……”），避免连接器与事实句首重复，保持自然呼吸。
    prefix_core = prefix.rstrip("，：。 ")
    if prefix_core and text.startswith(prefix_core):
        return text
    prefix_head = re.sub(r"^[，。！？：、\s]+", "", prefix_core)[:4]
    text_head = re.sub(r"^[，。！？：、\s]+", "", text)[:4]
    if len(prefix_head) >= 3 and prefix_head == text_head:
        return text
    if prefix[-1] in "，：":
        return prefix + text
    return _sentence(prefix) + text


def _compose_unit(unit: _TimelineUnit, state: dict[str, object]) -> str:
    """将一个年龄或年龄阶段的事实编排为连贯段落。"""
    if not unit.events:
        return ""

    # 同一年龄段内不重复使用同一句连接词，避免“余波仍在……余波仍在”的回声。
    state["unit_connectors"] = set()
    pieces: list[str] = []
    previous: _Event | None = None
    for event in unit.events:
        text = _event_sentence(event)
        if not text:
            continue
        if previous is None:
            prefix = _first_intro(unit, state)
            # 原始文案有时自带“多年后/然而/随后”等开场，避免再套一层
            # 时间或转折词，保持短篇的呼吸感。
            if _explicit_transition(text):
                prefix = ""
            pieces.append(_prepend(prefix, text))
            if event.kind == "birth":
                pieces.append("那时你还不知道，命运会在往后的岁月里一次次改写你的道路。")
        else:
            pieces.append(_prepend(_bridge(previous, event, state), text))
        previous = event
        # 逐事件更新，让同一年龄内的危机、晋升和仪式都能拿到正确上下文。
        _update_story_state(state, (event,))
    return "".join(pieces)


def _update_story_state(state: dict[str, object], events: Iterable[_Event]) -> None:
    for event in events:
        if event.kind == "contact":
            state["contact_seen"] = True
        if event.kind == "advance" and ("饮下" in event.text or "晋升" in event.text):
            state["has_power"] = True
        if event.kind in _WARNING_KINDS:
            state["warning_seen"] = True
            state["warning_count"] = int(state.get("warning_count", 0)) + 1
        if event.kind == "acting":
            state["acting_count"] = int(state.get("acting_count", 0)) + 1


def _compact_blocks(blocks: list[NarrativeBlock]) -> list[NarrativeBlock]:
    """在保留晋升间隔的前提下控制单图密度；最多 36 个独立年龄块。"""
    soft_kinds = {"climb", "youth", "acting"}

    def removal_key(item: tuple[int, NarrativeBlock]) -> tuple[int, int, int]:
        index, block = item
        value = _normal_value(
            _Event(index, block.kind, None, block.text)
        )
        # 先删重复度高、叙事价值低的普通事件；扮演失当/途径特色会自然得到更高分。
        return (value, len(block.text), -index)

    while len(blocks) > 36:
        candidates = [
            item for item in enumerate(blocks) if item[1].kind in soft_kinds
        ]
        if not candidates:
            candidates = [
                item
                for item in enumerate(blocks)
                if item[1].kind == "meta" and item[1].emphasis == "normal"
            ]
        if not candidates:
            break
        remove_at, _ = min(candidates, key=removal_key)
        del blocks[remove_at]

    # 目标是让普通人生正文达到约 2200–3000 字，但不人为注水；超过上限时
    # 仍只从普通块中删减，不截断关键晋升、危机和终局场景。
    while sum(len(block.text) for block in blocks) > 3200:
        candidates = [
            item
            for item in enumerate(blocks)
            if item[1].kind in soft_kinds and item[1].emphasis == "normal"
        ]
        if not candidates:
            break
        remove_at, _ = min(candidates, key=removal_key)
        del blocks[remove_at]
    return blocks


def _seq_note(result: dict, pathway: dict | None) -> str:
    category = result.get("category")
    seq = result.get("final_seq")
    if category == "eldritch":
        return "最终序列：常理之外（旧日）"
    if category == "god" and pathway:
        return f"最终序列：0 · 【{pathways_mod.seq0_name(pathway)}】（登神）"
    if seq is None:
        return "最终序列：无（凡人）"
    note = f"最终序列：序列{seq}"
    if pathway and pathway.get("sequences") and seq in pathway["sequences"]:
        note += f" · 【{pathway['sequences'][seq]}】"
    return note


def summarize_life(result: dict, player: str = "") -> NarrativeView:
    """把完整模拟结果编译为稳定、按年龄推进的第二人称人生短篇。"""
    origin = events_mod.ORIGINS[result["origin_key"]]
    talent = events_mod.TALENTS[result["talent_key"]]
    pathway = pathways_mod.get_pathway(result["pathway_key"]) if result.get("pathway_key") else None
    header: list[str] = [
        f"【出身】{origin['name']}",
        f"【天赋】{talent['name']}——{talent['desc']}",
    ]
    if pathway:
        header.append(f"【途径】{pathway['name']}（{pathway.get('faction', '')}）")

    groups = _group_events(result.get("lines", []))
    raw_events = [event for group in groups for event in group.events]
    acting_counts = {"得法": 0, "尚可": 0, "失当": 0}
    for event in raw_events:
        if event.kind != "acting":
            continue
        acting_result, _ = _acting_result(event)
        if acting_result in acting_counts:
            acting_counts[acting_result] += 1

    blocks: list[NarrativeBlock] = []
    state: dict[str, object] = {
        "contact_seen": False,
        "has_power": False,
        "warning_seen": False,
        "warning_count": 0,
        "acting_count": 0,
        "connector_counts": {},
    }
    for unit in _timeline_units(groups):
        text = _compose_unit(unit, state)
        if not text:
            _update_story_state(state, unit.events)
            continue
        blocks.append(
            NarrativeBlock(
                chapter=_chapter(unit.events, state["contact_seen"]),
                kind=_dominant_kind(unit.events),
                age_label=_age_label(unit.ages),
                text=text,
                emphasis=_emphasis(unit.events),
            )
        )
    blocks = _compact_blocks(blocks)

    category = str(result.get("category", ""))
    stats: dict[str, int | float | str] = {
        "score": int(result.get("score", 0)),
        "age": int(result.get("age", 0)),
        "madness_peak": int(result.get("madness_peak", 0)),
        "acting_perfect": int(result.get("acting_perfect", 0)),
        "acting_good": acting_counts["得法"],
        "acting_ok": acting_counts["尚可"],
        "acting_bad": acting_counts["失当"],
        "category": category,
        "final_seq": "凡人" if result.get("final_seq") is None else str(result.get("final_seq")),
        "block_count": len(blocks),
        "narrative_length": sum(len(block.text) for block in blocks),
    }
    if result.get("pathway_key"):
        stats["pathway_key"] = str(result["pathway_key"])
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
    """渲染纯文本；图卡与它逐段共用同一份正文。"""
    out = ["🌫️ 诡秘人生 · 第五纪", ""]
    out.extend(view.header_lines)
    out.append("")
    out.append(
        f"【人生摘要】活到 {view.stats.get('age', 0)} 岁 · "
        f"评分 {view.stats.get('score', 0)} · 疯狂峰值 {view.stats.get('madness_peak', 0)} · "
        f"完美扮演 {view.stats.get('acting_perfect', 0)} 次"
    )
    for block in view.blocks:
        text = block.text
        if block.kind.startswith("ascension_"):
            # 纯文本没有 CSS，只替换本次真实晋升名称，避免误伤途径意象引号。
            match = re.match(r"ascension_(\d+)", block.kind)
            if match and view.stats.get("pathway_key"):
                try:
                    pathway = pathways_mod.get_pathway(str(view.stats["pathway_key"]))
                    sequence_name = pathways_mod.seq_name(pathway, int(match.group(1)))
                    text = text.replace(f"「{sequence_name}」", f"【{sequence_name}】", 1)
                except (KeyError, TypeError, ValueError):
                    pass
        out.extend(
            ["", f"{block.age_label}{text}" if block.age_label else text]
        )
    out.extend(
        [
            "",
            f"【结局】{view.ending_title}",
            view.ending_text,
            view.seq_note,
            view.footer,
        ]
    )
    return "\n".join(line for line in out if line is not None)
