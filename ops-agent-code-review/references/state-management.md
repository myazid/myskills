# State Management Reference

Detailed descriptions for each Domain 6 check.

## 1. Persistent issue ID end-to-end

Every message that enters the system should produce exactly one issue record
with a UUID that follows it through every function call, queue hop, state
transition, and notification — all the way to closure.

Look for: the issue UUID being passed explicitly through all downstream
function calls, queue messages, and audit log entries. It must never be
regenerated mid-lifecycle.

```python
# GOOD — UUID created once at ingestion, threaded everywhere
issue_id = write_issue(event, extracted)          # UUID created here
push_to_classify(issue_id, event, extracted)      # passed explicitly
# classify function receives issue_id, never re-creates it
```

```python
# BAD — ID recreated at classify step
def classify(msg):
    issue_id = str(uuid.uuid4())  # new UUID — disconnects from ingestion record
    update_issue(issue_id, result)
```

Red flags:
- `uuid.uuid4()` called more than once per issue lifecycle
- Queue messages contain raw_text but no issue_id
- Audit log entries without an issue_id foreign key

---

## 2. Durable conversation state

When an operator replies to an agent question, the agent must reconnect
that reply to the original issue. This requires storing thread context
in a durable store (Redis, PostgreSQL, Azure Table Storage) — not in
function memory, which is ephemeral.

Look for: a store keyed on `source_thread_id` or `source_message_id`
that persists context between function invocations.

```python
# GOOD — Redis used for thread → issue_id mapping
import redis
r = redis.from_url(os.environ["REDIS_URL"])

def store_thread_context(thread_id: str, issue_id: str, state: dict):
    r.setex(
        f"thread:{thread_id}",
        86400,  # 24h TTL
        json.dumps({"issue_id": issue_id, "state": state})
    )

def get_thread_context(thread_id: str) -> dict | None:
    val = r.get(f"thread:{thread_id}")
    return json.loads(val) if val else None
```

```python
# BAD — context only in function memory
thread_contexts = {}  # lost on every cold start

def handle_reply(thread_id):
    ctx = thread_contexts.get(thread_id)  # always None after restart
```

Red flags:
- Context stored in module-level dicts or class attributes
- No TTL on stored context (memory leak)
- Azure Function with no external state store

---

## 3. Reply vs new issue detection

Every incoming Teams message could be either a new issue or a reply to an
existing open issue. Misclassifying a reply as a new issue creates a phantom
duplicate. Misclassifying a new issue as a reply silently drops it.

Look for: explicit thread ID lookup before creating a new issue record.

```python
# GOOD — check thread context before creating new issue
def handle_message(event: dict):
    thread_id = event["source_thread_id"]
    reply_to_id = event.get("reply_to_id")

    # If this is a reply in an existing thread, route to reply handler
    if reply_to_id:
        ctx = get_thread_context(thread_id)
        if ctx and ctx.get("issue_id"):
            handle_reply_to_issue(ctx["issue_id"], event)
            return

    # Otherwise treat as new issue
    issue_id = write_issue(event, extracted)
```

```python
# BAD — every message creates a new issue record
def handle_message(event):
    issue_id = write_issue(event, extracted)  # reply creates duplicate issue
```

Red flags:
- `reply_to_id` field from Teams activity ignored
- No thread context lookup before `write_issue()`
- Dedup only by text fingerprint (misses reply/new distinction)

---

## 4. Duplicate approval protection

When a supervisor clicks "Approve" on an Adaptive Card, Teams may deliver
the action payload more than once (network retry). The agent must be
idempotent — executing the approval action twice must produce the same
result as executing it once.

Look for: a check that the issue is still in the expected state before
executing the approved action. Also look for idempotency keys on
approval handlers.

```python
# GOOD — state check before acting on approval
def handle_approval(issue_id: str, approver_id: str, action: str):
    conn = get_db()
    cur = conn.cursor()

    # Atomic check-and-update — only proceeds if still in 'pending' state
    cur.execute("""
        UPDATE issues
        SET state = 'approved', updated_at = now()
        WHERE id = %s AND state = 'pending'
        RETURNING id
    """, (issue_id,))

    if not cur.fetchone():
        # Already processed — idempotent no-op
        return
    conn.commit()
    execute_approved_action(issue_id, action)
```

