"""排行榜持久化（JSON，按群隔离）。"""
from __future__ import annotations

import json
import os
import time


def empty_group() -> dict:
    return {"users": {}, "updated_at": 0.0}


def load_group_data(path: str) -> dict:
    """读取群数据文件；不存在或损坏时返回空结构。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return empty_group()
        if not isinstance(data.get("users"), dict):
            data["users"] = {}
        return data
    except (OSError, ValueError):
        return empty_group()


def save_group_data(path: str, data: dict) -> None:
    """原子写入：先写临时文件再替换。"""
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    tmp_path = os.path.join(directory, f".{os.path.basename(path)}.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp_path, path)


def _user(data: dict, user_id: str, name: str, now: float) -> dict:
    users = data.setdefault("users", {})
    user = users.get(user_id)
    if user is None:
        user = {
            "name": name or "群友",
            "best_score": 0,
            "best_seq": None,
            "best_ending": "",
            "god_count": 0,
            "plays": 0,
            "updated_at": now,
        }
        users[user_id] = user
    if name:
        user["name"] = name
    return user


def record_play(
    data: dict,
    user_id: str,
    name: str,
    score: int,
    final_seq: int | None,
    ending_title: str,
    is_god: bool,
    now: float | None = None,
) -> dict:
    """记录一次人生并刷新个人最佳；返回更新后的用户摘要。"""
    now = now or time.time()
    user = _user(data, user_id, name, now)
    user["plays"] = int(user.get("plays", 0)) + 1
    if is_god:
        user["god_count"] = int(user.get("god_count", 0)) + 1
    if score > int(user.get("best_score", 0)):
        user["best_score"] = score
        user["best_seq"] = final_seq
        user["best_ending"] = ending_title
    user["updated_at"] = now
    data["updated_at"] = now
    return dict(user)


def _seq_sort_key(row: dict):
    """排行榜排序键：评分降序；序列数字越小越强（旧日=-1 最强，凡人最弱）。"""
    seq = row.get("best_seq")
    seq_rank = 99 if seq is None else int(seq)
    return (int(row.get("best_score", 0)), -seq_rank)


def ranking(data: dict, limit: int = 10) -> list[dict]:
    """返回排行榜行（按最佳评分降序），附字段 rank_seq/score。"""
    users = data.get("users", {})
    rows = []
    for uid, user in users.items():
        rows.append(
            {
                "user_id": uid,
                "name": user.get("name", "群友"),
                "best_score": int(user.get("best_score", 0)),
                "best_seq": user.get("best_seq"),
                "best_ending": user.get("best_ending", ""),
                "god_count": int(user.get("god_count", 0)),
                "plays": int(user.get("plays", 0)),
            }
        )
    rows.sort(key=_seq_sort_key, reverse=True)
    return rows[: max(1, limit)]


def seq_display(seq: int | None) -> str:
    """排行榜上的序列显示。"""
    if seq is None:
        return "凡人"
    if seq == -1:
        return "旧日"
    if seq == 0:
        return "序列0·登神"
    return f"序列{seq}"
