"""核心逻辑测试：不依赖 AstrBot 运行时。"""
import os
import random
import sys

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)

from cyber_mystery.core import endings, engine, events, narrative, pathways, render, storage
from cyber_mystery.core.commands import (
    choose_random_build,
    normalize_seed,
    remainder_from_text,
)

STAGES = ("low", "mid", "high")


# ---------- 词库完整性 ----------

def test_origins_and_talents_complete():
    assert len(events.ORIGINS) >= 16
    assert len(events.TALENTS) >= 16
    for key, o in events.ORIGINS.items():
        assert o["name"] and o["region"] and o["desc"]
        assert o["pathway_bias"], key
        for p in o["pathway_bias"]:
            assert p in pathways.PATHWAYS, f"{key} 引用了未知途径 {p}"
    for key, t in events.TALENTS.items():
        assert t["name"] and t["desc"], key
        for p in t.get("pathway_bias", []):
            assert p in pathways.PATHWAYS, f"{key} 引用了未知途径 {p}"


def test_outer_talents_exist():
    outer_talents = [
        t for t in events.TALENTS.values() if float(t.get("outer_chance", 0) or 0) > 0
    ]
    assert outer_talents, "必须存在能解锁外神途径的天赋"


def test_pathways_structure():
    assert len(pathways.PATHWAYS) >= 12
    assert len(pathways.OUTER_PATHWAYS) >= 8
    for key, p in pathways.ALL_PATHWAYS.items():
        assert p["name"] and p["faction"] and p["desc"], key
        seqs = p.get("sequences") or {}
        assert 0 in seqs, f"{key} 缺少序列0（途径顶点）"
        assert 9 in seqs, f"{key} 缺少序列9（入门序列）"
        for seq, name in seqs.items():
            assert 0 <= seq <= 9 and isinstance(name, str) and name, f"{key} 序列{seq}"
        assert seqs[0], f"{key} 序列0 名称不能为空"


def test_fool_pathway_full():
    seqs = pathways.PATHWAYS["fool"]["sequences"]
    assert len(seqs) == 10
    assert seqs[9] == "占卜家"
    assert seqs[0] == "愚者"


def test_contact_events_cover_all_normal_pathways():
    for key in pathways.PATHWAYS:
        assert key in events.CONTACT_EVENTS, f"途径 {key} 缺少接触事件"
        assert events.CONTACT_EVENTS[key], key


def test_signature_events_keys_valid():
    for key, stages in events.SIGNATURE_EVENTS.items():
        assert key in pathways.PATHWAYS, f"特色事件引用未知途径 {key}"
        for stage in stages:
            assert stage in STAGES, f"{key} 非法序列段 {stage}"
            assert stages[stage], key


def test_event_pools_nonempty():
    for stage in STAGES:
        assert events.CLIMB_EVENTS[stage]
        assert events.OUTER_EVENTS[stage]
        assert events.CRISIS_EVENTS[stage]
    assert events.YOUTH_EVENTS
    assert events.OUTER_CONTACT_EVENTS
    assert events.ACTING_TEXTS["good"]
    assert events.ACTING_TEXTS["ok"]
    assert events.ACTING_TEXTS["bad"]
    assert events.DEATH_EVENTS
    assert events.MADNESS_EVENTS
    assert events.NORMAL_LATER_EVENTS
    assert len(events.YOUTH_EVENTS) >= 20
    assert all(len(events.CLIMB_EVENTS[stage]) >= 10 for stage in STAGES)
    assert all(len(events.OUTER_EVENTS[stage]) >= 10 for stage in STAGES)
    assert all(len(events.CRISIS_EVENTS[stage]) >= 9 for stage in STAGES)


def test_endings_cover_all_categories():
    for cat in endings.ENDING_ORDER:
        assert endings.ENDINGS.get(cat), f"结局类别 {cat} 没有文案"
        assert endings.TITLES_BY_CATEGORY.get(cat), f"结局类别 {cat} 没有称号"
        for e in endings.ENDINGS[cat]:
            assert e["title"] and e["text"], cat


