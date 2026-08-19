"""高序列晋升与序列零终局目录。

本模块只保存展示文案和受控视觉主题，不参与随机判定。引擎在已有的
晋升分支确定之后查询这里的场景，因此不会改变随机调用顺序或模拟概率。
"""
from __future__ import annotations

from dataclasses import dataclass

from . import pathways as pathways_mod


ASCENSION_MODES = (
    "standard_god",
    "adjacent_seq0_devour",
    "source_essence_devour",
    "outer_terminus",
)
LOW_SEQUENCES = (9, 8, 7, 6, 5)
HIGH_SEQUENCES = (4, 3, 2, 1)
ASCENSION_SEQUENCES = LOW_SEQUENCES + HIGH_SEQUENCES
FINAL_SEQUENCE = 0


@dataclass(frozen=True)
class AscensionScene:
    pathway_key: str
    sequence: int
    mode: str
    title: str
    text: str
    motif: str
    visual_theme: str
    emphasis: str = "key"


# 每条途径保留独立的意象、权柄和世界反馈。序列模板只负责推进层级，
# 具体词汇来自这里，因此同一序列在不同途径中不会只是替换一个名称。
_MOTIFS: dict[str, dict[str, str]] = {
    "fool": {"core": "灰雾、历史孔隙与荒诞戏法", "image": "一张没有背面的纸牌", "domain": "欺瞒与奇迹", "sign": "雾中钟声"},
    "door": {"core": "无尽门扉与星界夹缝", "image": "一把在虚空中自行转动的钥匙", "domain": "空间与旅行", "sign": "远方同时打开"},
    "error": {"core": "规则裂隙与被偷走的命运", "image": "一行被世界删去的法则", "domain": "错误与窃取", "sign": "因果短暂失焦"},
    "hanged": {"core": "阴影祷告与堕落圣言", "image": "倒悬在黑暗中的祭坛", "domain": "牺牲与污染", "sign": "祷文从反方向响起"},
    "visionary": {"core": "人心剧场与梦境操控", "image": "一座没有观众的剧院", "domain": "心灵与梦境", "sign": "所有人同时沉默"},
    "tyrant": {"core": "风暴怒海与天灾权柄", "image": "悬在雷云中的王冠", "domain": "海洋与雷霆", "sign": "远海先于你低头"},
    "sun": {"core": "永恒光辉与净化圣火", "image": "从黑夜中央升起的白色太阳", "domain": "光明与净化", "sign": "阴影被迫说出真名"},
    "tower": {"core": "知识洪流与真理之眼", "image": "一座向自身内部延伸的图书馆", "domain": "知识与真理", "sign": "所有书页同时翻动"},
    "paragon": {"core": "齿轮文明与造物之火", "image": "一颗仍在运转的金属心脏", "domain": "工艺与文明", "sign": "城市依次亮起"},
    "giant": {"core": "古老力量与黄昏战歌", "image": "立在暮色尽头的巨人脊骨", "domain": "战争与巨人", "sign": "大地记起你的脚步"},
    "night": {"core": "永夜安眠与隐秘阴影", "image": "一轮没有边缘的黑月", "domain": "黑暗与安眠", "sign": "所有梦境归于寂静"},
    "death": {"core": "亡者国度与生死摆渡", "image": "驶向无灯彼岸的渡船", "domain": "死亡与归还", "sign": "死者为你让开道路"},
    "red_priest": {"core": "战争火焰与征服铁血", "image": "插入焦土的燃烧军旗", "domain": "战争与征服", "sign": "远处的军阵同时转向"},
    "witch": {"core": "欢愉痛苦与混沌魔药", "image": "盛满七色液体的裂口酒杯", "domain": "欲望与魔药", "sign": "笑声和哭声重叠"},
    "hermit": {"core": "禁忌知识与疯狂奥秘", "image": "写满无法理解文字的眼睛", "domain": "隐秘与奥秘", "sign": "知识先于问题出现"},
    "monster": {"core": "无常命运与幸运厄运", "image": "落地后永远不会停止的硬币", "domain": "命运与概率", "sign": "偶然开始有了方向"},
    "mother_of_tree": {"core": "欲望根系与失心之树", "image": "从星空倒长下来的根须", "domain": "繁衍与渴望", "sign": "根系穿过你的名字"},
    "wheel_of_fate": {"core": "永恒轮回与命运之环", "image": "没有起点的巨大圆环", "domain": "轮回与宿命", "sign": "昨日从明日返回"},
    "star_sovereign": {"core": "无垠星空与沉重星核", "image": "坠入掌心的冷暗星核", "domain": "星辰与引力", "sign": "群星调整了位置"},
    "primordial_hunger": {"core": "永不满足的聚合之口", "image": "吞食光线的巨大裂口", "domain": "聚合与饥饿", "sign": "世界边缘开始缺失"},
    "dimension_shifter": {"core": "高维俯视与画中世界", "image": "被折叠成一角的现实", "domain": "维度与观察", "sign": "上下左右失去意义"},
    "whisper": {"core": "不熄呓语与意识共鸣", "image": "从所有喉咙同时发出的低语", "domain": "意识与回响", "sign": "你的念头被提前说出"},
    "decay_lord": {"core": "万物终朽与熵之权柄", "image": "正在腐烂却永不坍塌的王座", "domain": "衰败与终结", "sign": "时间在物质上留下伤口"},
    "chaos_mist": {"core": "不确定迷雾与监督真理", "image": "无法被任何测量捕捉的雾滴", "domain": "混沌与监督", "sign": "答案先于规则崩解"},
    "bound_one": {"core": "暗影锁链与神孽囚笼", "image": "锁住星空的黑色枷锁", "domain": "束缚与神孽", "sign": "连神性也开始挣扎"},
    "black_emperor": {"core": "秩序腐化与黑皇帝律", "image": "写满矛盾法令的王冠", "domain": "秩序与腐化", "sign": "所有命令互相否定"},
    "fallen_mother": {"core": "绯红月光与母巢根源", "image": "在月背缓慢张开的巢穴", "domain": "母巢与血月", "sign": "血缘延伸到星空"},
    "chaos_womb": {"core": "生命原胎与现实主宰", "image": "孕育世界的无形胎室", "domain": "生命与现实", "sign": "新生事物没有旧名"},
    "evil_origin": {"core": "丰饶背面的原初恶意", "image": "开满花却没有果实的荒原", "domain": "丰饶与恶意", "sign": "祝福长出尖牙"},
    "disorder_realm": {"core": "律法倒影与失序之国", "image": "倒映着另一套法律的王国", "domain": "失序与律法", "sign": "边界拒绝承认自己存在"},
}


