"""与 AstrBot 无关的命令文本解析工具。"""
from __future__ import annotations

import random
from collections.abc import Mapping


GROUP_WORDS = {"mystery", "诡秘", "guimi"}
SUB_WORDS = {
    "help", "帮助", "菜单",
    "restart", "重开", "人生", "kaishi",
    "choose", "选", "选择",
    "origin", "出身", "地点",
    "talent", "天赋", "才能",
    "pathway", "途径", "图鉴",
    "rank", "天骄榜", "排行榜", "排行",
}


def remainder_from_text(text: str) -> str:
    """去掉唤醒前缀、命令组和子命令词，返回剩余参数。"""
    tokens = text.strip().split()
    if tokens and tokens[0].startswith(("/", "／", "@")):
        tokens = tokens[1:]
    command_words = GROUP_WORDS | SUB_WORDS
    dropped = 0
    while tokens and dropped < 2:
        token = tokens[0].strip("，,。.！!？?")
        if token.lower() not in command_words:
            break
        tokens = tokens[1:]
        dropped += 1
    return " ".join(tokens).strip()


def normalize_seed(seed: object) -> str | int | None:
    """把纯数字字符串种子转成 int，保证各入口的随机序列一致。"""
    if seed is None:
        return None
    try:
        return int(str(seed))
    except (ValueError, TypeError):
        return str(seed)


def choose_random_build(
    rng: random.Random,
    origins: Mapping[str, object],
    talents: Mapping[str, object],
) -> tuple[str, str]:
    """从同一个随机源抽取随机开局，便于种子完整复现。"""
    return rng.choice(list(origins)), rng.choice(list(talents))