# ---------- 引擎 ----------

def test_simulate_deterministic():
    for origin in ("tingen_clerk", "backlund_slum"):
        for talent in ("spirit_vision", "ancient_blood"):
            a = engine.simulate(random.Random(42), origin, talent)
            b = engine.simulate(random.Random(42), origin, talent)
            assert a == b, "同 seed 模拟结果必须一致"


def test_simulate_structure_valid():
    rng = random.Random(7)
    for _ in range(300):
        origin = rng.choice(list(events.ORIGINS))
        talent = rng.choice(list(events.TALENTS))
        r = engine.simulate(rng, origin, talent)
        assert r["category"] in endings.ENDING_ORDER
        assert r["final_seq"] is None or 0 <= r["final_seq"] <= 9
        assert 1 <= r["score"] <= 100
        assert r["lines"], "人生轨迹不能为空"
        assert r["ending_title"] and r["ending_text"] and r["title"]
        # 年龄单调不减
        ages = [ln["age"] for ln in r["lines"] if ln["age"] is not None]
        assert ages == sorted(ages)
        # 凡人结局必须未接触非凡；旧日必然抵达序列0
        if r["category"] == "normal":
            assert r["final_seq"] is None and r["pathway_key"] is None
        if r["category"] == "eldritch":
            assert r["final_seq"] == 0
        if r["is_outer"]:
            assert r["pathway_key"] in pathways.OUTER_PATHWAYS
        else:
            assert r["pathway_key"] is None or r["pathway_key"] in pathways.PATHWAYS


def test_simulate_all_combinations_smoke():
    rng = random.Random(99)
    for origin in events.ORIGINS:
        for talent in events.TALENTS:
            for _ in range(5):
                engine.simulate(rng, origin, talent)  # 不抛异常即可


def test_outer_pathway_reachable():
    """古神血脉应有可观概率触发外神途径（大数定律粗验）。"""
    rng = random.Random(2024)
    hits = 0
    trials = 400
    for _ in range(trials):
        r = engine.simulate(rng, "bansy_watcher", "ancient_blood")
        if r["is_outer"]:
            hits += 1
            assert r["pathway_key"] in pathways.OUTER_PATHWAYS
    assert hits > trials * 0.05, f"外神触发率过低：{hits}/{trials}"


def test_normal_pathway_never_outer_without_talent():
    rng = random.Random(1)
    for _ in range(300):
        r = engine.simulate(rng, "tingen_clerk", "iron_will")
        assert not r["is_outer"]


def test_format_life_output():
    r = engine.simulate(random.Random(5), "tingen_clerk", "spirit_vision")
    text = engine.format_life(r, "测试者")
    assert "【出身】" in text and "【天赋】" in text
    assert "【结局】" in text and "人生评分" in text
    assert "测试者" in text


def test_render_html_escapes():
    html = render.build_life_html(
        ["【出身】<script>x</script>"],
        [("climb", "3岁 <b>出生</b>")],
        "结局<&>",
        "文本&'\"引号",
        "序列9",
        "页脚",
    )
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "结局&lt;&amp;&gt;" in html


def test_render_pages_keep_long_lives_readable():
    compact_lines = [("climb", f"{i}岁 " + "雾中回响" * 6) for i in range(34)]
    compact_pages = render.build_life_html_pages(
        ["【出身】测试"], compact_lines, "终局", "结局文本", "序列9", "评分 60"
    )
    assert len(compact_pages) == 1
    assert "grid-template-columns: repeat(3" in compact_pages[0]

    lines = [("climb", f"{i}岁 " + "雾中回响" * 30) for i in range(80)]
    pages = render.build_life_html_pages(
        ["【出身】测试"], lines, "终局", "结局文本", "序列9", "评分 60"
    )
    assert len(pages) == 1
    assert "诡秘人生 · 第五纪" in pages[0]
    assert "【结局】终局" in pages[-1]


