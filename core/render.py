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
    width: 640px;
    padding: 36px 40px;
    font-family: "Noto Sans SC", "Microsoft YaHei", sans-serif;
    color: #ddd8cc;
    background: linear-gradient(165deg, #14161c 0%, #23262f 40%, #171a21 100%);
    border-radius: 20px;
  }}
  .card {{
    border: 1px solid rgba(200, 178, 120, 0.35);
    border-radius: 16px;
    padding: 28px 26px;
    background: rgba(16, 18, 24, 0.6);
    box-shadow: 0 0 42px rgba(120, 130, 160, 0.14);
  }}
  .title {{
    font-size: 30px;
    font-weight: 700;
    color: #d8c48e;
    letter-spacing: 3px;
    margin-bottom: 14px;
  }}
  .hline {{ font-size: 14px; color: #9aa2b4; margin-bottom: 4px; }}
  .sep {{ height: 14px; border-top: 1px dashed rgba(200,178,120,0.22); margin: 14px 0 10px; }}
  .line {{ font-size: 15.5px; line-height: 1.7; white-space: pre-wrap; word-break: break-all; color: #c9c5ba; }}
  .line-birth {{ color: #b9c2d4; }}
  .line-youth {{ color: #aab4c6; }}
  .line-key {{ color: #e4d3a2; }}
  .line-acting {{ color: #9db98d; }}
  .line-crisis {{ color: #c98a8a; }}
  .line-meta {{ color: #8b93a6; font-style: italic; }}
  .ending {{ margin-top: 16px; font-size: 20px; font-weight: 700; color: #e4d3a2; }}
  .etext {{ font-size: 15px; line-height: 1.7; color: #cfcabd; margin-top: 6px; }}
  .note {{ margin-top: 10px; font-size: 13.5px; color: #9aa2b4; }}
  .footer {{ margin-top: 18px; font-size: 12px; color: #7d8496; border-top: 1px dashed rgba(200,178,120,0.25); padding-top: 12px; }}
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
