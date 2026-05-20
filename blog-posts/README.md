# LLM Observatory — Blog Post Series

6-post series for Medium / Substack. Each post is a standalone piece. Together they form a complete practitioner case study.

**Tone:** First-person engineering retrospective. Not a tutorial. Not a product pitch.
**Target:** Mixed — Engineering leaders (CTO, EM) + practitioners (Staff Eng, MLOps, Platform Eng).

---

## Series Arc

| File | Post title | Pillar | Primary audience |
|---|---|---|---|
| `01-silent-degradation-problem.md` | Your LLM Feature Is Degrading Right Now and You Probably Don't Know It | Problem and failure mode | CTO, EM |
| `02-architecture-gateway-ingest.md` | How I Structured the LLM Observatory: Gateway, Ingest, and Why the Boundary Matters | Architecture and component boundaries | Staff Eng, EM, Platform Eng |
| `03-design-decisions-why-a-over-b.md` | Three Design Decisions in LLM Observatory and Why I Made Them | Design decisions (why A over B) | Staff Eng, MLOps |
| `04-evaluation-as-operational-signal.md` | Evaluation Is Not a Pre-Deploy Step. It Is a Production Signal. | Validation run and measured outputs | MLOps, EM |
| `05-security-controls-and-tradeoffs.md` | Security in an LLM Observability Platform: Controls, Tradeoffs, and What Is Still Open | Security and controls | CTO, EM, Platform Eng |
| `06-deployment-readiness-and-limits.md` | What LLM Observatory Is Today and What It Would Take to Run It in Production | Deployment readiness and limits | CTO, EM |

---

## Publishing cadence (suggested)

One post per week. The arc reads well in sequence but each post is standalone enough to publish independently.

## Screenshots referenced

Source files are in `../demo/`. When publishing on Medium:

1. Upload each PNG directly via the Medium image upload button (drag-and-drop inline).
2. The image alt text in each post already describes what the screenshot shows — use it as the Medium caption.
3. Do not use relative file paths — Medium requires uploaded images, not local paths.

| Screenshot | Used in posts |
|---|---|
| `llm-observatory-dashboard.png` | 1, 4 |
| `llm-observatory-incidents.png` | 1, 4 |
| `llm-observatory-api-keys.png` | 5 |

## Medium publishing checklist

Before hitting Publish on each post:
- [ ] Upload all referenced screenshots inline at the correct position
- [ ] Remove the `*Post N of 6*` series line or replace it with a Medium series tag
- [ ] In post 6, fill in the series index with actual Medium post URLs after the earlier posts are published
- [ ] Add relevant Medium tags: `llm`, `machine-learning`, `software-engineering`, `mlops`, `observability`
- [ ] Set a subtitle in Medium (use the first sentence of each post's opening paragraph)

## QA checklist status

All 6 posts were drafted against the playbook QA checklist:
- Every claim maps to a verified file, endpoint, or screenshot
- No unverifiable metrics included
- "Production" wording is scoped precisely in every instance
- Security claims are specific (not "fully secure")
- At least one limitation disclosed per post
- One technical anchor per post (API path, architecture element, or metric)
- No full code blocks or replication walkthroughs
- Language is direct and free from hype terms