def test_render_events_fill_columns_before_moving_right():
    cards = [f"card-{index}" for index in range(10)]
    columns = render._column_major_slices(cards)
    assert columns == [
        ["card-0", "card-1", "card-2", "card-3"],
        ["card-4", "card-5", "card-6", "card-7"],
        ["card-8", "card-9"],
    ]
    html = render._column_major_html(cards)
    assert html.count('class="timeline-column"') == 3
    assert "flex-direction:column" in render.build_life_html_pages(
        ["测试"], [("climb", "事件")], "结局", "文本", "序列", "页脚"
    )[0]


def test_narrative_summarizes_without_mutating_result():
    result = engine.simulate(random.Random(59), "tingen_clerk", "transmigrator")
    original_lines = [dict(line) for line in result["lines"]]
    view = narrative.summarize_life(result, "测试者")
    assert view.blocks
    assert len(view.blocks) <= 30
    assert tuple(block.chapter for block in view.blocks) == tuple(
        block.chapter for block in view.blocks
    )
    assert any(block.chapter == "非凡接触" for block in view.blocks)
    assert any(block.chapter == "代价与终局" for block in view.blocks)
    assert result["lines"] == original_lines


def test_narrative_preserves_key_nodes_and_merges_ordinary_events():
    result = engine.simulate(random.Random(59), "tingen_clerk", "transmigrator")
    view = narrative.summarize_life(result)
    raw_key_texts = [
        line["text"]
        for line in result["lines"]
        if line["kind"] in {"birth", "contact", "advance", "crisis", "madness", "ending"}
    ]
    for text in raw_key_texts:
        assert any(text[:18] in block.text for block in view.blocks)
    assert any(block.kind == "summary" for block in view.blocks)
    assert any(block.kind == "acting" for block in view.blocks)


def test_narrative_plain_text_and_card_share_blocks():
    result = engine.simulate(random.Random(42), "tingen_clerk", "spirit_vision")
    view = narrative.summarize_life(result, "测试者")
    text = narrative.format_narrative(view)
    html = render.build_life_html_pages(narrative=view)[0]
    for block in view.blocks:
        assert block.text[:20] in text
        assert render._esc(block.text) in html


def test_narrative_bounds_and_single_card_across_random_lives():
    rng = random.Random(20260819)
    for _ in range(300):
        origin = rng.choice(list(events.ORIGINS))
        talent = rng.choice(list(events.TALENTS))
        result = engine.simulate(rng, origin, talent)
        view = narrative.summarize_life(result)
        assert len(view.blocks) <= 30
        assert len(render.build_life_html_pages(narrative=view)) == 1


def test_narrative_age_ranges_and_acting_counts():
    result = {
        "origin_key": "tingen_clerk",
        "talent_key": "spirit_vision",
        "pathway_key": "fool",
        "category": "saint",
        "final_seq": 4,
        "score": 72,
        "age": 41,
        "madness_peak": 22,
        "acting_perfect": 2,
        "ending_title": "测试结局",
        "ending_text": "测试结局文本",
        "title": "测试称号",
        "lines": [
            {"kind": "birth", "age": 0, "text": "你出生于廷根"},
            {"kind": "youth", "age": 5, "text": "你在雨中拾到一枚旧徽章"},
            {"kind": "youth", "age": 9, "text": "你在学校的地图背面看见一条不存在的街"},
            {"kind": "contact", "age": 16, "text": "你接触了非凡世界"},
            {"kind": "acting", "age": 20, "text": "扮演得法：魔药温顺地融入血脉"},
            {"kind": "acting", "age": 24, "text": "扮演尚可：消化仍在推进"},
            {"kind": "acting", "age": 28, "text": "扮演失当：疯狂在梦中回响"},
            {"kind": "crisis", "age": 30, "text": "你在灵界听见第一声钟响"},
            {"kind": "crisis", "age": 30, "text": "你在灵界迷路了一夜"},
        ],
    }
    view = narrative.summarize_life(result)
    assert any(block.age_label == "5–9岁" for block in view.blocks)
    acting = next(block for block in view.blocks if block.kind == "acting")
    assert "得法1次" in acting.text and "尚可1次" in acting.text and "失当1次" in acting.text
    assert sum(block.kind == "acting" for block in view.blocks) == 1
    assert sum(block.kind == "crisis" for block in view.blocks) == 1


