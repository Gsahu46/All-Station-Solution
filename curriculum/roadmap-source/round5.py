"""Round 5 (industry gap research, 2026-10-11): merge 13, replace 1, add 13, update the rest. Total stays 200.
Applied to the ordered station list by build_roadmap.py before numbering. Prerequisites are titles here."""

# Removed station -> (station it merges into, concepts the target gains)
MERGES = {
    "Income tax calculator: old vs new regime": ("GST on invoices", ["slab lookup with TreeMap.floorEntry"]),
    "Recurring bill reminders": ("Webinar scheduling across time zones", ["month ends and leap years with TemporalAdjusters"]),
    "Transactional emails from templates": ("Welcome emails with Spring application events", ["HTML email templates with escaping and UTF-8"]),
    "Serving product images through a CDN": ("Large video uploads to S3", ["delivery through a CDN with versioned URLs"]),
    "Resumable statement downloads": ("Large video uploads to S3", ["resumable downloads with HTTP Range (206)"]),
    "Testing asynchronous code reliably": ("Invoice PDFs without blocking", ["testing async code with Awaitility, never sleep"]),
    "Exchange rates with an in-memory cache": ("Product pages with Redis cache-aside", ["two-level cache: Caffeine in front of Redis"]),
    "Streaming stock prices with WebFlux": ("API gateway and service discovery", ["reactive basics in Spring Cloud Gateway (WebFlux)"]),
    "Respecting a courier partner's rate limit": ("Retrying the SMS provider safely", ["respecting a partner's rate limit (429, Retry-After)"]),
    "Event-sourced insurance claims": ("A double-entry wallet ledger", ["event sourcing compared with an append-only ledger"]),
    "Monitoring with CloudWatch": ("Health, metrics and alerts for payments", []),
    "Testing AWS code with LocalStack": ("Order processing with Amazon SQS", ["testing with LocalStack (free account token required since March 2026)"]),
    "Sharding chat messages": ("Partitioning a huge tracking-events table", ["when partitioning is not enough: shard keys and sharding"]),
}

RENAMES = {
    "Semantic search with pgvector": "Help-centre answers with RAG",
    "Health, metrics and alerts for payments": "Health, metrics and SLOs for payments",
    "Large video uploads to S3": "Large media uploads and CDN delivery",
    "Two-factor login with TOTP": "Passkey sign-in with WebAuthn",
}