```python
# BAD — no state check, re-executes on duplicate delivery
def handle_approval(issue_id, action):
    execute_approved_action(issue_id, action)  # runs twice on duplicate
    update_state(issue_id, "approved")
```

---

## 5. State transition validation

The issue state machine should only allow valid transitions. Invalid
transitions (e.g., jumping from `received` directly to `closed` without
going through `triaged`) indicate a logic bug and can mask audit gaps.

Look for: a transition map that is checked before every state update.

```python
# GOOD — explicit transition map enforced
VALID_TRANSITIONS = {
    "received":   {"clarifying", "triaged"},
    "clarifying": {"received", "triaged"},
    "triaged":    {"pending", "closed"},
    "pending":    {"approved", "escalated", "triaged"},
    "approved":   {"closed"},
    "escalated":  {"pending", "closed"},
    "closed":     set(),  # terminal — no transitions out
}

def transition_state(issue_id: str, from_state: str, to_state: str):
    if to_state not in VALID_TRANSITIONS.get(from_state, set()):
        raise ValueError(f"Invalid transition: {from_state} → {to_state}")
    # proceed with update
```

```python
# BAD — any state value accepted
def update_state(issue_id, new_state):
    cur.execute("UPDATE issues SET state = %s WHERE id = %s",
                (new_state, issue_id))  # no validation
```

---

## 6. Maximum clarification attempt limit

If the agent asks a clarifying question and the operator never replies,
the issue should not remain in `clarifying` state indefinitely. There
must be a maximum number of attempts before the agent escalates to a
human rather than waiting forever.

Look for: a counter on clarification attempts and a fallback escalation.

```python
# GOOD — max attempts enforced
MAX_CLARIFICATION_ATTEMPTS = 3

def handle_info_gap(issue_id: str, question: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT clarification_attempts FROM issues WHERE id = %s",
        (issue_id,)
    )
    attempts = cur.fetchone()[0] or 0

    if attempts >= MAX_CLARIFICATION_ATTEMPTS:
        # Give up asking, escalate with available info
        escalate_to_supervisor(issue_id, reason="max_clarification_attempts")
        return

    cur.execute(
        "UPDATE issues SET clarification_attempts = %s WHERE id = %s",
        (attempts + 1, issue_id)
    )
    post_clarification_question(issue_id, question)
```

```python
# BAD — no limit, issue stuck forever if operator ignores
def handle_info_gap(issue_id, question):
    post_clarification_question(issue_id, question)
    # If operator never replies, issue stays in 'clarifying' indefinitely
```

---

## 7. Closed issue blocks further actions

Once an issue reaches `closed` state, the agent must not execute further
autonomous actions on it — even if a late-arriving queue message or
duplicate payload triggers re-processing.

Look for: a check on issue state at the beginning of every action function.

```python
# GOOD — guard clause on closed state
def execute_action(issue_id: str, action: str):
    cur.execute("SELECT state FROM issues WHERE id = %s", (issue_id,))
    state = cur.fetchone()[0]

    if state == "closed":
        log_audit(issue_id, "agent", "action_skipped_already_closed",
                  detail={"attempted_action": action})
        return  # do nothing

    # proceed
```

```python
# BAD — acts regardless of current state
def execute_action(issue_id, action):
    perform_action(action)  # could re-execute on a closed issue
```

---

## 8. Orphaned state detection

Issues can get stuck in intermediate states if a function crashes mid-execution
or a queue message is dropped. A monitoring job should detect these and alert.

Look for: a scheduled function or cron job that queries for issues that have
been in non-terminal states for longer than expected.

```python
# GOOD — watchdog detects orphaned issues
@app.schedule(schedule="0 */15 * * * *")  # every 15 minutes
def orphan_watchdog(timer: func.TimerRequest):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, state, updated_at
        FROM issues
        WHERE state NOT IN ('closed')
        AND updated_at < now() - INTERVAL '2 hours'
    """)
    orphans = cur.fetchall()
    for issue_id, state, updated_at in orphans:
        alert_ops_team(issue_id, f"Issue stuck in '{state}' since {updated_at}")
```

If no watchdog exists: mark as WARN. If issues have been observed stuck
in staging during testing: mark as FAIL.
