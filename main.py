"""赛博诡秘插件：诡秘之主主题的人生重开模拟器。"""
from __future__ import annotations

import os
import random
import time

from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star

from .core import engine, events, pathways, storage
from .core.commands import choose_random_build, normalize_seed, remainder_from_text
from .core.narrative import summarize_life
from .core.render import build_choice_html_pages, build_life_html_pages

_HELP_TEXT = """🌫️ 赛博诡秘 · 诡秘人生重开使用说明

/诡秘 重开
    开启捏人式开局：先选出身，再选天赋，随即跑完一生
/诡秘 重开 随机 [种子]
    全随机一键到底，听天由命；可带种子复现
/诡秘 重开 <出身> <天赋> [种子]
    老手直选：如 /诡秘 重开 廷根 灵视 12345
/诡秘 选 编号|名称|随机
    回答当前选择点（90 秒内有效）
/诡秘 出身 / 诡秘 天赋
    查看全部可选出身与天赋
/诡秘 途径 [名称]
    途径图鉴；带名称查看详情与序列
/诡秘 天骄榜
    本群最强人生排行
/诡秘 帮助
    查看本说明

玩法：非凡接触 → 饮下魔药 → 扮演消化 → 爬升序列。
疯狂值越高越容易失控；扮演得法则登临序列0。
种子系统：同一出身 + 同一天赋 + 同一种子 = 同一段人生。
纯属娱乐，与真实神秘学无关。"""

_ORIGIN_HEADER = "🌫️ 诡秘人生 · 第一步，选择你的出身"
_TALENT_HEADER = "🌫️ 诡秘人生 · 第二步，选择你的天赋"
_CHOOSE_TIP = "回复 /诡秘 选 编号 或名称 · /诡秘 选 随机 听天由命"

class _Pending:
    """一个进行中的捏人选择。"""

    __slots__ = ("expires", "origin_key", "stage")

    def __init__(self, stage: str, origin_key: str | None, expires: float):
        self.stage = stage  # "origin" | "talent"
        self.origin_key = origin_key
        self.expires = expires