# Field overrides after renaming (title -> fields). "concepts+" appends, "concepts" replaces.
UPDATES = {
    "Help-centre answers with RAG": {
        "scenario": "Help-centre search misses 'cannot log in' when the article says 'sign-in problems', and the chatbot invents answers with no source.",
        "endpoints": ["POST /articles", "POST /answers"],
        "concepts": ["embeddings and pgvector", "retrieval-augmented generation with citations", "hybrid keyword + vector search", "an evaluation set to measure answer quality"]},
    "Passkey sign-in with WebAuthn": {
        "industry": "Fintech", "company": "Tijori",
        "scenario": "Phished passwords and SIM-swapped SMS codes drained 14 accounts; customers want to sign in with a fingerprint or face.",
        "endpoints": ["POST /webauthn/registration/options", "POST /webauthn/registration", "POST /webauthn/authentication", "POST /2fa/totp (fallback)"],
        "concepts": ["passkeys and WebAuthn (FIDO2)", "challenge, origin and relying-party checks", "TOTP as a fallback second factor", "Spring Security 7 multi-factor authentication"]},
    "Health, metrics and SLOs for payments": {
        "concepts": ["Actuator liveness vs readiness", "Micrometer counters, timers and gauges", "SLOs and error budgets", "multi-window burn-rate alerts", "export to Prometheus or CloudWatch"]},
    "Large media uploads and CDN delivery": {
        "scenario": "Creators upload 4 GB videos through the API servers, which run out of memory, and product images served by the API eat half the bandwidth on sale days."},
    "Support ticket summaries with an LLM API": {"concepts+": ["OWASP Top 10 for LLM apps: prompt injection, sensitive data, unbounded consumption"]},
    "Order API v2 without breaking old apps": {
        "concepts": ["Spring Framework 7 API versioning (path, header, media type)", "breaking vs compatible changes", "Deprecation and Sunset headers (RFC 9745)", "dated versions like Stripe's", "tolerant reader"]},
    "Retrying the SMS provider safely": {"concepts+": ["Spring Framework 7 @Retryable and @ConcurrencyLimit"]},
    "Circuit breaker for a payment partner": {"concepts+": ["Resilience4j next to Spring's built-in retries"]},
    "Public holidays from a partner API": {"concepts+": ["HTTP service clients (@HttpExchange)"]},
    "Pincode serviceability from another service": {"concepts+": ["HTTP service client groups"]},
    "Accepting a partner's snake_case JSON": {"concepts+": ["Jackson 3: tools.jackson, JsonMapper, ISO dates by default"]},
    "Masking card and Aadhaar numbers in responses": {"concepts+": ["Jackson 3 serializers"]},
    "Upgrading to a new Spring Boot major version": {
        "scenario": "The tracking service is still on Spring Boot 3.5, whose free support ends in June 2026, and the upgrade keeps getting postponed.",
        "concepts": ["Spring Boot 3.5 to 4.0 and Java 21 to 25", "reading release notes and migration guides", "Jackson 3, modular starters and removed APIs", "upgrading step by step with tests"]},
    "Flight fare aggregator": {"concepts+": ["no pinning on synchronized since JDK 24 (JEP 491)", "scoped values (final in JDK 25)"]},
    "Tracing a checkout across services": {"concepts+": ["Spring Boot 4 OpenTelemetry starter"]},
    "Publishing order events": {"concepts+": ["Kafka 4 without ZooKeeper (KRaft)"]},
    "Trip events in order": {"concepts+": ["the new consumer rebalance protocol (KIP-848)"]},
    "Task queue with RabbitMQ": {"concepts+": ["RabbitMQ vs Kafka share groups (queues)"]},
    "Product pages with Redis cache-aside": {"concepts+": ["Redis or Valkey: licences and managed options"]},
    "Orchestrated trip booking": {
        "concepts": ["durable workflow engine (Temporal, from Uber's Cadence)", "persisted workflow state", "idempotent activities and retries", "compensation order"]},
    "Splitting hotel booking from inventory": {"concepts+": ["modular monolith first (Spring Modulith)"]},
    "Tenant isolation in a CRM": {"concepts+": ["tenancy models: shared tables, schema or database per tenant"]},
    "GraphQL for the streaming home screen": {"concepts+": ["GraphQL federation (Netflix DGS)"]},
    "Feature flags and gradual rollout": {"endpoints": ["GET /me/flags", "PUT /flags/{key}"], "concepts+": ["the OpenFeature API"]},
    "Troubleshooting a ticketing incident": {"concepts+": ["blameless postmortem"]},
    "Account deletion and data export": {"concepts+": ["DPDP Rules 2025: consent notices, erasure within 90 days"]},
    "Thumbnails with AWS Lambda": {"concepts+": ["start-up: SnapStart vs GraalVM native image vs JDK 25 AOT cache"]},
    "Idempotent UPI-style payments": {"concepts+": ["amounts as integer paise in the API"]},
    "Fare estimates per vehicle type": {"endpoints": ["GET /fare-estimates?pickup&drop"], "concepts+": ["the server computes distance; never trust price inputs"]},
    "Per-city delivery settings": {"concepts+": ["server-computed distance, not the client's"]},
    "Invoice PDFs without blocking": {"concepts+": ["one operation resource for long-running work (Google AIP-151)"]},
    "Bulk shipment creation": {"concepts+": ["standard batch results (Google AIP-231 to 235)"]},
    "Recovering from an accidental DELETE": {"endpoints": ["GET /admin/restore-verifications/{id}"]},
    "Bank statement pages": {"concepts+": ["why live data needs cursors (see the keyset station)"]},
}