_NORMAL_THEMES = {
    key: {
        "visual_theme": key,
        "accent": accent,
        "accent_soft": soft,
        "border": border,
        "glow": glow,
        "symbol": symbol,
        "texture": texture,
        "faction": "normal",
    }
    for key, accent, soft, border, glow, symbol, texture in (
        ("fool", "#b99ae8", "rgba(143,92,190,.22)", "#d6b8ff", "rgba(180,130,255,.3)", "◌", "mist"),
        ("door", "#76c9ef", "rgba(60,150,220,.2)", "#9ee1ff", "rgba(90,180,255,.3)", "◇", "star"),
        ("error", "#d98ad4", "rgba(180,60,160,.2)", "#f2b1ea", "rgba(230,90,210,.3)", "⌁", "glitch"),
        ("hanged", "#8e9b9f", "rgba(70,80,85,.24)", "#c3d0d2", "rgba(150,170,170,.25)", "⸸", "prayer"),
        ("visionary", "#e39cce", "rgba(200,90,170,.2)", "#f3c4e5", "rgba(230,130,200,.3)", "◉", "theatre"),
        ("tyrant", "#5eb9e7", "rgba(30,120,190,.22)", "#a0e5ff", "rgba(40,170,240,.32)", "ϟ", "storm"),
        ("sun", "#f1cf76", "rgba(220,165,50,.2)", "#ffe7a1", "rgba(255,210,90,.34)", "✦", "radiance"),
        ("tower", "#96b3d8", "rgba(80,120,180,.2)", "#c8ddff", "rgba(120,160,220,.28)", "⌘", "knowledge"),
        ("paragon", "#d9a66b", "rgba(180,100,40,.2)", "#f3c18a", "rgba(230,140,60,.3)", "⚙", "gear"),
        ("giant", "#c28d6e", "rgba(150,70,40,.2)", "#e4b394", "rgba(190,100,70,.28)", "ᛉ", "war"),
        ("night", "#7189c4", "rgba(40,60,130,.24)", "#a7b9ef", "rgba(80,110,200,.3)", "☾", "night"),
        ("death", "#9b9da8", "rgba(75,75,95,.22)", "#d0d1dc", "rgba(150,150,180,.28)", "†", "grave"),
        ("red_priest", "#dc6d58", "rgba(170,50,35,.22)", "#ffad8f", "rgba(230,80,50,.32)", "⚔", "warfire"),
        ("witch", "#d77cb8", "rgba(175,50,130,.22)", "#f2a6d8", "rgba(220,90,170,.32)", "♢", "potion"),
        ("hermit", "#a88cc7", "rgba(100,60,150,.22)", "#d2b8f0", "rgba(160,100,220,.3)", "☍", "occult"),
        ("monster", "#8fd1a1", "rgba(55,145,90,.2)", "#c2f0c9", "rgba(90,200,120,.3)", "◈", "chance"),
    )
}


