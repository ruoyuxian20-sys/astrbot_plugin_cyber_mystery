"""人生模拟引擎：出身 + 天赋 + 随机数 → 一段诡秘人生。

纯函数实现，不依赖 AstrBot 运行时，便于 pytest 覆盖。
"""
from __future__ import annotations

import random

from . import endings as endings_mod
from . import events as events_mod
from . import narrative as narrative_mod
from . import pathways as pathways_mod

# ---------- 可调参数（测试依赖这些常量的稳定性） ----------
CONTACT_BASE = 0.62          # 非凡接触基础概率
CONTACT_RETRY = 0.35         # 第一次未接触时的二次概率
MADNESS_CAP = 100            # 疯狂值上限，达到即失控/癫狂
ACTING_BASE = 0.58           # 扮演成功基础概率
OUTER_ACTING_PENALTY = 0.08  # 外神途径扮演惩罚
OUTER_MADNESS_MULT = 1.3     # 外神途径疯狂增长系数
PROMOTE_BASE = 0.78          # 晋升成功基础概率
GOD_MADNESS_MAX = 25         # 登神要求的疯狂上限
GOD_ACTING_MIN = 3           # 登神要求的完美扮演次数
ELDRITCH_FROM_GOD = 0.12     # 登神后吞并相邻途径成为旧日的概率
SCORE_SEQ = {9: 18, 8: 26, 7: 34, 6: 42, 5: 50, 4: 58, 3: 66, 2: 74, 1: 82, 0: 95}

# ---------- 晋升词（按途径专属生成） ----------
PATHWAY_ESSENCE = {
    "fool": "灰雾之上的愚弄与奇迹",
    "door": "无尽门扉与空间夹缝",
    "error": "规则裂隙与命运偷窃",
    "hanged": "阴影祷告与堕落圣言",
    "visionary": "人心剧场与梦境操控",
    "tyrant": "风暴怒海与天灾权柄",
    "sun": "永恒光辉与净化圣火",
    "tower": "知识洪流与真理之眼",
    "paragon": "齿轮文明与造物之火",
    "giant": "古老力量与黄昏战歌",
    "night": "永夜安眠与隐秘阴影",
    "death": "亡者国度与生死摆渡",
    "red_priest": "战争火焰与征服铁血",
    "witch": "欢愉痛苦与混沌魔药",
    "hermit": "禁忌知识与疯狂奥秘",
    "monster": "无常命运与幸运厄运",
    "mother_of_tree": "欲望根系与失心之树",
    "wheel_of_fate": "永恒轮回与命运之环",
    "star_sovereign": "无垠星空与沉重星核",
    "primordial_hunger": "永不满足的聚合之口",
    "dimension_shifter": "高维俯视与画中世界",
    "whisper": "不熄呓语与意识共鸣",
    "decay_lord": "万物终朽与熵之权柄",
    "chaos_mist": "不确定迷雾与监督真理",
    "bound_one": "暗影锁链与神孽囚笼",
    "black_emperor": "秩序腐化与黑皇帝律",
    "fallen_mother": "绯红月光与母巢根源",
    "chaos_womb": "生命原胎与现实主宰",
    "evil_origin": "丰饶背面的原初恶意",
    "disorder_realm": "律法倒影与失序之国",
}


def _ascension_text(pathway_key: str, pathway: dict, kind: str) -> str:
    """按途径生成序列四 / 真神 / 旧日的专属晋升词。"""
    essence = PATHWAY_ESSENCE.get(pathway_key, "神秘")
    seq4 = pathways_mod.seq_name(pathway, 4)
    seq0 = pathways_mod.seq0_name(pathway)
    if kind == "seq4":
        return (
            f"魔药入喉，{seq4}的轮廓在{essence}中浮现。\n"
            f"你听见{pathway['name']}途径的源质开始低语，半神之门轰然洞开。\n"
            "从今往后，你已是圣者——凡人仰望的深渊。"
        )
    if kind == "god":
        return (
            f"最后一滴魔药落入舌尖，{essence}在你体内彻底苏醒。\n"
            f"「{seq0}」之名被刻入{pathway['name']}途径的顶点，旧日退潮。\n"
            "你登临序列0，成为此世真神。"
        )
    return (
        f"仪式没有停下，{essence}向着常理之外继续坍缩。\n"
        f"你吞下相邻途径的序列0，{seq0}与你的存在融为一体。\n"
        "历史在你身后合拢，世界因你而改写——你已是旧日。"
    )