# (after_title, level, title, industry, company, scenario, endpoints, concepts, infra, prereq_titles)
NEW5 = [
 ("Support ticket summaries with an LLM API", "0-2", "Expose an API to AI agents with MCP", "SaaS", "Taskloom",
  "Customers want their AI assistants to create and find tasks; today agents scrape the web UI and break on every release.",
  ["MCP tools: create_task, search_tasks (Streamable HTTP)", "GET /tasks"],
  ["Model Context Protocol servers with Spring AI", "tool names, descriptions and JSON schemas", "authenticating and rate-limiting agent callers", "read-only vs write tools"],
  "none", ["Support ticket summaries with an LLM API", "Partner API keys and quotas"]),
 ("Customers see only their own accounts", "0-2", "Document sharing with relationship-based permissions", "SaaS", "Taskloom",
  "Sharing is checked with ad-hoc SQL in 30 places; a user removed from a team still opened its documents for a week.",
  ["POST /docs/{id}/shares", "GET /docs/{id}", "GET /me/shared-with-me"],
  ["relationship-based access control (Zanzibar-style)", "tuples: user, relation, object", "inherited access through folders and teams", "OpenFGA or SpiceDB vs your own tables"],
  "postgres", ["Customers see only their own accounts", "Category tree and breadcrumbs"]),
 ("One API for many payment providers", "0-2", "Saving cards with network tokens", "Payments", "Paysetu",
  "A breach exposed card numbers a merchant had kept for one-click checkout; RBI rules forbid storing them at all.",
  ["POST /customers/{id}/saved-cards", "GET /customers/{id}/saved-cards", "POST /payments (with a token)"],
  ["RBI card-on-file tokenisation", "network tokens vs card numbers", "token lifecycle: create, use, expire, delete", "keeping card data out of your systems"],
  "postgres", ["One API for many payment providers", "Masking card and Aadhaar numbers in responses"]),
 ("Subscription plan changes", "0-2", "Subscriptions with UPI AutoPay mandates", "Streaming", "Streamo",
  "Monthly renewals fail silently because customers revoked mandates in their UPI app, and some debits went out without the 24-hour notice.",
  ["POST /subscriptions/{id}/mandates", "POST /mandates/{id}/debits", "POST /webhooks/mandates"],
  ["mandate states: created, active, paused, revoked", "24-hour pre-debit notification", "per-debit limits and re-authentication", "retries without double debits"],
  "postgres", ["Subscription plan changes", "Idempotent UPI-style payments"]),
 ("Calling a legacy SOAP service", "0-2", "Enterprise integration with Apache Camel", "Insurance", "Bimaly",
  "Partner banks drop policy files on SFTP at 2 am, a queue carries claims, and 4,000 lines of custom glue code connect them.",
  ["route: SFTP file → validate → queue", "GET /integration/runs/{id}"],
  ["Apache Camel routes and components", "file and SFTP polling", "error handlers and dead-letter channels", "idempotent consumers for files"],
  "rabbitmq", ["Calling a legacy SOAP service", "Task queue with RabbitMQ"]),
 ("Reviewing a pull request", "0-2", "Tests that catch weak tests", "SaaS", "Taskloom",
  "Coverage is 85%, yet a pricing bug shipped: the tests ran the code but asserted nothing useful.",
  ["POST /invoices/preview"],
  ["mutation testing with PIT", "property-based tests (jqwik)", "architecture rules with ArchUnit", "what coverage does not tell you"],
  "none", ["Return and refund eligibility", "Reviewing a pull request"]),
 ("Account opening with an outbox", "2-3", "Change data capture with Debezium", "E-commerce", "Kartwala",
  "Search and the warehouse are synced by nightly copies, so prices in search can be a day old.",
  ["Debezium connector: products table → product-changes topic", "consumer: search indexer"],
  ["change data capture from the database log", "Debezium outbox event router", "initial snapshots and schema changes", "duplicates and ordering by key"],
  "kafka+postgres", ["Account opening with an outbox"]),
 ("Help-centre answers with RAG", "2-3", "A tool-calling agent with guardrails", "SaaS", "Taskloom",
  "An AI support agent allowed to issue refunds gave away ₹2 lakh to messages that said 'ignore previous instructions'.",
  ["POST /agent/conversations/{id}/messages", "POST /agent/actions/{id}/approve"],
  ["tool calling with Spring AI", "least-privilege tools and excessive agency", "human approval for write actions", "auditing every tool call"],
  "postgres", ["Help-centre answers with RAG", "Expose an API to AI agents with MCP"]),
 ("A tool-calling agent with guardrails", "2-3", "An AI gateway for many models", "SaaS", "Taskloom",
  "Five teams call three LLM providers with separate keys; one runaway job spent a month's budget over a weekend.",
  ["POST /v1/chat/completions (gateway)", "GET /usage?team"],
  ["routing between hosted and self-hosted models", "token budgets and rate limits per team", "response caching and fallbacks", "logging without leaking prompts"],
  "redis", ["A tool-calling agent with guardrails", "Login attempt limits across servers"]),
 ("Home screen that survives a slow dependency", "2-3", "Cell-based architecture for a SaaS", "SaaS", "Taskloom",
  "One customer's bulk import overloaded the shared database and took every customer down for an hour.",
  ["cell router: /api/** → cell by tenant", "POST /admin/tenants/{id}/move"],
  ["cells and a thin cell router", "shuffle sharding", "limiting the blast radius", "moving tenants between cells"],
  "multi-service+postgres", ["Home screen that survives a slow dependency", "Tenant isolation in a CRM"]),
 ("Replacing a legacy endpoint with a strangler fig", "2-3", "COBOL-to-Java with characterisation tests", "Insurance", "Bimaly",
  "A 30-year-old COBOL interest calculation must move to Java; nobody knows all its rules, and a one-paisa difference is a regulatory issue.",
  ["POST /interest/calculate (new Java)", "comparison job: old vs new outputs"],
  ["characterisation (golden master) tests", "extracting business rules from legacy code", "AI-assisted translation with human review", "running old and new side by side"],
  "postgres", ["Replacing a legacy endpoint with a strangler fig", "Tests that catch weak tests"]),
 ("Payment reconciliation with bank files", "2-3", "ISO 20022 payment messages", "Banking", "Tijori",
  "Partner banks now send ISO 20022 XML instead of SWIFT MT text; free-text addresses fail sanctions screening and reconciliation.",
  ["POST /payments/iso20022/pacs008", "GET /payments/{id}/status (pacs.002)"],
  ["pacs and camt message families", "parsing and validating XML against schemas", "structured addresses", "mapping messages to ledger entries"],
  "postgres", ["Payment reconciliation with bank files", "Accepting a partner's snake_case JSON"]),
 ("ISO 20022 payment messages", "2-3", "Loan checks with Account Aggregator consent", "Fintech", "Tijori",
  "A lending app asks for bank-statement PDFs and passwords; many are forged and approval takes three days.",
  ["POST /consents", "POST /webhooks/consent-status", "GET /loan-applications/{id}/cash-flow"],
  ["consent artefacts: purpose, data range, expiry", "encrypted data from financial information providers", "using data only as consented, then deleting it", "handling revoked consent"],
  "postgres", ["Account deletion and data export", "Encrypting Aadhaar and PAN at rest"]),
]