def test_choice_cards_have_distinct_origin_and_talent_styles():
    origin_pages = render.build_choice_html_pages("origin", "选择出身", events.ORIGINS)
    talent_pages = render.build_choice_html_pages("talent", "选择天赋", events.TALENTS)
    assert len(origin_pages) == 1
    assert len(talent_pages) == 1
    origin_page = origin_pages[0]
    talent_page = talent_pages[0]
    assert "雾都档案 · 身份卷宗" in origin_page
    assert "财力" in origin_page and "风险" in origin_page
    assert "grid-template-columns:repeat(4" in origin_page
    assert "灵性档案 · 命运回响" in talent_page
    assert "非凡接触" in talent_page


# ---------- 存储 ----------

def test_record_and_ranking():
    data = storage.empty_group()
    storage.record_play(data, "u1", "甲", 50, 5, "一方传奇", False)
    storage.record_play(data, "u1", "甲", 80, 2, "神之左手", False)
    storage.record_play(data, "u2", "乙", 95, -1, "旧日临世", True)
    storage.record_play(data, "u3", "丙", 30, None, "凡人一生", False)
    rows = storage.ranking(data, 10)
    assert [r["user_id"] for r in rows] == ["u2", "u1", "u3"]
    assert rows[0]["god_count"] == 1
    u1 = data["users"]["u1"]
    assert u1["best_score"] == 80 and u1["best_seq"] == 2  # 只记最佳
    assert u1["plays"] == 2


def test_seq_display():
    assert storage.seq_display(-1) == "旧日"
    assert storage.seq_display(0) == "序列0·登神"
    assert storage.seq_display(7) == "序列7"
    assert storage.seq_display(None) == "凡人"


def test_group_data_roundtrip(tmp_path):
    path = str(tmp_path / "g1.json")
    data = storage.empty_group()
    storage.record_play(data, "u1", "甲", 60, 4, "圣者", False)
    storage.save_group_data(path, data)
    loaded = storage.load_group_data(path)
    assert loaded["users"]["u1"]["best_score"] == 60
    # 损坏文件回退空结构
    bad = str(tmp_path / "bad.json")
    with open(bad, "w", encoding="utf-8") as f:
        f.write("{not json")
    assert storage.load_group_data(bad)["users"] == {}


# ---------- 命令参数提取 ----------

def test_remainder_strips_group_and_subcommand():
    dummy = object()
    cases = [
        ("诡秘 重开", ""),
        ("诡秘 重开 随机", "随机"),
        ("诡秘 重开 廷根 灵视", "廷根 灵视"),
        ("诡秘 选 3", "3"),
        ("诡秘 途径 愚者", "愚者"),
        ("/诡秘 重开 随机", "随机"),
        ("guimi restart random", "random"),
        ("诡秘 帮助", ""),
    ]
    for text, expected in cases:
        assert remainder_from_text(text) == expected, text


# ---------- 种子复现 ----------

def test_normalize_seed():
    assert normalize_seed("14") == 14
    assert normalize_seed("abc") == "abc"
    assert normalize_seed(None) is None


def test_seeded_random_restart_is_reproducible():
    first_rng = random.Random(normalize_seed("12345"))
    first_origin, first_talent = choose_random_build(
        first_rng, events.ORIGINS, events.TALENTS
    )
    first_result = engine.simulate(first_rng, first_origin, first_talent)

    second_rng = random.Random(normalize_seed("12345"))
    second_origin, second_talent = choose_random_build(
        second_rng, events.ORIGINS, events.TALENTS
    )
    second_result = engine.simulate(second_rng, second_origin, second_talent)

    assert (first_origin, first_talent, first_result) == (
        second_origin,
        second_talent,
        second_result,
    )

def test_god_and_eldritch_are_reachable():
    categories = {
        engine.simulate(random.Random(seed), "tingen_clerk", "transmigrator")["category"]
        for seed in range(500)
    }
    assert "god" in categories
    assert "eldritch" in categories
