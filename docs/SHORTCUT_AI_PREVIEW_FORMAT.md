# Shortcut AI Preview Format

Status: `CURRENT` for formatting a validated V3 response. Never show raw JSON. Prefix the screen with `AI 建議：尚未確認`.

## Standard preview

```text
標題
<suggested_title or 未提供>

一句重點
<one_sentence_insight or 未提供>

核心
• <core point 1>
• <core point 2>
• <core point 3>

為何重要
<why_it_matters or 未提供>

可立即使用
• <application 1>
• <application 2>
• <application 3>

下一步
<suggested_next_action or 未提供>

待核實
• <fact 1>
• <fact 2>

欠缺資料
• <missing item>

相關專案 / 信心
<related_project or 無> / <low|medium|high>
```

Omit empty bullet sections instead of showing `[]` or `null`.

## Short article preview

Append only when `requested_output=short_article` and the validated response contains the bounded field:

```text
AI 草稿
<short_article_draft body without the transport label>
```

Keep `AI 草稿` visible in preview and in any accepted Markdown. Human review is required before reuse or publication.

## Recommended mobile bounds

| Display field | Maximum shown before `…` | Full value handling |
|---|---:|---|
| Title | 80 characters | Keep validated full value in draft only after acceptance |
| One-sentence insight | 240 characters | Allow one expandable preview block |
| Each core/application/fact item | 180 characters | At most contract item count |
| Why/next action/missing item | 240 characters | Show `…` without mutating stored validated value |
| Standard preview total | about 1,800 characters | Offer `顯示完整預覽` if needed |
| Short article body | full validated 150–300 Chinese chars or 80–180 English words | No extra truncation needed |

The Shortcut must validate first, then format. Truncation is display-only; it must never conceal schema errors or silently change accepted Source/User content.