class CyberMystery(Star):
    """赛博诡秘：诡秘世界的人生重开模拟器。"""

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self._groups: dict[str, dict] = {}
        self._dirty: set[str] = set()
        self._last_save = 0.0
        self._ops_since_save = 0
        self._rng = random.Random()
        self._pending: dict[str, _Pending] = {}

    # ---------- 工具 ----------

    def _cfg(self, key: str, default):
        try:
            return self.config.get(key, default)
        except Exception:
            return default

    def _data_dir(self) -> str:
        try:
            base = getattr(self.context, "data_dir", None) or "data"
        except Exception:
            base = "data"
        return os.path.join(base, "plugins", "cyber_mystery")

    def _sender_id(self, event: AstrMessageEvent) -> str:
        try:
            return str(event.get_sender_id() or "")
        except Exception:
            return ""

    def _sender_name(self, event: AstrMessageEvent) -> str:
        try:
            return (event.get_sender_name() or "").strip()
        except Exception:
            return ""

    def _group_key(self, event: AstrMessageEvent) -> str:
        try:
            gid = event.get_group_id() or ""
        except Exception:
            gid = ""
        if gid:
            return str(gid)
        return "dm_" + (self._sender_id(event) or "unknown")

    def _remainder(self, event: AstrMessageEvent) -> str:
        """去掉唤醒前缀、命令组和子命令词，返回剩余参数。"""
        try:
            return remainder_from_text(event.get_message_str())
        except Exception:
            return ""

    def _timeout(self) -> float:
        try:
            return max(30.0, float(self._cfg("choose_timeout_seconds", 90)))
        except Exception:
            return 90.0

    # ---------- 群数据 ----------

    def _group_data(self, key: str) -> dict:
        data = self._groups.get(key)
        if data is None:
            path = os.path.join(self._data_dir(), f"{key}.json")
            data = storage.load_group_data(path)
            self._groups[key] = data
        return data

    def _flush(self, force: bool = False) -> None:
        if not self._dirty:
            return
        now = time.time()
        if not force and now - self._last_save < 30 and self._ops_since_save < 20:
            return
        base = self._data_dir()
        saved: set[str] = set()
        for key in list(self._dirty):
            try:
                storage.save_group_data(
                    os.path.join(base, f"{key}.json"),
                    self._groups.get(key, storage.empty_group()),
                )
                saved.add(key)
            except Exception as e:
                logger.warning(f"cyber_mystery 保存群数据失败 {key}: {e}")
        self._dirty.difference_update(saved)
        self._last_save = now
        self._ops_since_save = 0

    # ---------- 选择状态机 ----------

    def _pending_key(self, event: AstrMessageEvent) -> str:
        return f"{event.unified_msg_origin}:{self._sender_id(event)}"

    def _get_pending(self, event: AstrMessageEvent) -> _Pending | None:
        key = self._pending_key(event)
        pending = self._pending.get(key)
        if pending is None:
            return None
        if time.time() > pending.expires:
            self._pending.pop(key, None)
            return None
        return pending

    def _set_pending(self, event: AstrMessageEvent, pending: _Pending) -> None:
        self._pending[self._pending_key(event)] = pending
        # 顺手清理过期项，防内存缓慢增长
        now = time.time()
        for k in [k for k, p in self._pending.items() if now > p.expires]:
            self._pending.pop(k, None)

    @staticmethod
    def _match_option(token: str, items: dict[str, dict]) -> str | None:
        """按序号或名称子串匹配可选项。"""
        token = token.strip()
        if not token:
            return None
        if token.isdigit():
            idx = int(token)
            if 1 <= idx <= len(items):
                return list(items)[idx - 1]
        for key, item in items.items():
            name = item["name"]
            if token == name or token in name or name in token:
                return key
        # 支持只打关键词（如 "贫民窟" → 贝克兰德东区贫民窟）
        for key, item in items.items():
            if len(token) >= 2 and token in item["name"]:
                return key
        return None

    @staticmethod
    def _format_options(header: str, items: dict[str, dict], field: str) -> str:
        lines = [header, ""]
        for i, item in enumerate(items.values(), 1):
            lines.append(f"{i}. {item['name']}——{item[field]}")
        lines.append("")
        lines.append(_CHOOSE_TIP)
        return "\n".join(lines)

    async def _option_results(
        self,
        event: AstrMessageEvent,
        header: str,
        items: dict[str, dict],
        field: str,
        kind: str,
    ):
        """输出选择卡片；图片不可用时保持文本交互。"""
        if self._cfg("use_image", False):
            try:
                for page in build_choice_html_pages(kind, header, items):
                    url = await self.html_render(page, {})
                    yield event.image_result(url)
                return
            except Exception as e:
                logger.warning(f"cyber_mystery 选择卡片渲染失败，回退纯文本: {e}")
        yield event.plain_result(self._format_options(header, items, field))

    # ---------- 人生输出 ----------

    async def _finish_life(self, event: AstrMessageEvent, result: dict):
        """渲染人生结果：默认文本，可选图卡，失败回退。"""
        player = self._sender_name(event)
        view = summarize_life(result, player)
        body = engine.format_life(result, player, view=view)
        # 记录排行榜
        key = self._group_key(event)
        data = self._group_data(key)
        storage.record_play(
            data,
            self._sender_id(event) or "unknown",
            player,
            result["score"],
            -1 if result["category"] == "eldritch" else result["final_seq"],
            result["ending_title"],
            result["category"] in ("god", "eldritch"),
        )
        self._dirty.add(key)
        self._ops_since_save += 1
        self._flush()
        if self._cfg("use_image", False):
            try:
                for page in build_life_html_pages(narrative=view):
                    url = await self.html_render(page, {})
                    yield event.image_result(url)
                return
            except Exception as e:
                logger.warning(f"cyber_mystery 图片渲染失败，回退纯文本: {e}")
        yield event.plain_result(body)

    def _run_life(
        self,
        event: AstrMessageEvent,
        origin_key: str,
        talent_key: str,
        seed: str | int | None = None,
        rng: random.Random | None = None,
    ):
        """跑一局人生并返回待输出的异步生成器；seed 非空时使用确定性随机源。"""
        seed = normalize_seed(seed)
        if rng is None:
            rng = random.Random(seed) if seed is not None else self._rng
        result = engine.simulate(rng, origin_key, talent_key)
        if seed is not None:
            result = {**result, "seed": seed}
        return self._finish_life(event, result)

    # ---------- 命令组 ----------

    @filter.command_group("mystery", alias={"诡秘", "guimi"})
    def mystery():
        """赛博诡秘：/诡秘 重开|选|途径|出身|天赋|天骄榜|帮助"""

    @mystery.command("help", alias={"帮助", "菜单"})
    async def help_cmd(self, event: AstrMessageEvent):
        """查看赛博诡秘使用说明"""
        yield event.plain_result(_HELP_TEXT)

    @mystery.command("restart", alias={"重开", "人生", "kaishi"})
    async def restart_cmd(self, event: AstrMessageEvent):
        """诡秘人生重开。用法：/诡秘 重开 [随机 [种子]|出身 天赋 [种子]]"""
        args = self._remainder(event).split()
        if not args:
            # 捏人流程：先选出身
            self._set_pending(
                event, _Pending("origin", None, time.time() + self._timeout())
            )
            async for result in self._option_results(
                event, _ORIGIN_HEADER, events.ORIGINS, "desc", "origin"
            ):
                yield result
            return
        if args[0] in {"随机", "random", "随便"}:
            seed = args[1] if len(args) >= 2 else None
            normalized_seed = normalize_seed(seed)
            rng = random.Random(normalized_seed) if normalized_seed is not None else self._rng
            origin_key, talent_key = choose_random_build(
                rng, events.ORIGINS, events.TALENTS
            )
            async for result in self._run_life(
                event, origin_key, talent_key, normalized_seed, rng
            ):
                yield result
            return
        # 直选模式：<出身> [天赋 [种子]]
        origin_key = self._match_option(args[0], events.ORIGINS)
        if not origin_key:
            yield event.plain_result(
                "没有匹配到这个出身，用 /诡秘 出身 查看全部可选。"
            )
            return
        if len(args) >= 2:
            talent_key = self._match_option(args[1], events.TALENTS)
            if not talent_key:
                yield event.plain_result(
                    "没有匹配到这个天赋，用 /诡秘 天赋 查看全部可选。"
                )
                return
            seed = args[2] if len(args) >= 3 else None
            async for result in self._run_life(event, origin_key, talent_key, seed):
                yield result
            return
        # 只选了出身：进入天赋选择
        self._set_pending(
            event, _Pending("talent", origin_key, time.time() + self._timeout())
        )
        async for result in self._option_results(
            event, _TALENT_HEADER, events.TALENTS, "desc", "talent"
        ):
            yield result

    @mystery.command("choose", alias={"选", "选择"})
    async def choose_cmd(self, event: AstrMessageEvent):
        """回答当前选择点。用法：/诡秘 选 编号|名称|随机"""
        pending = self._get_pending(event)
        if pending is None:
            yield event.plain_result("当前没有进行中的选择，用 /诡秘 重开 开始新的人生。")
            return
        token = self._remainder(event).split()[0] if self._remainder(event) else ""
        if not token:
            yield event.plain_result("请回复 /诡秘 选 编号、名称或 随机。")
            return
        items = events.ORIGINS if pending.stage == "origin" else events.TALENTS
        key: str | None
        if token in {"随机", "random", "随便"}:
            key = self._rng.choice(list(items))
        else:
            key = self._match_option(token, items)
        if not key:
            yield event.plain_result(
                "没有匹配到这个选项，回复 /诡秘 选 编号、名称或 随机。"
            )
            return
        if pending.stage == "origin":
            self._set_pending(
                event, _Pending("talent", key, time.time() + self._timeout())
            )
            async for result in self._option_results(
                event, _TALENT_HEADER, events.TALENTS, "desc", "talent"
            ):
                yield result
            return
        self._pending.pop(self._pending_key(event), None)
        async for result in self._run_life(event, pending.origin_key, key):
            yield result

    @mystery.command("origin", alias={"出身", "地点"})
    async def origin_cmd(self, event: AstrMessageEvent):
        """查看全部可选出身"""
        async for result in self._option_results(
            event, "🌫️ 可选出身一览", events.ORIGINS, "desc", "origin"
        ):
            yield result

    @mystery.command("talent", alias={"天赋", "才能"})
    async def talent_cmd(self, event: AstrMessageEvent):
        """查看全部可选天赋"""
        async for result in self._option_results(
            event, "🌫️ 可选天赋一览", events.TALENTS, "desc", "talent"
        ):
            yield result

    @mystery.command("pathway", alias={"途径", "图鉴"})
    async def pathway_cmd(self, event: AstrMessageEvent):
        """途径图鉴。用法：/诡秘 途径 [名称]"""
        token = self._remainder(event)
        if not token:
            lines = ["🌫️ 诡秘途径图鉴", "", "◆ 正规途径"]
            for i, p in enumerate(pathways.PATHWAYS.values(), 1):
                secret = " · 隐秘" if p.get("secret") else ""
                lines.append(f"{i}. {p['name']}途径（{p['faction']}）{secret}")
            lines.append("")
            lines.append("◆ 外神途径（常理之外）")
            lines.append("⚠️ 正常人生无法踏足，唯有携带特定天赋者可能被引上")
            for p in pathways.OUTER_PATHWAYS.values():
                lines.append(f"· {p['name']}（{p['faction']}）")
            lines.append("")
            lines.append("查看详情：/诡秘 途径 名称（如 /诡秘 途径 愚者）")
            yield event.plain_result("\n".join(lines))
            return
        target = self._match_option(token, pathways.ALL_PATHWAYS)
        if not target:
            yield event.plain_result("没有匹配到这个途径，用 /诡秘 途径 查看全部。")
            return
        p = pathways.ALL_PATHWAYS[target]
        lines = [f"🌫️ {p['name']}途径", f"所属：{p['faction']}", "", p["desc"], ""]
        if target in pathways.OUTER_PATHWAYS:
            lines.insert(1, "⚠️ 来自外神：常规人生无法踏足")
        if p.get("sequences"):
            lines.append("序列阶梯（序列9 → 序列0）：")
            for seq in range(9, -1, -1):
                name = p["sequences"].get(seq)
                if not name:
                    continue
                lines.append(f"  序列{seq} · {name}")
                acting = p.get("acting", {}).get(seq)
                if acting:
                    lines.append(f"    扮演要点：{acting}")
            gaps = [s for s in range(9, -1, -1) if s not in p["sequences"]]
            if gaps:
                lines.append(f"  （序列{'、'.join(map(str, gaps))} 待考）")
        else:
            lines.append("（此途径的序列阶梯尚未被完全记录……）")
        yield event.plain_result("\n".join(lines))

    @mystery.command("rank", alias={"天骄榜", "排行榜", "排行"})
    async def rank_cmd(self, event: AstrMessageEvent):
        """本群最强人生排行"""
        key = self._group_key(event)
        data = self._group_data(key)
        rows = storage.ranking(data, int(self._cfg("ranking_size", 10)))
        if not rows:
            yield event.plain_result("还没有人重开过人生，/诡秘 重开 抢占榜首！")
            return
        lines = ["🌫️ 天骄榜 · 本群最强人生", ""]
        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        for i, row in enumerate(rows, 1):
            god = f" · 登神×{row['god_count']}" if row["god_count"] else ""
            lines.append(
                f"{medals.get(i, f'{i}.')} {row['name']} "
                f"{storage.seq_display(row['best_seq'])} · {row['best_score']}分"
                f" ·「{row['best_ending']}」{god}"
            )
        lines.append("")
        lines.append(f"累计 {len(data.get('users', {}))} 人重开 · /诡秘 重开 迎战")
        yield event.plain_result("\n".join(lines))

    async def terminate(self):
        self._flush(force=True)
        logger.info("cyber_mystery 插件已停止")
