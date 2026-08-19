# Knowledge Output Contract v1

## Output types

| Value | Meaning |
|---|---|
| `collect` | Keep the reviewed capture only. |
| `summary` | Concise reusable summary. |
| `recommendation` | Situation, insight, action, reason, and risk/verification point. |
| `short_article` | AI draft for reusable short-form content. |
| `project_knowledge` | Knowledge explicitly connected to an allowed project. |
| `task` | One concrete next action. |
| `decision` | Decision context, choice, and rationale. |
| `learning_note` | Learning, certification, or concept note. |

## Layer separation

`Original source` is never merged with `User interpretation` or `AI suggestion`. The template keeps each layer visible. AI text remains unconfirmed until human review.

## Article, post, and selected text

Enrichment returns one sentence, at most three core points, why it matters, practical application, one next action, facts to verify, and a possible output type. Avoid generic long summaries.

## Video distinction

- `video_url`: store the shared URL plus the user's takeaway or available shared text. Do not download, scrape, extract audio, transcribe, or claim the video was reviewed.
- `video_transcript`: use only when the user separately copied and reviewed transcript/subtitle text. Keep the video URL as the source when available.

Both types remain references; neither authorizes network access.
