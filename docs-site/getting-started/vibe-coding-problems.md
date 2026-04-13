# Problems Every Vibe-Coder Recognizes

You know that feeling? You've been shipping with Copilot and Cursor for three weeks, everything works, CI is green. Then a teammate opens a PR and asks: *"Why do we have three config loaders?"*

You don't remember writing three. But you did — once per chat session, because the AI didn't see the other files.

This page shows exactly what that looks like. If you've vibed for more than a week, you'll recognize every single one.

---

## You tab-complete `get_current_user()` — and it already exists somewhere else

Monday. You're in `routes/orders.py`. You need the logged-in user. Copilot suggests a complete function. You tab, it works, you move on.

Thursday. You're in `routes/billing.py`. Same situation. Copilot generates it again — slightly different name, slightly different logic. You don't notice because you never opened `routes/orders.py` this week.

A month later:

```python
# routes/orders.py  —  written Monday with Copilot
def get_current_user(request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    return db.query(User).filter(User.id == payload["sub"]).first()


# routes/billing.py  —  written Thursday with Copilot
def get_authenticated_user(req):
    auth = req.headers["Authorization"]
    token = auth.split(" ")[1]
    data = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    user = db.query(User).get(data["user_id"])
    if not user:
        raise HTTPException(status_code=401)
    return user


# routes/admin.py  —  written the following week with Cursor
def current_user_from_request(request):
    try:
        token = request.headers["Authorization"].removeprefix("Bearer ")
        return jwt.decode(token, os.environ["SECRET_KEY"], algorithms=["HS256"])
    except Exception:
        return None  # returns the raw dict, not a User object
```

Three copies. Three names. One checks for missing users, one returns `None` on failure, one returns the raw JWT payload instead of a `User` object. They'll all pass tests because nobody tests them against each other.

The worst part? You'll find the bug in production when `current_user_from_request` returns a dict and some downstream code calls `.email` on it.

**What drift finds:** `MDS` — three functions with 85%+ AST similarity across three files.

---

## You prompt "add error handling" four separate times

It starts innocently. You're building an API and each endpoint talks to an external service. Each endpoint was written in a separate chat session. The AI starts each session fresh — it doesn't remember what it did yesterday.

```python
# routes/users.py  —  Session on Tuesday
@app.post("/users")
def create_user(data: UserCreate):
    try:
        user = user_service.create(data)
        return {"id": user.id}
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Email already exists")


# routes/orders.py  —  Session on Wednesday
@app.post("/orders")
def create_order(data: OrderCreate):
    try:
        order = order_service.create(data)
        return {"id": order.id}
    except Exception as e:
        logger.error(f"Order creation failed: {e}")
        return {"error": str(e)}  # returns 200 with error in body


# routes/payments.py  —  Session on Thursday
@app.post("/payments")
def create_payment(data: PaymentCreate):
    result = payment_service.charge(data)
    # no error handling at all — "I'll add it later"
    return {"status": result.status}


# routes/notifications.py  —  Session on Friday
@app.post("/notifications")
def send_notification(data: NotificationCreate):
    try:
        notification_service.send(data)
    except Exception:
        pass  # silently swallows everything
    return {"ok": True}  # always returns success
```

Every endpoint looks fine in isolation. But your API now has four completely different error contracts: one raises HTTP exceptions, one returns 200 with an error body, one lets exceptions bubble up raw, and one eats every error silently and says "ok".

The frontend developer writing the client? Good luck figuring out what to catch.

**What drift finds:** `PFS` — four endpoints in the same module, same concern (error handling), four incompatible patterns.

---

## You prompt "just make it work" and the AI takes a shortcut

You're in the API layer. You need the user's subscription status. The proper way is through the service layer. But you prompt "get me the user's subscription from the database" and the AI writes the fastest path:

```python
# api/endpoints/dashboard.py
from app.db.models import User, Subscription  # straight into the DB layer
from app.db.session import get_db


@router.get("/dashboard")
def get_dashboard(user_id: int, db=Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    sub = db.query(Subscription).filter(Subscription.user_id == user_id).first()
    return {
        "name": user.name,
        "plan": sub.plan_name if sub else "free",
        "expires": sub.expires_at if sub else None,
    }
```

Tests pass. The feature works. You ship it.

But now your API layer knows about SQLAlchemy models, database sessions, and query syntax. Every AI-prompted feature adds another `from app.db.models import ...` to the API layer. After 30 features, the "layer boundary" is a myth — the API **is** the database layer.

Later, when someone tries to swap SQLAlchemy for async SQLAlchemy or split the database module, they find 47 files with direct model imports. The migration that should've taken a day takes two weeks.

**What drift finds:** `AVS` — the `api/` layer importing directly from `db/`, bypassing the `services/` boundary.

---

## You prompt "write tests" and the AI gives you a green checkmark that means nothing

You just finished a `signup()` function. It validates emails, checks for duplicates, hashes passwords, sends a welcome email. Six `if` branches, three possible exceptions.

You prompt: *"Write tests for the signup function."*

The AI generates:

```python
def test_signup_creates_user():
    result = signup("alice@example.com", "SecurePass123!")
    assert result.id is not None
    assert result.email == "alice@example.com"

def test_signup_returns_user_object():
    user = signup("bob@test.com", "MyPassword1!")
    assert isinstance(user, User)
    assert user.is_active is True

def test_signup_hashes_password():
    user = signup("carol@test.com", "RawPassword1!")
    assert user.password_hash != "RawPassword1!"
    assert user.password_hash.startswith("$2b$")

def test_signup_with_name():
    user = signup("dave@test.com", "Pass1234!", name="Dave")
    assert user.name == "Dave"
```

Four tests. All green. You feel productive.

But: what happens when someone signs up with an email that already exists? With an empty password? With `password = "1"`? When the email service is down? When the database is unreachable? None of those paths are tested. The function has six error branches and zero of them have coverage.

The day it breaks in production will be the first time that code path runs at all.

**What drift finds:** `TPD` — a test file with 100% positive assertions and zero negative test cases for a function with multiple error branches.

---

## Mypy complains, you prompt "fix this", the AI adds `# type: ignore`

You're deep in a feature. Mypy underlines something in red. You could fix the type — but you're in flow, that's not what you're working on right now. You prompt "fix this type error" and the AI adds:

```python
user = get_cached_user(user_id)  # type: ignore[assignment]
```

Fine. Once. But this happens three times a day across the team. After a month:

```python
response = client.post(url, json=data)  # type: ignore[arg-type]
config = load_config()  # type: ignore[return-value]
items = db.execute(query).all()  # type: ignore[call-overload]
session["user"] = user_data  # type: ignore[assignment]
result = cache.get(key) or default  # type: ignore[union-attr]
handler = REGISTRY[event_type]  # type: ignore[index]
cleaned = sanitize(raw_input)  # type: ignore[misc]
```

You still have type annotations everywhere. Mypy is still in CI. But it's checking nothing — because every line it would flag is silenced. You have a type system that costs maintenance effort but provides zero safety.

The `# type: ignore[assignment]` on `get_cached_user`? That was hiding a real bug: the cache returns `Optional[User]` but the code treated it as `User`. It crashed in production three weeks later.

**What drift finds:** `BAT` — 47 `type: ignore` markers, 12 bare `except Exception`, and 8 `Any` annotations in a codebase that claims to be fully typed.

---

## You prompt "ensure the connection is ready" and the function doesn't ensure anything

You ask the AI to add a connection check before your database operations. It generates:

```python
def ensure_db_connection(conn) -> bool:
    """Ensure the database connection is ready."""
    try:
        conn.execute("SELECT 1")
        return True
    except Exception:
        return False
```

The function is called `ensure_db_connection`. "Ensure" means "guarantee this postcondition or fail loudly." But the function doesn't ensure anything — it's a health check that returns `True`/`False`. And the caller?

```python
def get_users(conn):
    ensure_db_connection(conn)  # return value ignored
    return conn.execute("SELECT * FROM users").fetchall()
```

Someone saw the name `ensure_*`, assumed it raises on failure (because that's what "ensure" means everywhere), and didn't check the return value. The dead connection goes through, and the `SELECT` blows up with a cryptic socket error instead of a clean "database unreachable" message.

This is how it happens: the AI picks a name that sounds right, implements a body that does something slightly different, and nobody notices because the name feels trustworthy.

**What drift finds:** `NBV` — function name prefix `ensure_` implies guarantee-or-raise semantics but the implementation returns a boolean.

---

## Sound familiar?

If you recognized even one of these, drift will find more in your codebase. These aren't theoretical — they're what actually accumulates when AI generates code file-by-file without seeing the big picture.

```bash
pip install drift-analyzer
drift analyze --repo .
```

Or copy a [prompt into your AI assistant](prompts.md) and let it run drift for you.

!!! tip "Vibe-coding config"
    If your team uses AI assistants heavily, copy the [vibe-coding optimized config](https://github.com/mick-gsk/drift/tree/main/examples/vibe-coding) for signal weights tuned to these exact patterns.

## What drift catches that other tools miss

| Problem | Ruff/pylint | mypy | Semgrep | **drift** |
|---|:---:|:---:|:---:|:---:|
| Same function generated in 3 files | — | — | — | **MDS** |
| 4 endpoints, 4 error contracts | — | — | — | **PFS** |
| AI imports across layer boundaries | — | — | partial | **AVS** |
| Tests that only test the happy path | — | — | — | **TPD** |
| `type: ignore` accumulation | — | — | — | **BAT** |
| `ensure_*` that doesn't ensure | — | — | — | **NBV** |

Ruff checks style. Mypy checks types. Semgrep checks patterns. **None of them check whether your codebase still makes structural sense across files.** That's what drift does.

## Related pages

- [Quick Start](quickstart.md) — install and run in 2 minutes
- [Prompts to Try](prompts.md) — copy-paste prompts for your AI assistant
- [Example Findings](../product/example-findings.md) — signal-level output examples
- [Signal Reference](../algorithms/signals.md) — all 24 signals explained