def apply(order):
    """order: list of dicts with level, title, industry, company, scenario, endpoints, concepts, infra, pre (titles)."""
    by_title = {r["title"]: r for r in order}
    for gone, (target, extra) in MERGES.items():
        assert gone in by_title and target in by_title, (gone, target)
        by_title[target]["concepts"] = by_title[target]["concepts"] + [c for c in extra if c not in by_title[target]["concepts"]]
    order[:] = [r for r in order if r["title"] not in MERGES]
    # Prerequisites that pointed at a merged station now point at its target (dropped later if not earlier).
    redirect = {g: t for g, (t, _) in MERGES.items()}
    for r in order:
        r["pre"] = [redirect.get(p, p) for p in r["pre"]]
    for old, new in RENAMES.items():
        for r in order:
            if r["title"] == old:
                r["title"] = new
            r["pre"] = [new if p == old else p for p in r["pre"]]
    for r in order:
        u = UPDATES.get(r["title"], {})
        for k, v in u.items():
            if k == "concepts+":
                r["concepts"] = r["concepts"] + [c for c in v if c not in r["concepts"]]
            else:
                r[k] = v
    assert set(UPDATES) <= {r["title"] for r in order}, set(UPDATES) - {r["title"] for r in order}
    for after, lvl, title, ind, co, scen, eps, cons, infra, pre in NEW5:
        k = next(i for i, r in enumerate(order) if r["title"] == after)
        order.insert(k + 1, {"level": lvl, "title": title, "industry": ind, "company": co, "scenario": scen,
                             "endpoints": eps, "concepts": cons, "infra": infra, "pre": pre})
    # A redirected prerequisite may now point at itself or at a later station; keep only earlier ones.
    pos = {r["title"]: i for i, r in enumerate(order)}
    for i, r in enumerate(order):
        r["pre"] = sorted({p for p in r["pre"] if pos[p] < i}, key=pos.get)
    return order