_OUTER_ACCENTS = {
    "mother_of_tree": ("#d66f9d", "◒", "root"),
    "wheel_of_fate": ("#a98cff", "◉", "wheel"),
    "star_sovereign": ("#82bff2", "✶", "starcore"),
    "primordial_hunger": ("#cf5c68", "◉", "hunger"),
    "dimension_shifter": ("#8dd8d0", "◇", "dimension"),
    "whisper": ("#bf91dd", "≋", "whisper"),
    "decay_lord": ("#a5af73", "∴", "decay"),
    "chaos_mist": ("#8fa4c9", "∿", "chaos"),
    "bound_one": ("#8b7ab6", "⛓", "bound"),
    "black_emperor": ("#bf6d5f", "♜", "corrupt"),
    "fallen_mother": ("#d46c8f", "☽", "bloodmoon"),
    "chaos_womb": ("#7ad0ae", "◍", "womb"),
    "evil_origin": ("#c4936d", "❧", "thorn"),
    "disorder_realm": ("#bd82d2", "⌘", "disorder"),
}


def _outer_theme(key: str) -> dict[str, str]:
    accent, symbol, texture = _OUTER_ACCENTS[key]
    return {
        "visual_theme": f"outer-{texture}",
        "accent": accent,
        "accent_soft": "rgba(125,55,145,.22)",
        "border": accent,
        "glow": "rgba(180,70,190,.34)",
        "symbol": symbol,
        "texture": texture,
        "faction": "outer",
    }


PATHWAY_THEMES = {
    **_NORMAL_THEMES,
    **{key: _outer_theme(key) for key in _OUTER_ACCENTS},
}


def pathway_visual_theme(pathway_key: str) -> dict[str, str]:
    """返回受控视觉主题副本，避免调用方修改目录。"""
    theme = PATHWAY_THEMES.get(pathway_key)
    if theme is None:
        return {
            "visual_theme": "unknown",
            "accent": "#d8c58b",
            "accent_soft": "rgba(216,197,139,.16)",
            "border": "#e8d9a8",
            "glow": "rgba(220,190,100,.22)",
            "symbol": "◈",
            "texture": "plain",
            "faction": "unknown",
        }
    return dict(theme)


