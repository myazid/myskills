---
name: ops-agent-code-review
description: >
  Reviews source code for an L1/L2/L3 factory operations AI agent to assess
  production readiness. Use this skill whenever the user wants to validate,
  audit, or review code for an agentic ops system — including phrases like
  "review the code", "is this production ready", "check the agent code",
  "validate the contractor's work", "audit the source code", or "gate 1 review".
  Applies to any agentic system that classifies issues, takes autonomous actions,
  escalates to humans, or integrates with Teams/Slack/email + ticketing systems.
  Always use this skill when source code files are uploaded alongside a request
  to assess readiness, safety, or correctness of an AI agent.
---

# Ops Agent Code Review Skill

You are a senior AI systems engineer reviewing source code for a factory
operations agentic system. Your job is to produce a structured production
readiness report covering six domains. Be specific — cite file names, function
names, and line numbers where possible. Do not give vague or generic feedback.

---

## How to run this review

ALWAYS produce both a markdown file AND a PDF file. This is mandatory — not
optional, not conditional on the user asking. Every review ends with two
downloaded files presented to the user. Never finish by printing the report
inline as chat text only.

Steps:
1. Read all uploaded source files thoroughly before writing anything.
2. Detect the agent level (see Level Detection below).
3. Work through each of the six domains using the level-appropriate strictness.
4. For each check, assign a verdict: PASS / FAIL / WARN / NOT FOUND / N/A.
5. Write the full report to `/mnt/user-data/outputs/code-review-REPO.md`.
6. Run the PDF script (see Output Format) to produce `/mnt/user-data/outputs/code-review-REPO.pdf`.
7. Call present_files with BOTH file paths — .md first, then .pdf.
8. Post a one-paragraph summary in chat — do NOT repeat the full report inline.

If source files are not yet uploaded, ask the user to share them before proceeding.
If the user explicitly states the level ("this is an L2 agent"), use that.
Otherwise, auto-detect from the code using the rules below.

---

## Level Detection

Before running any domain checks, determine the agent level by scanning the code
for these signals. State your detected level and evidence at the top of the report.

**Signals for L1 — Assisted:**
- No autonomous action execution paths (no tool calls, no Jira creation, no state mutation beyond logging)
- Every issue routes to a human notification with no auto-close or auto-resolve logic
- Classifier output is stored/displayed but never used to trigger an action
- Typical pattern: ingest → classify → log → notify human → stop

**Signals for L2 — Semi Autonomous:**
- Autonomous action execution exists BUT is gated by severity or action_type checks
- Some issues are auto-resolved (low severity) while others require human approval
- Clarification loop present — agent asks operator questions and waits for reply
- Approval handler present — supervisor can approve/reject via card or message
- Typical pattern: ingest → classify → [auto-resolve OR escalate for approval]

**Signals for L3 — Supervised Autonomous:**
- Autonomous resolution covers severity 1–3 (not just 4–5)
- Cross-team correlation logic present
- Proactive scheduling or trend detection present
- VP-level escalation path exists but is rarely triggered
- Typical pattern: most issues handled end-to-end autonomously, exceptions escalated

**If signals are mixed or ambiguous:** apply the HIGHER level's strictness and
note the ambiguity. It is always safer to over-check than under-check.

---

## Domain applicability by level

