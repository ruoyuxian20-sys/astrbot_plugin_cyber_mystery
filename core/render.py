"""人生结果图文卡片渲染（可选功能，渲染失败时主插件会回退到纯文本）。"""
from __future__ import annotations

import html as _html

# 事件行配色：灰雾中的不同回响
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


def _esc(value: str) -> str:
    """HTML 转义，防止文本破坏卡片。"""
    return _html.escape(value or "", quote=True)


def build_life_html(
    header_lines: list[str],
    body_lines: list[tuple[str, str]],  # (kind, text with age prefix)
    ending_title: str,
    ending_text: str,
    seq_note: str,
    footer: str,
) -> str:
    """把一段诡秘人生渲染成灰雾暗金风格的卡片 HTML。"""
    header_html = "\n".join(
        f"<div class=\"hline\">{_esc(line)}</div>" for line in header_lines
    )
    body_html = "\n".join(
        f"<div class=\"line {_KIND_CLASS.get(kind, '')}\">{_esc(text)}</div>"
        for kind, text in body_lines
    )
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    width: 680px;
    padding: 42px 44px;
    font-family: "Noto Sans SC", "Microsoft YaHei", serif;
    color: #ded7c4;
    background:
      radial-gradient(circle at 12% 18%, rgba(120, 80, 180, 0.16) 0, transparent 34%),
      radial-gradient(circle at 88% 82%, rgba(40, 90, 140, 0.18) 0, transparent 38%),
      radial-gradient(1px 1px at 20% 30%, #d9c48a 50%, transparent 51%),
      radial-gradient(1px 1px at 70% 20%, #b9a6e0 50%, transparent 51%),
      radial-gradient(1px 1px at 85% 55%, #8fd0e8 50%, transparent 51%),
      radial-gradient(1px 1px at 35% 75%, #e0b48a 50%, transparent 51%),
      linear-gradient(160deg, #0b0d16 0%, #151225 45%, #0a101c 100%);
    background-size: auto, auto, 90px 90px, 110px 110px, 130px 130px, 100px 100px, auto;
    border-radius: 24px;
  }}
  .card {{
    border: 1px solid rgba(210, 180, 100, 0.55);
    border-radius: 20px;
    padding: 32px 30px;
    background: rgba(8, 10, 18, 0.78);
    box-shadow:
      0 0 60px rgba(100, 70, 180, 0.18),
      0 0 24px rgba(210, 180, 100, 0.08),
      inset 0 0 60px rgba(30, 20, 60, 0.25);
  }}
  .title {{
    font-size: 32px;
    font-weight: 700;
    color: #e6c878;
    text-align: center;
    letter-spacing: 6px;
    text-shadow: 0 0 18px rgba(230, 200, 120, 0.35);
    margin-bottom: 18px;
    padding-bottom: 14px;
    border-bottom: 1px solid rgba(210, 180, 100, 0.35);
  }}
  .title::before {{ content: "✦ "; color: #b3924a; }}
  .title::after {{ content: " ✦"; color: #b3924a; }}
  .hline {{
    font-size: 14px;
    color: #b8ac92;
    margin: 5px 0;
    padding: 2px 10px;
    border-left: 2px solid rgba(210, 180, 100, 0.3);
  }}
  .sep {{
    height: 1px;
    margin: 18px 0 14px;
    background: linear-gradient(90deg, transparent, rgba(210,180,100,0.5), transparent);
  }}
  .line {{
    display: block;
    font-size: 15.5px;
    line-height: 1.75;
    white-space: pre-wrap;
    word-break: break-word;
    color: #cfc8b8;
    margin: 7px 0;
    padding: 8px 14px 8px 18px;
    border-left: 2px solid rgba(210, 180, 100, 0.4);
    border-radius: 0 10px 10px 0;
    background: linear-gradient(90deg, rgba(210, 180, 100, 0.09), transparent 72%);
  }}
  .line-birth {{ color: #c3c9dd; border-left-color: #7f8db5; }}
  .line-youth {{ color: #aab4cc; border-left-color: #7a86a8; }}
  .line-key {{ color: #e6d5a0; border-left-color: #d4af55; }}
  .line-key::before {{ content: "◈ "; color: #b3924a; }}
  .line-acting {{ color: #a8c89a; border-left-color: #7fa872; }}
  .line-acting::before {{ content: "✧ "; color: #7fa872; }}
  .line-crisis {{ color: #d49a8a; border-left-color: #b35d4a; }}
  .line-crisis::before {{ content: "☠ "; color: #b35d4a; }}
  .line-meta {{ color: #9a8fb0; border-left-color: #7a6b96; font-style: italic; }}
  .line-meta::before {{ content: "☾ "; color: #7a6b96; }}
  .ending {{
    margin-top: 20px;
    font-size: 22px;
    font-weight: 700;
    color: #e6c878;
    text-align: center;
    letter-spacing: 3px;
    padding: 12px 0;
    border-top: 1px solid rgba(210,180,100,0.35);
    border-bottom: 1px solid rgba(210,180,100,0.35);
  }}
  .etext {{
    font-size: 15.5px;
    line-height: 1.8;
    color: #d6cfc0;
    margin-top: 10px;
    padding: 0 8px;
    text-align: center;
  }}
  .note {{ margin-top: 14px; font-size: 14px; color: #b8ac92; text-align: center; }}
  .footer {{
    margin-top: 18px;
    font-size: 12.5px;
    color: #8d8496;
    text-align: center;
    border-top: 1px dashed rgba(210,180,100,0.3);
    padding-top: 12px;
  }}
</style>
</head>
<body>
<div class="card">
  <div class="title">🌫️ 诡秘人生 · 第五纪</div>
  {header_html}
  <div class="sep"></div>
  {body_html}
  <div class="ending">【结局】{_esc(ending_title)}</div>
  <div class="etext">{_esc(ending_text)}</div>
  <div class="note">{_esc(seq_note)}</div>
  <div class="footer">{_esc(footer)}</div>
</div>
</body>
</html>"""