def _build_low_scene(pathway_key: str, sequence: int) -> AscensionScene:
    """生成序列 9–5 的完整入门经历，不参与任何随机判定。"""
    pathway = pathways_mod.get_pathway(pathway_key)
    motif = _MOTIFS[pathway_key]
    name = pathways_mod.seq_name(pathway, sequence)
    if sequence == 9:
        text = (
            f"你饮下「{name}」魔药，第一次真正踏入{pathway['name']}途径。"
            f"冰冷的灵性沿着血管展开，{motif['image']}在短暂的眩晕中一闪而过。"
            f"从这一刻起，你开始听懂{motif['core']}留下的细微信号，也明白非凡世界已经不会再轻易放你离开。"
        )
    elif sequence == 8:
        text = (
            f"魔药完成初步消化后，你晋升为「{name}」。这一次，{motif['sign']}不再只是偶然出现的异象，"
            f"而逐渐变成你判断危险、使用能力和约束自身的尺度。你仍会畏惧未知，"
            f"但已经学会在{motif['domain']}的阴影边缘保持清醒。"
        )
    elif sequence == 7:
        text = (
            f"你在一次次扮演与试探中晋升为「{name}」。{motif['core']}开始改变你的习惯，"
            f"让某些原本需要仪式和准备的能力变得近乎本能。力量第一次真正进入你的日常，"
            f"而你也第一次察觉，角色与自我之间的界线正在悄悄移动。"
        )
    elif sequence == 6:
        text = (
            f"当「{name}」的魔药在体内稳定下来，你不再只是借用这条途径的技巧。"
            f"{motif['image']}开始反复出现在梦境与灵视里，{motif['sign']}也会在你动用力量前先一步浮现。"
            f"你获得了足以改变一场遭遇的能力，也必须承担每一次出手留下的回声。"
        )
    elif sequence == 5:
        text = (
            f"你完成仪式，晋升为「{name}」。序列中段的最后一道门在身后合拢，"
            f"{motif['core']}由零散能力凝结成清晰道路。你开始能够主动塑造{motif['domain']}的局势，"
            f"也清楚看见前方那条通往半神的界线——越过它，凡人的尺度将不再适用于你。"
        )
    else:
        raise KeyError(f"序列{sequence}不属于低序列场景")
    theme = pathway_visual_theme(pathway_key)
    return AscensionScene(
        pathway_key,
        sequence,
        f"standard_seq{sequence}",
        f"序列{sequence} · {name}",
        text,
        motif["core"],
        theme["visual_theme"],
    )


def _build_high_scene(pathway_key: str, sequence: int) -> AscensionScene:
    pathway = pathways_mod.get_pathway(pathway_key)
    motif = _MOTIFS[pathway_key]
    name = pathways_mod.seq_name(pathway, sequence)
    if sequence == 4:
        text = (
            f"你饮下最后一份属于半神门槛的魔药，{motif['image']}在意识深处裂开。"
            f"{motif['core']}第一次不再只是远方的象征，而在你的血肉与灵性中同时回应。"
            f"当{motif['sign']}响起，凡人的世界已经无法完整容纳你。你晋升为「{name}」，"
            f"开始触及{motif['domain']}真正的权柄。"
        )
    elif sequence == 3:
        text = (
            f"「{name}」的晋升没有带来单纯的力量增长，而是让{motif['core']}向周围展开。"
            f"你所经过的地方开始留下属于{motif['domain']}的痕迹：{motif['sign']}不再只是预兆，"
            f"而成为现实对你的回应。你第一次以近乎天使的视角俯瞰自身，明白自己已经站在凡俗秩序之外。"
        )
    elif sequence == 2:
        text = (
            f"当你晋升为「{name}」，{motif['domain']}不再只是你借来的工具。"
            f"{motif['image']}穿过梦境、历史或现实的缝隙，在你身后投下真正的领域。"
            f"从这一年起，{motif['sign']}会先于你的意志发生；你开始改写周围世界，而不是仅仅在世界中求生。"
        )
    else:
        text = (
            f"你晋升为「{name}」，距离途径的顶点只剩最后一道无法与他人共享的门。"
            f"{motif['core']}在你体内收束成唯一的声音，{motif['image']}仿佛已经成为你的另一颗心脏。"
            f"你逐渐明白，下一次晋升不会只是获得更高的序列，而是决定你究竟还能不能继续称自己为‘你’。"
        )
    theme = pathway_visual_theme(pathway_key)
    return AscensionScene(pathway_key, sequence, f"standard_seq{sequence}", f"序列{sequence} · {name}", text, motif["core"], theme["visual_theme"])