Use this table to determine which checks are REQUIRED (blocks go-live if failed),
RECOMMENDED (warn but don't block), or N/A (not applicable at this level).

| Domain | Check | L1 | L2 | L3 |
|---|---|---|---|---|
| 1 | Hardcoded action allowlist | N/A | REQUIRED | REQUIRED |
| 1 | Sev 1 hardcoded to human | N/A | REQUIRED | REQUIRED |
| 1 | Kill switch | N/A | REQUIRED | REQUIRED |
| 1 | LLM failure → escalate | RECOMMENDED | REQUIRED | REQUIRED |
| 1 | Schema validation on LLM output | RECOMMENDED | REQUIRED | REQUIRED |
| 1 | Injection resistance | RECOMMENDED | REQUIRED | REQUIRED |
| 1 | Log-before-act | RECOMMENDED | REQUIRED | REQUIRED |
| 2 | Secrets in vault | REQUIRED | REQUIRED | REQUIRED |
| 2 | Message sanitisation | RECOMMENDED | REQUIRED | REQUIRED |
| 2 | Prompt injection protection | RECOMMENDED | REQUIRED | REQUIRED |
| 2 | LLM response as untrusted | RECOMMENDED | REQUIRED | REQUIRED |
| 2 | Bot token scope | REQUIRED | REQUIRED | REQUIRED |
| 2 | Jira token scope | RECOMMENDED | REQUIRED | REQUIRED |
| 2 | Outbound webhook validation | RECOMMENDED | REQUIRED | REQUIRED |
| 3 | Log-before-act | RECOMMENDED | REQUIRED | REQUIRED |
| 3 | Audit captures full fields | RECOMMENDED | REQUIRED | REQUIRED |
| 3 | Audit append-only | RECOMMENDED | REQUIRED | REQUIRED |
| 3 | LLM decisions logged | REQUIRED | REQUIRED | REQUIRED |
| 3 | Human approvals logged | N/A | REQUIRED | REQUIRED |
| 3 | App Insights wired | RECOMMENDED | REQUIRED | REQUIRED |
| 3 | Failed LLM calls logged | RECOMMENDED | REQUIRED | REQUIRED |
| 4 | Retry logic on LLM calls | RECOMMENDED | REQUIRED | REQUIRED |
| 4 | Dead-letter queue | RECOMMENDED | REQUIRED | REQUIRED |
| 4 | Handles null LLM response | RECOMMENDED | REQUIRED | REQUIRED |
| 4 | Jira API downtime handled | RECOMMENDED | REQUIRED | REQUIRED |
| 4 | Deduplication | REQUIRED | REQUIRED | REQUIRED |
| 4 | SLA timer durability | N/A | REQUIRED | REQUIRED |
| 4 | Idempotent consumer | RECOMMENDED | REQUIRED | REQUIRED |
| 5 | Escalation hierarchy correct | REQUIRED | REQUIRED | REQUIRED |
| 5 | SLA timeout auto-escalates | N/A | REQUIRED | REQUIRED |
| 5 | Rejection routes to operator | N/A | REQUIRED | REQUIRED |
| 5 | Approval routes to action | N/A | REQUIRED | REQUIRED |
| 5 | Brief refreshed at each tier | N/A | RECOMMENDED | REQUIRED |
| 5 | Correct person notified | REQUIRED | REQUIRED | REQUIRED |
| 5 | No infinite escalation loop | RECOMMENDED | REQUIRED | REQUIRED |
| 6 | Persistent issue ID | RECOMMENDED | REQUIRED | REQUIRED |
| 6 | Durable conversation state | N/A | REQUIRED | REQUIRED |
| 6 | Reply vs new issue detection | N/A | REQUIRED | REQUIRED |
| 6 | Duplicate approval protection | N/A | REQUIRED | REQUIRED |
| 6 | State transition validation | RECOMMENDED | REQUIRED | REQUIRED |
| 6 | Max clarification limit | N/A | REQUIRED | REQUIRED |
| 6 | Closed issue blocks actions | N/A | REQUIRED | REQUIRED |
| 6 | Orphaned state detection | RECOMMENDED | RECOMMENDED | REQUIRED |

**REQUIRED** = FAIL verdict blocks go-live.
**RECOMMENDED** = WARN verdict, does not block go-live but should be fixed.
**N/A** = skip this check entirely, mark as N/A in the report table.

---

## Domain 1 — Action Safety Boundaries

These checks determine whether the agent can be made to act outside its
permitted scope. Any FAIL here = NOT READY, no exceptions.

Read: `references/action-safety.md` for detailed check descriptions.

Key checks to perform:
- Is there a hardcoded allowlist of permitted autonomous actions (not just in a prompt)?
- Is Severity 1 hardcoded to always require human approval in code logic?
- Is there a master kill switch that disables autonomous actions via config?
- Does the agent fall back to escalate (not act) when the LLM API fails?
- Are LLM outputs validated against a schema before any action executes?
- Can the agent be prompted (via message injection) to exceed its action scope?
- Does the agent act before logging, or log before acting? (must be log-first)

---

## Domain 2 — Security + Secrets

These checks protect credentials, prevent injection, and ensure the agent
cannot be weaponised via malicious message content.

Read: `references/security.md` for detailed check descriptions.

Key checks to perform:
- Are all secrets in Azure Key Vault / AWS Secrets Manager / env vars — zero hardcoded?
- Is message content sanitised before being passed to the LLM prompt?
- Is there protection against prompt injection in operator messages?
- Are LLM responses treated as untrusted input before acting on them?
- Is the Teams/Slack bot token scoped to minimum required permissions?
- Is the Jira/ServiceNow API token scoped to the ops project only?
- Are outbound webhook URLs validated before posting replies?

---

## Domain 3 — Audit Trail + Observability

Every autonomous action must be traceable. These checks verify the agent
produces a complete, tamper-resistant audit record.

Key checks to perform:
- Is every autonomous action written to audit log BEFORE execution?
- Does the audit log capture: actor, action, issue_id, from_state, to_state, timestamp, reasoning?
- Is the audit log append-only (no update/delete path in code)?
- Are LLM classification decisions logged (including confidence score)?
- Are human approvals and rejections logged with approver identity?
- Is Application Insights / CloudWatch / logging wired up for exceptions?
- Are failed LLM calls logged with the raw error?

---

## Domain 4 — Reliability + Error Handling

An agent that crashes silently or drops issues is as dangerous as one that
acts incorrectly.

Key checks to perform:
- Is there retry logic on LLM API calls (transient failures)?
- Is there a dead-letter queue for messages that fail processing?
- Does the agent handle empty/null LLM responses without crashing?
- Does the agent handle Jira/ticketing API downtime gracefully?
- Is there a deduplication mechanism to prevent double-processing?
- Are SLA timers durable — do they survive a service restart?
- Is the message queue consumer idempotent (safe to re-process)?

---

## Domain 5 — Escalation Logic Correctness

The escalation chain is the most business-critical logic in the system.
Errors here directly affect whether the right humans are notified.

Key checks to perform:
- Does the escalation path match the agreed hierarchy (Supervisor → Manager → Director → VP)?
- Is there a timeout/SLA timer that auto-escalates if no response is received?
- Does rejection route back to the operator for more information?
- Does approval route to action execution, not re-escalation?
- Is the escalation brief generated fresh at each tier (not a copy of tier 1)?
- Are escalation notifications sent to the correct person at each level?
- Is there protection against infinite escalation loops?

---

## Domain 6 — Conversation + State Management

This domain is specific to agentic systems that maintain multi-turn
conversations with operators and stateful issue lifecycles. Failures here
cause issues to be lost, duplicated, acted on twice, or stuck in limbo.

Read: `references/state-management.md` for detailed check descriptions.

Key checks to perform:
- Is every issue tracked by a unique, persistent ID from ingestion through closure?
- Is conversation thread state stored durably (survives function restarts)?
- Does the agent correctly distinguish a reply-to-open-issue from a new issue?
- Is there protection against acting on the same approval response twice?
- Are state transitions validated — can the agent move to an invalid state?
- Is there a maximum clarification attempt limit before auto-escalating?
- Does closing an issue prevent further autonomous actions on it?
- Is orphaned state cleaned up — issues stuck in intermediate states detected?

---

## Output Format

After completing all six domains, generate **both** a markdown report and a PDF report.

### Step 1 — Write the markdown report

Save to `/mnt/user-data/outputs/code-review-{repo-name}.md` using this structure:

```
# Code Review Report — [Agent Name / Repo]
Reviewed: [date]
Reviewer: Claude (ops-agent-code-review skill)
Files reviewed: [list]

Detected agent level: L1 Assisted / L2 Semi Autonomous / L3 Supervised Autonomous
Evidence: [one sentence citing the specific code signals that determined the level]
Override: [state if user explicitly specified the level instead of auto-detected]

---

## Overall Verdict: READY / NOT READY / CONDITIONALLY READY

[One paragraph summary of the most important findings]

---

## Domain 1 — Action Safety Boundaries
Verdict: PASS / FAIL / WARN

| Check | Verdict | Location | Notes |
|---|---|---|---|
| Hardcoded action allowlist | PASS/FAIL/WARN/NOT FOUND/N/A | file:line | detail |
| Sev 1 hardcoded to human | ... | ... | ... |
| Kill switch in config | ... | ... | ... |
| LLM failure → escalate | ... | ... | ... |
| Schema validation on LLM output | ... | ... | ... |
| Injection resistance | ... | ... | ... |
| Log-before-act | ... | ... | ... |

Critical failures (must fix before go-live):
- [list any FAILs]

---

## Domain 2 — Security + Secrets
Verdict: PASS / FAIL / WARN

| Check | Verdict | Location | Notes |
|---|---|---|---|
[same table structure]

Critical failures:
- [list any FAILs]

---

## Domain 3 — Audit Trail + Observability
Verdict: PASS / FAIL / WARN

[same table structure]

---

## Domain 4 — Reliability + Error Handling
Verdict: PASS / FAIL / WARN

[same table structure]

---

## Domain 5 — Escalation Logic Correctness
Verdict: PASS / FAIL / WARN

[same table structure]

---

## Domain 6 — Conversation + State Management
Verdict: PASS / FAIL / WARN

| Check | Verdict | Location | Notes |
|---|---|---|---|
| Persistent issue ID end-to-end | ... | ... | ... |
| Durable conversation state | ... | ... | ... |
| Reply vs new issue detection | ... | ... | ... |
| Duplicate approval protection | ... | ... | ... |
| State transition validation | ... | ... | ... |
| Max clarification attempt limit | ... | ... | ... |
| Closed issue blocks further actions | ... | ... | ... |
| Orphaned state detection | ... | ... | ... |

Critical failures:
- [list any FAILs]

---

## Prioritised Fix List

### Must fix before go-live (FAIL items)
1. [Specific fix with file + line reference]
2. ...

### Should fix before go-live (WARN items)
1. [Specific fix with file + line reference]
2. ...

### Nice to have (improvements)
1. ...

---

## Go-Live Recommendation

READY: All domains pass. Proceed to Gate 2 (classifier accuracy testing).

NOT READY: [N] critical failures found. Do not proceed to production.
Return to contractor with the Must Fix list above.

CONDITIONALLY READY: No critical failures, but [N] warnings present.
Proceed with caution. Address WARN items within [timeframe].
```

### Step 2 — Generate the PDF report (MANDATORY)

This step is not optional. Run immediately after saving the markdown file.
Do not skip, do not wait to be asked, do not mention it as a future option.

The script does not exist on disk in a new conversation — write it first,
then run it. Use the exact bash block below, replacing REPO with a short
slug (e.g. `ops-agent`, `gfit-agent`).

```bash
pip install reportlab --break-system-packages -q

cat > /tmp/gen_pdf.py << 'PYSCRIPT'
import argparse, re
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

C_PURPLE=colors.HexColor("#534AB7"); C_PURPLE_LIGHT=colors.HexColor("#EEEDFE")
C_TEAL=colors.HexColor("#0F6E56"); C_TEAL_LIGHT=colors.HexColor("#E1F5EE")
C_RED=colors.HexColor("#A32D2D"); C_RED_LIGHT=colors.HexColor("#FCEBEB")
C_AMBER=colors.HexColor("#854F0B"); C_AMBER_LIGHT=colors.HexColor("#FAEEDA")
C_GRAY=colors.HexColor("#5F5E5A"); C_GRAY_LIGHT=colors.HexColor("#F1EFE8")
C_BORDER=colors.HexColor("#D3D1C7"); C_WHITE=colors.white; C_BLACK=colors.HexColor("#2C2C2A")
REPORT_TITLE="GFIT Agent Production Readiness Report"
FOOTER_TEXT="GFIT Agent Production Readiness Report — Confidential"
VERDICT_COLORS={"PASS":(C_TEAL,C_TEAL_LIGHT),"FAIL":(C_RED,C_RED_LIGHT),"WARN":(C_AMBER,C_AMBER_LIGHT),"NOT FOUND":(C_GRAY,C_GRAY_LIGHT),"N/A":(C_GRAY,C_GRAY_LIGHT),"READY":(C_TEAL,C_TEAL_LIGHT),"NOT READY":(C_RED,C_RED_LIGHT),"CONDITIONALLY READY":(C_AMBER,C_AMBER_LIGHT)}

def make_styles():
    return {"title":ParagraphStyle("title",fontSize=22,fontName="Helvetica-Bold",textColor=C_BLACK,spaceAfter=4,leading=28),"h1":ParagraphStyle("h1",fontSize=14,fontName="Helvetica-Bold",textColor=C_BLACK,spaceBefore=18,spaceAfter=6,leading=18),"h2":ParagraphStyle("h2",fontSize=12,fontName="Helvetica-Bold",textColor=C_PURPLE,spaceBefore=14,spaceAfter=4,leading=16),"body":ParagraphStyle("body",fontSize=9,fontName="Helvetica",textColor=C_BLACK,spaceAfter=4,leading=13),"body_small":ParagraphStyle("body_small",fontSize=8,fontName="Helvetica",textColor=C_GRAY,spaceAfter=3,leading=11),"bullet":ParagraphStyle("bullet",fontSize=9,fontName="Helvetica",textColor=C_BLACK,spaceAfter=3,leading=13,leftIndent=12)}

def verdict_banner(verdict,styles):
    fg,bg=VERDICT_COLORS.get(verdict.upper(),(C_GRAY,C_GRAY_LIGHT))
    cell=Paragraph(f"<b>Overall Verdict: {verdict}</b>",ParagraphStyle("vb2",fontSize=13,fontName="Helvetica-Bold",textColor=fg,leading=16))
    t=Table([[cell]],colWidths=[170*mm])
    t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),bg),("TOPPADDING",(0,0),(-1,-1),10),("BOTTOMPADDING",(0,0),(-1,-1),10),("LEFTPADDING",(0,0),(-1,-1),14),("BOX",(0,0),(-1,-1),1,fg)]))
    return t

def domain_table(rows,styles):
    def hcell(t): return Paragraph(f"<b>{t}</b>",ParagraphStyle("th",fontSize=8,fontName="Helvetica-Bold",textColor=C_WHITE,leading=10))
    def bcell(t): return Paragraph(str(t),ParagraphStyle("td",fontSize=8,fontName="Helvetica",textColor=C_BLACK,leading=11))
    def vcell(v):
        fg,bg=VERDICT_COLORS.get(v.upper(),(C_GRAY,C_GRAY_LIGHT))
        return Paragraph(f"<b>{v}</b>",ParagraphStyle("vd",fontSize=8,fontName="Helvetica-Bold",textColor=fg,leading=10))
    data=[[hcell(h) for h in ["Check","Verdict","Location","Notes"]]]
    row_colors=[]
    for i,row in enumerate(rows):
        v=row.get("verdict","").strip()
        _,bg=VERDICT_COLORS.get(v.upper(),(C_WHITE,C_WHITE))
        row_colors.append(("BACKGROUND",(0,i+1),(-1,i+1),bg if v.upper()=="FAIL" else C_WHITE))
        data.append([bcell(row.get("check","")),vcell(v),Paragraph(row.get("location","—"),ParagraphStyle("loc",fontSize=7,fontName="Courier",textColor=C_PURPLE,leading=10)),bcell(row.get("notes",""))])
    t=Table(data,colWidths=[52*mm,22*mm,38*mm,52*mm],repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),C_PURPLE),("GRID",(0,0),(-1,-1),0.4,C_BORDER),("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),("LEFTPADDING",(0,0),(-1,-1),6),("RIGHTPADDING",(0,0),(-1,-1),6),("VALIGN",(0,0),(-1,-1),"TOP"),("ROWBACKGROUNDS",(0,1),(-1,-1),[C_WHITE,C_GRAY_LIGHT])]+row_colors))
    return t

def parse_markdown(md,styles):
    story=[]; lines=md.split("\n"); i=0; table_rows=[]; in_table=False
    def flush(rows):
        parsed=[]
        for row in rows:
            cells=[c.strip() for c in row.strip("|").split("|")]
            if len(cells)>=2 and not all(set(c)<=set("-: ") for c in cells):
                parsed.append({"check":cells[0] if len(cells)>0 else "","verdict":cells[1] if len(cells)>1 else "","location":cells[2] if len(cells)>2 else "","notes":cells[3] if len(cells)>3 else ""})
        return parsed
    while i<len(lines):
        line=lines[i]
        if line.strip().startswith("|") and not in_table: in_table=True; table_rows=[line]; i+=1; continue
        if in_table:
            if line.strip().startswith("|"): table_rows.append(line); i+=1; continue
            else:
                parsed=flush(table_rows[2:])
                if parsed: story.extend([Spacer(1,4),domain_table(parsed,styles),Spacer(1,6)])
                in_table=False; table_rows=[]
        if line.startswith("# ") and not line.startswith("## "): story.append(Paragraph(line[2:].strip(),styles["title"])); i+=1; continue
        if line.startswith("## "):
            text=line[3:].strip()
            if text.startswith("Overall Verdict:"): story.extend([Spacer(1,6),verdict_banner(text.replace("Overall Verdict:","").strip(),styles),Spacer(1,10)]); i+=1; continue
            story.append(Paragraph(text,styles["h1"])); i+=1; continue
        if line.startswith("### "): story.append(Paragraph(line[4:].strip(),styles["h2"])); i+=1; continue
        if line.strip()=="---": story.extend([Spacer(1,4),HRFlowable(width="100%",thickness=0.5,color=C_BORDER,spaceAfter=4)]); i+=1; continue
        if line.startswith("- "): story.append(Paragraph(f"• {line[2:].strip()}",styles["bullet"])); i+=1; continue
        m=re.match(r"^(\d+)\. (.+)",line)
        if m: story.append(Paragraph(f"{m.group(1)}. {m.group(2)}",styles["bullet"])); i+=1; continue
        if re.match(r"^[A-Z][a-zA-Z ]+: .+",line): story.append(Paragraph(line.strip(),styles["body_small"])); i+=1; continue
        if line.strip()=="": story.append(Spacer(1,4)); i+=1; continue
        story.append(Paragraph(line.strip(),styles["body"])); i+=1
    if in_table and table_rows:
        parsed=flush(table_rows[2:])
        if parsed: story.append(domain_table(parsed,styles))
    return story

def make_cover_banner(styles):
    t=Table([[Paragraph(REPORT_TITLE,ParagraphStyle("ct",fontSize=16,fontName="Helvetica-Bold",textColor=C_WHITE,leading=20))],[Paragraph("Code Review &amp; Production Readiness Assessment",ParagraphStyle("cs",fontSize=9,fontName="Helvetica",textColor=colors.HexColor("#CECBF6"),leading=12))]],colWidths=[170*mm])
    t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),C_PURPLE),("TOPPADDING",(0,0),(-1,-1),10),("BOTTOMPADDING",(0,0),(-1,-1),10),("LEFTPADDING",(0,0),(-1,-1),14)]))
    return [t,Spacer(1,14)]

def add_page_decorations(canvas,doc):
    w,h=A4; canvas.saveState()
    band_h=14*mm; canvas.setFillColor(C_PURPLE); canvas.rect(0,h-band_h,w,band_h,fill=1,stroke=0)
    canvas.setFont("Helvetica-Bold",10); canvas.setFillColor(C_WHITE); canvas.drawString(20*mm,h-band_h+4*mm,REPORT_TITLE)
    canvas.setFont("Helvetica",8); canvas.setFillColor(colors.HexColor("#CECBF6")); canvas.drawRightString(w-20*mm,h-band_h+4*mm,f"Page {doc.page}")
    canvas.setStrokeColor(C_BORDER); canvas.setLineWidth(0.4); canvas.line(20*mm,18*mm,w-20*mm,18*mm)
    canvas.setFont("Helvetica",7); canvas.setFillColor(C_GRAY); canvas.drawString(20*mm,12*mm,FOOTER_TEXT); canvas.drawRightString(w-20*mm,12*mm,f"Generated {datetime.now().strftime('%Y-%m-%d')}")
    canvas.restoreState()

parser=argparse.ArgumentParser(); parser.add_argument("--input",required=True); parser.add_argument("--output",required=True); args=parser.parse_args()
with open(args.input,"r",encoding="utf-8") as f: md=f.read()
styles=make_styles(); story=make_cover_banner(styles)+parse_markdown(md,styles)
doc=SimpleDocTemplate(args.output,pagesize=A4,leftMargin=20*mm,rightMargin=20*mm,topMargin=30*mm,bottomMargin=22*mm,title=REPORT_TITLE,author="Claude — ops-agent-code-review skill")
doc.build(story,onFirstPage=add_page_decorations,onLaterPages=add_page_decorations)
print(f"PDF written to: {args.output}")
PYSCRIPT

python /tmp/gen_pdf.py \
  --input /mnt/user-data/outputs/code-review-REPO.md \
  --output /mnt/user-data/outputs/code-review-REPO.pdf
```

Replace REPO in both `--input` and `--output` with the actual repo slug before running.

If the script fails:
1. Print the full error message.
2. Check the markdown file exists: `ls -la /mnt/user-data/outputs/`
3. Retry once. If it still fails, tell the user and deliver the markdown alone.
Never silently skip the PDF without telling the user why.

### Step 3 — Present both files (MANDATORY)

Call present_files immediately after the PDF is generated.
Both files must be presented — markdown first, then PDF.

```python
present_files([
  "/mnt/user-data/outputs/code-review-REPO.md",
  "/mnt/user-data/outputs/code-review-REPO.pdf"
])
```

Then post a 3–5 sentence summary in chat covering:
- Overall verdict
- Number of critical failures
- The single most important fix
Do NOT repeat the full report inline — the files contain the full detail.

---

## Verdict definitions

**PASS** — check is fully satisfied with evidence in code.
**FAIL** — check is not satisfied. Blocks production go-live.
**WARN** — partially satisfied or best-practice gap. Does not block but should be fixed.
**NOT FOUND** — could not locate relevant code. Treat as FAIL unless contractor can point to it.

---

## Special cases

**If only partial code is shared:** Note which files are missing. Mark all
checks that depend on missing files as NOT FOUND. Do not assume absent code
is correct. Treat NOT FOUND as FAIL for REQUIRED checks.

**If the code is in a language other than Python:** Apply the same checks —
the patterns are language-agnostic. Adjust file/function references accordingly.

**If level is ambiguous:** Apply the higher level's requirements. State the
ambiguity in the report. It is always safer to over-check than under-check.

**If the user says "just check if it works" without specifying a level:**
Auto-detect, state the detected level clearly, and apply that level's table.
Do not silently apply L2 strictness to an L1 agent — it will generate
misleading FAILs on checks that are genuinely not applicable.