def _line(kind: str, age: int | None, text: str) -> dict:
    return {"kind": kind, "age": age, "text": text}


def _talent_num(talent: dict, key: str) -> float:
    return float(talent.get(key, 0) or 0)


def _pick_pathway(rng: random.Random, origin: dict, talent: dict) -> str:
    """按出身与天赋的途径倾向加权随机（仅正规途径）。"""
    weights: dict[str, float] = {k: 1.0 for k in pathways_mod.PATHWAYS}
    for key in origin.get("pathway_bias", []):
        if key in weights:
            weights[key] += 3.0
    for key in talent.get("pathway_bias", []):
        if key in weights:
            weights[key] += 2.5
    keys = list(weights)
    picks = [weights[k] for k in keys]
    return rng.choices(keys, weights=picks, k=1)[0]


def simulate(
    rng: random.Random,
    origin_key: str,
    talent_key: str,
) -> dict:
    """跑完一段人生，返回结构化结果。"""
    origin = events_mod.ORIGINS[origin_key]
    talent = events_mod.TALENTS[talent_key]
    lines: list[dict] = []
    madness = int(_talent_num(talent, "start_madness"))
    madness_resist = _talent_num(talent, "madness_resist")
    acting_bonus = _talent_num(talent, "acting_bonus")
    luck = _talent_num(talent, "luck")
    watched = bool(talent.get("watched"))
    perfect = 0

    def add_madness(delta: int, is_outer: bool) -> int:
        nonlocal madness
        madness = min(MADNESS_CAP, madness + int(delta * OUTER_MADNESS_MULT) if is_outer
                      else min(MADNESS_CAP, madness + delta))
        return madness

    used_texts: set[str] = set()

    def pick_text(pool: list[str]) -> str:
        """优先抽未用过的事件文本，避免一局内重复。"""
        fresh = [t for t in pool if t not in used_texts]
        text = rng.choice(fresh if fresh else pool)
        used_texts.add(text)
        return text

    age = 0
    lines.append(_line("birth", 0, f"你出生于{origin['region']}"))

    # ---------- 童年与少年 ----------
    for _ in range(rng.randint(1, 2)):
        age += rng.randint(3, 6)
        lines.append(_line("youth", age, pick_text(events_mod.YOUTH_EVENTS)))

    # ---------- 非凡接触（一般在成年前后） ----------
    age = max(age + rng.randint(1, 6), 14)
    contact_p = (
        CONTACT_BASE
        + _talent_num(talent, "contact_bonus")
        + origin.get("danger", 2) * 0.04
    )
    contacted = rng.random() < max(0.05, min(0.95, contact_p))
    if not contacted:
        contacted = rng.random() < CONTACT_RETRY  # 命运的第二次敲门
        if contacted:
            lines.append(_line("meta", age, "命运第二次敲响了你的门——这一次你应了门"))

    pathway_key = None
    is_outer = False
    if contacted:
        # 外神侵蚀判定：仅特定天赋有几率被引上外神途径
        if rng.random() < _talent_num(talent, "outer_chance"):
            is_outer = True
            pathway_key = rng.choice(list(pathways_mod.OUTER_PATHWAYS))
            lines.append(
                _line("contact", age, pick_text(events_mod.OUTER_CONTACT_EVENTS + events_mod.EXTRA_CONTACT_EVENTS.get(pathway_key, [])))
            )
        else:
            pathway_key = _pick_pathway(rng, origin, talent)
            lines.append(
                _line("contact", age, pick_text(events_mod.CONTACT_EVENTS[pathway_key] + events_mod.EXTRA_CONTACT_EVENTS.get(pathway_key, [])))
            )
        pathway = pathways_mod.get_pathway(pathway_key)
        seq = 9
        lines.append(
            _line(
                "advance",
                age,
                f"你饮下了「{pathways_mod.seq_name(pathway, 9)}」魔药，"
                f"踏入{pathway['name']}途径",
            )
        )
        if is_outer:
            lines.append(
                _line("meta", age, "这不是任何正统教会的配方——但它认你")
            )
    else:
        seq = None
        lines.append(_line("meta", age, "非凡世界的大门始终没有为你敞开"))

    # ---------- 序列爬升 ----------
    fail_streak = 0
    finished: str | None = None  # 提前终结的结局类别
    while seq is not None and seq >= 0 and finished is None and age < 88:
        age += rng.randint(2, 4)
        stage = pathways_mod.seq_stage(seq)
        pathway = pathways_mod.get_pathway(pathway_key)

        # 段内事件：外神氛围 / 途径特色 / 通用
        sig = (
            events_mod.SIGNATURE_EVENTS.get(pathway_key, {}).get(stage, [])
            + events_mod.EXTRA_SIGNATURE_EVENTS.get(pathway_key, {}).get(stage, [])
        )
        if is_outer:
            pool = (
                events_mod.OUTER_EVENTS[stage]
                if rng.random() < 0.6
                else (sig or events_mod.CLIMB_EVENTS[stage])
            )
        else:
            pool = (
                events_mod.CLIMB_EVENTS[stage]
                if rng.random() < 0.45
                else (sig or events_mod.CLIMB_EVENTS[stage])
            )
        lines.append(_line("climb", age, pick_text(pool)))

        # 危机事件
        crisis_p = 0.07 + madness / 320 + (0.04 if seq <= 4 else 0.0)
        if is_outer:
            crisis_p += 0.05
        if rng.random() < crisis_p:
            lines.append(
                _line("crisis", age, pick_text(events_mod.CRISIS_EVENTS[stage]))
            )
            add_madness(rng.randint(8, 16), is_outer)

        # 疯狂临界提示
        if madness >= 85:
            lines.append(_line("madness", age, pick_text(events_mod.MADNESS_EVENTS)))

        # 疯狂爆表 → 失控 / 癫狂
        if madness >= MADNESS_CAP:
            finished = "mad" if rng.random() < madness_resist else "monster"
            break

        # 扮演判定
        acting_p = (
            ACTING_BASE
            + acting_bonus
            - (OUTER_ACTING_PENALTY if is_outer else 0.0)
            - (0.10 if seq <= 3 else 0.0)
            - madness / 250
        )
        roll = rng.random()
        if roll < max(0.05, acting_p):
            madness = max(0, madness - 20)
            perfect += 1
            lines.append(_line("acting", age, pick_text(events_mod.ACTING_TEXTS["good"])))
        elif roll < acting_p + 0.30:
            add_madness(5, is_outer)
            lines.append(_line("acting", age, pick_text(events_mod.ACTING_TEXTS["ok"])))
        else:
            add_madness(13, is_outer)
            lines.append(_line("acting", age, pick_text(events_mod.ACTING_TEXTS["bad"])))

        # 高序列死亡风险
        if seq <= 4 and rng.random() < 0.03 + origin.get("danger", 2) * 0.01:
            lines.append(_line("ending", age, pick_text(events_mod.DEATH_EVENTS)))
            finished = "dead"
            break

        # 登神 / 旧日 / 晋升
        if seq == 1:
            if is_outer:
                # 外神途径的尽头：条件放宽但仍需扮演与压制疯狂
                ascend = (
                    perfect >= 2
                    and madness <= 45
                    and rng.random() < 0.35 + luck * 0.5
                )
            else:
                ascend = (
                    perfect >= GOD_ACTING_MIN
                    and madness <= GOD_MADNESS_MAX
                    and rng.random() < 0.30 + luck * 0.5
                )
            if ascend:
                if is_outer:
                    lines.append(
                        _line(
                            "advance",
                            age,
                            "你抵达了外神途径的尽头——常理在你身后合拢",
                        )
                    )
                    lines.append(_line("advance", age, _ascension_text(pathway_key, pathway, "eldritch")))
                    seq = 0
                    finished = "eldritch"
                elif rng.random() < ELDRITCH_FROM_GOD:
                    lines.append(
                        _line(
                            "advance",
                            age,
                            "登神的仪式没有停下——你顺手吞下了相邻途径的序列0",
                        )
                    )
                    lines.append(_line("advance", age, _ascension_text(pathway_key, pathway, "eldritch")))
                    seq = 0
                    finished = "eldritch"
                else:
                    lines.append(
                        _line(
                            "advance",
                            age,
                            f"你完成了最后的仪式——「{pathways_mod.seq0_name(pathway)}」之名加于你身",
                        )
                    )
                    lines.append(_line("advance", age, _ascension_text(pathway_key, pathway, "god")))
                    seq = 0
                    finished = "god"
            else:
                finished = "angel"
            break

        promote_p = (
            PROMOTE_BASE - (9 - seq) * 0.06 + luck - madness / 400
        )
        if rng.random() < max(0.10, promote_p):
            seq -= 1
            fail_streak = 0
            name = pathways_mod.seq_name(pathway, seq)
            has_name = (pathway.get("sequences") or {}).get(seq)
            lines.append(
                _line(
                    "advance",
                    age,
                    f"你晋升「{name}」" + ("" if has_name else f"（{pathway['name']}途径）"),
                )
            )
            if seq == 4:
                lines.append(_line("advance", age, _ascension_text(pathway_key, pathway, "seq4")))
            if seq <= 3 and watched:
                lines.append(
                    _line(
                        "meta",
                        age,
                        rng.choice([
                            "某个高处的存在，正在注视着你",
                            "星空深处，有什么缓缓转动目光",
                            "你的一次心跳，在遥远的某处被记下",
                            "无端地，你想起了那片灰雾",
                        ]),
                    )
                )
        else:
            fail_streak += 1
            add_madness(10, is_outer)
            lines.append(
                _line(
                    "crisis",
                    age,
                    "这一步你没能迈过去，魔药在体内郁结，疯狂滋长",
                )
            )
            # 年岁渐长，或心灰意冷：急流勇退，安于当前序列
            if age >= 58 or (fail_streak >= 2 and rng.random() < 0.35):
                lines.append(
                    _line("meta", age, "岁月与旧伤让你停下了脚步——你选择了急流勇退")
                )
                break
            if fail_streak >= 3 or rng.random() < madness / 220:
                loss_p = 0.22 + madness / 180 - madness_resist
                if rng.random() < max(0.10, loss_p):
                    finished = "monster"
                    break

    # ---------- 终局判定 ----------
    if finished is None:
        if seq is None:
            for _ in range(rng.randint(1, 2)):
                age += rng.randint(8, 18)
                lines.append(
                    _line("climb", age, pick_text(events_mod.NORMAL_LATER_EVENTS))
                )
            category = "normal"
        else:
            category = (
                "angel" if seq <= 1
                else "saint" if seq <= 4
                else "mid" if seq <= 7
                else "low"
            )
    else:
        category = finished

    ending = endings_mod.pick_ending(category, rng)

    # ---------- 评分 ----------
    if seq is None:
        score = 38 + rng.randint(0, 12)
    else:
        score = SCORE_SEQ.get(seq, 30) + perfect * 2
        score -= min(20, madness // 5)
        if category == "dead":
            score = int(score * 0.75)
        elif category in ("monster", "mad"):
            score = int(score * 0.6)
        elif category == "god":
            score = max(90, score)
        elif category == "eldritch":
            score = max(97, score)
        score = max(1, min(100, score + rng.randint(-3, 3)))

    return {
        "origin_key": origin_key,
        "talent_key": talent_key,
        "pathway_key": pathway_key,
        "is_outer": is_outer,
        "final_seq": seq,
        "category": category,
        "ending_title": ending["title"],
        "ending_text": ending["text"],
        "title": endings_mod.make_title(category, rng),
        "score": score,
        "madness_peak": madness,
        "acting_perfect": perfect,
        "lines": lines,
        "age": age,
    }


# ---------- 文本格式化 ----------

def format_life(
    result: dict,
    player: str = "",
    view: narrative_mod.NarrativeView | None = None,
) -> str:
    """把人生结果渲染成摘要纯文本；图卡与文本共享同一叙事模型。"""
    return narrative_mod.format_narrative(
        view or narrative_mod.summarize_life(result, player)
    )