def _build_final_scene(pathway_key: str, mode: str) -> AscensionScene:
    pathway = pathways_mod.get_pathway(pathway_key)
    motif = _MOTIFS[pathway_key]
    seq0 = pathways_mod.seq0_name(pathway)
    theme = pathway_visual_theme(pathway_key)
    if mode == "standard_god":
        title = f"序列0 · {seq0} · 登神"
        text = (
            f"最后的仪式终于完成。{motif['core']}在你体内归于同一个中心，"
            f"「{seq0}」之名不再是被你借用的称号，而成为{motif['domain']}本身对你的回应。"
            f"{motif['sign']}在世界各处同时出现，凡人第一次意识到某个新的神性已经拥有了自己的位置。"
            f"你登临序列0，成为此世真神。"
        )
    elif mode == "adjacent_seq0_devour":
        title = f"序列0 · {seq0} · 相邻序列吞噬"
        text = (
            f"登神的仪式本应在这里结束，但你没有松手。你抓住相邻途径的序列0，"
            f"将那份不属于你的神性拖入{motif['core']}的核心。两套权柄彼此排斥又互相咬合，"
            f"你的名字、历史与「{seq0}」的边界开始重叠。{motif['image']}因此裂成两种颜色，"
            f"世界再也无法把你归类为单纯的真神。你吞噬了相邻途径的序列0，向旧日坍缩。"
        )
    elif mode == "source_essence_devour":
        title = f"序列0 · {seq0} · 源质吞噬"
        text = (
            f"你抵达了外神途径能够抵达的尽头。尽头没有王座，只有{motif['core']}深处沉睡的源质。"
            f"你主动打开最后的缝隙，让源质灌入灵魂；它先吞掉你的名字，再吞掉记忆和边界。"
            f"{motif['sign']}从星空落入你的身体，你不再只是驾驭{motif['domain']}，而成为它在现实中的裂口。"
            f"你吞噬了途径源质，成为常理之外的旧日。"
        )
    elif mode == "outer_terminus":
        title = f"序列0 · {seq0} · 外神终点"
        text = (
            f"你抵达了外神途径的尽头。没有晋升阶梯，也没有可以握住的王座，只有{motif['core']}从你的身后逐层合拢。"
            f"你看见过去被改写成一段不属于你的历史，{motif['image']}在现实表面留下无法解释的缺口。"
            f"直到最后你才明白，所谓终点不是得到更高的力量，而是世界失去解释你的能力。你成为旧日。"
        )
    else:
        raise KeyError(f"未知终局模式：{mode}")
    return AscensionScene(pathway_key, 0, mode, title, text, motif["core"], theme["visual_theme"], "key")


ASCENSION_SCENES: dict[str, dict[int, AscensionScene]] = {
    key: {
        sequence: (
            _build_low_scene(key, sequence)
            if sequence in LOW_SEQUENCES
            else _build_high_scene(key, sequence)
        )
        for sequence in ASCENSION_SEQUENCES
    }
    for key in pathways_mod.ALL_PATHWAYS
}

FINAL_SCENES: dict[str, dict[str, AscensionScene]] = {
    key: {mode: _build_final_scene(key, mode) for mode in ASCENSION_MODES}
    for key in pathways_mod.ALL_PATHWAYS
}


def get_ascension_scene(pathway_key: str, sequence: int) -> AscensionScene:
    if sequence == 0:
        return get_final_scene(pathway_key, "standard_god")
    try:
        return ASCENSION_SCENES[pathway_key][sequence]
    except KeyError as exc:
        raise KeyError(f"缺少途径 {pathway_key} 的序列{sequence}晋升文案") from exc


def get_final_scene(pathway_key: str, mode: str) -> AscensionScene:
    try:
        return FINAL_SCENES[pathway_key][mode]
    except KeyError as exc:
        raise KeyError(f"缺少途径 {pathway_key} 的终局模式 {mode}") from exc


def validate_ascension_catalog() -> list[str]:
    errors: list[str] = []
    expected = set(pathways_mod.ALL_PATHWAYS)
    if set(_MOTIFS) != expected:
        errors.append("途径意象目录与 ALL_PATHWAYS 不一致")
    if set(PATHWAY_THEMES) != expected:
        errors.append("途径视觉主题目录与 ALL_PATHWAYS 不一致")
    if set(ASCENSION_SCENES) != expected or set(FINAL_SCENES) != expected:
        errors.append("晋升场景目录与 ALL_PATHWAYS 不一致")
    for key in expected:
        for sequence in ASCENSION_SEQUENCES:
            scene = ASCENSION_SCENES.get(key, {}).get(sequence)
            if scene is None or not scene.text or scene.sequence != sequence:
                errors.append(f"{key} 缺少序列{sequence}场景")
        for mode in ASCENSION_MODES:
            scene = FINAL_SCENES.get(key, {}).get(mode)
            if scene is None or not scene.text or scene.sequence != 0:
                errors.append(f"{key} 缺少终局模式 {mode}")
        theme = PATHWAY_THEMES.get(key, {})
        for field in ("accent", "accent_soft", "border", "glow", "symbol", "texture", "visual_theme", "faction"):
            if not theme.get(field):
                errors.append(f"{key} 缺少主题字段 {field}")
    return errors
