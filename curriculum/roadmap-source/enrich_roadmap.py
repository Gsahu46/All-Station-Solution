"""Adds the review's improvements to roadmap.json (run after build_roadmap.py):
stage name, core vs specialisation track, the trap each station must teach, required tests by station type,
reviewer view for advanced stations, and staged milestones for the capstones."""
import json, os

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(W, "curriculum", "roadmap.json")
doc = json.load(open(P))
R = doc["stations"]

STAGE = {"0-1": "Foundations", "0-2": "Working Systems", "2-3": "Production Scale"}

SPECIALISATIONS = {
    "Product catalog on MongoDB", "Calling a legacy SOAP service", "Support ticket summaries with an LLM API",
    "Streaming stock prices with WebFlux", "Internal pricing over gRPC", "GraphQL for the streaming home screen",
    "Product search with OpenSearch", "Surge pricing with Kafka Streams", "Event-sourced insurance claims",
    "Semantic search with pgvector", "Thumbnails with AWS Lambda", "Shopping cart on DynamoDB", "Sharding chat messages",
}

# The plausible-but-wrong approach each station must show failing (with a test where code can show it).
TRAP = {
 "Is the dark store open?": "Returning null or 200 with an empty body for an unknown store instead of 404.",
 "Restaurant menu filters": "Applying limit before sort, so 'cheapest 5' returns 5 random dishes, sorted.",
 "Product search autocomplete": "Scanning every product name with contains() on each keystroke.",
 "Event registration form": "Trusting the client: no validation, so 0 tickets and empty names are saved.",
 "Designing REST resources for gym classes": "Verbs in URLs and 200 for every outcome, so clients cannot tell what happened.",
 "One error shape for a banking API": "Returning exception messages and stack traces, leaking internals to attackers.",
 "Comment moderation and XSS-safe output": "Filtering '<script>' from input instead of encoding output; attackers bypass the filter.",
 "Saved delivery addresses": "Using POST for edits, so a retry on a flaky network creates duplicates.",
 "Wishlist without duplicates": "Overriding equals without hashCode, or using a mutable field as the key.",
 "Threaded comment replies": "Unbounded recursion on deep threads, crashing with StackOverflowError.",
 "Smart parking slot allocation": "Re-scanning every slot on each entry instead of keeping free slots ordered.",
 "Fleet vehicles: abstract classes vs interfaces": "Deep inheritance trees where one change in the base class breaks every vehicle.",
 "Recently viewed products with an LRU cache": "Treating a per-server in-memory cache as shared: each server shows different history.",
 "Fare estimates per vehicle type": "A growing if-else chain where adding one vehicle type breaks another.",
 "Splitting a group bill": "Dividing with double or default rounding, so a paisa goes missing.",
 "Loan EMI calculator and schedule": "Rounding every instalment the same way, so the last one never closes the loan.",
 "GST on invoices": "Hard-coding rates and charging IGST on same-state sales.",
 "Payment methods with sealed interfaces": "One class with nullable fields for every method, so a new method is silently missed.",
 "A Money type for a multi-currency wallet": "Adding amounts in different currencies, or comparing BigDecimal with equals.",
 "Income tax calculator: old vs new regime": "Hard-coded slabs presented as tax advice; rules change every budget.",
 "Bank statement pages": "Unbounded page size, so one request loads millions of rows.",
 "Parsing a bank statement CSV": "Failing the whole file on one bad line, with no line number in the error.",
 "Masking card and Aadhaar numbers in responses": "Masking in the UI only; the full number is still in the API response.",
 "Accepting a partner's snake_case JSON": "Failing on unknown fields, so every new partner field breaks parsing.",
 "Public holidays from a partner API": "No timeout and no handling of the partner's 5xx, so our API hangs or 500s.",
 "OTP request limiter": "An in-memory limiter that only works on one server, and check-then-act races.",
 "Request ids for parcel tracking": "Setting the MDC without clearing it, so the next request on the thread logs the wrong id.",
 "Food order status flow": "Setting any status the client sends, so DELIVERED can come before PREPARING.",
 "Library book loans in layers": "Business rules in controllers, copied into a second entry point and drifting.",
 "Travel insurance premium factors": "Injecting one bean when several exist, or relying on unspecified bean order.",
 "Per-city delivery settings": "Unvalidated config: a typo sets the minimum order to zero and nothing fails.",
 "Appointment reminders in many languages": "Concatenating translated fragments and formatting numbers without the locale.",
 "Return and refund eligibility": "Testing only the happy path; one changed rule breaks another category unnoticed.",
 "Bug triage from a customer ticket": "Fixing the symptom without a failing test first, so the bug returns.",
 "Restaurant chain daily sales report": "Summing money in double and grouping by a mutable key.",
 "Quiz leaderboard ranking": "Ranking by list position, so tied scores get different ranks.",
 "Medicine search with plain JDBC": "Building SQL by string concatenation (SQL injection) and leaking connections.",
 "Bus ticket booking in one transaction": "Auto-commit on: a crash leaves a booking without its passengers.",
 "Gym memberships with migrations and constraints": "Enforcing rules only in Java; another writer inserts invalid rows.",
 "Human-friendly order numbers": "An in-memory counter that repeats numbers after a restart or on two servers.",
 "Short links with click counts": "Random codes without a unique constraint, so collisions overwrite links.",
 "Clinic appointments report with joins": "INNER JOIN hides doctors with zero appointments.",
 "Flash sale without overselling": "Read stock, check, then update: concurrent buyers oversell.",
 "Doctor directory with JPA": "Returning entities directly as JSON, leaking fields and lazy-loading errors.",
 "Hotel room availability calendar": "Comparing only start dates, so overlapping bookings are accepted.",
 "Order DTOs with MapStruct": "Hand-written mapping that silently skips a newly added field.",
 "Employee leave requests": "Changing a managed entity outside a transaction and expecting it to be saved.",
 "Invoices and their line items": "Removing a line from the collection without orphanRemoval, leaving orphan rows.",
 "Product reviews and ratings": "Recomputing the average over millions of rows on every page view.",
 "Course enrolments with progress": "@ManyToMany for a link that needs its own data, with nowhere to store it.",
 "Hotel booking request validation": "Validating each field alone, so check-out before check-in passes.",
 "Webinar scheduling across time zones": "Storing LocalDateTime without a zone, so times shift for other countries.",
 "Recurring bill reminders": "Adding 30 days for 'monthly', or assuming every month has a 31st.",
 "Bank notifications by channel": "One class doing SMS, email and push, so one change breaks all three.",
 "Sign-up emails on MySQL and PostgreSQL": "Assuming case-insensitive uniqueness works the same on both databases.",
 "Archiving seller products": "Hard-deleting rows that past orders still reference.",
 "Checkout as one transaction": "Calling a @Transactional method from the same class, so no transaction starts.",
 "Timing and auditing with Spring AOP": "Expecting aspects to run on private, final or self-invoked methods.",
 "Audit trail that survives a rollback": "Writing the audit row in the same transaction, so it rolls back too.",
 "Welcome emails with Spring application events": "Sending email in a plain listener before commit; failed sign-ups still get mail.",
 "Transactional emails from templates": "Building HTML by string concatenation without escaping or UTF-8.",
 "Loyalty points tested on real PostgreSQL": "Testing on H2 and shipping SQL that PostgreSQL rejects.",
 "Inventory sync with MySQL upserts": "Select-then-insert under concurrency, causing duplicates and gap-lock deadlocks.",
 "Restaurant list without N+1 queries": "Lazy loading inside a loop: 1 + N queries per page.",
 "Shipment search by phone number": "Adding an index without checking EXPLAIN, or in the wrong column order.",
 "Hotel search with optional filters": "Concatenating optional filters and sort fields into SQL.",
 "Dish search with PostgreSQL full-text": "LIKE '%term%' that cannot use an index and misses word forms.",
 "Seller catalog pages": "Sorting by a non-unique column, so items repeat or vanish between pages.",
 "Social feed with keyset pagination": "Deep OFFSET paging that gets slower page by page and duplicates new posts.",
 "Category tree and breadcrumbs": "One query per level, and no protection against cycles.",
 "Flexible product attributes with jsonb": "Putting everything in jsonb, including fields that need constraints and joins.",
 "Scheduled price changes": "Overwriting the price at a scheduled time instead of storing dated prices.",
 "Product catalog on MongoDB": "Using a document store for data that needs joins and multi-document transactions.",
 "Job portal sign-up and passwords": "Fast hashes like MD5 or SHA-256 without a work factor.",
 "Password reset by email": "Reusable, non-expiring tokens and different replies for known and unknown emails.",
 "Login with JWT for a fitness app": "Not checking signature, expiry or algorithm; long-lived tokens that cannot be revoked.",
 "Device sessions for a streaming app": "Refresh tokens that never rotate, so a stolen one works for months.",
 "Sign in with Google": "Accepting any ID token without checking issuer and audience.",
 "Two-factor login with TOTP": "No rate limit on codes and no way to recover a lost device.",
 "Hospital staff roles": "Checking roles only in the UI, while every endpoint stays open.",
 "Customers see only their own accounts": "Trusting the id in the URL without an ownership check (IDOR).",
 "Task board edits without lost updates": "Last write wins: two editors silently overwrite each other.",
 "Who changed this price?": "Logging changes as free text, so history cannot be queried or trusted.",
 "Movie seat holds": "Locking without a timeout or holding locks across remote calls.",
 "On-call doctor roster": "Assuming READ COMMITTED prevents write skew.",
 "Daily wallet limits": "Summing today's top-ups without locking, so two top-ups pass the limit.",
 "Idempotent UPI-style payments": "Retrying a timed-out payment without an idempotency key, charging twice.",
 "One API for many payment providers": "Failing over to a second provider after a timeout when the first may already have charged.",
 "Order API v2 without breaking old apps": "Renaming or removing fields in place, breaking old app versions.",
 "App config with HTTP caching": "No ETag or Cache-Control, so every launch downloads the same config.",
 "Serving product images through a CDN": "Overwriting images at the same URL, so the CDN serves stale files.",
 "Partner shipping-rate API docs": "Hand-written docs that drift from the real API.",
 "Bulk shipment creation": "All-or-nothing batches with no per-item results.",
 "KYC document upload": "Trusting the file name and Content-Type, and loading whole files into memory.",
 "Order export to CSV": "Building the whole file in memory, and not escaping cells that start with '='.",
 "Image previews without SSRF": "Fetching any URL the user sends, including internal addresses.",
 "Resumable statement downloads": "Ignoring Range, so every retry downloads from the start.",
 "Webhooks to merchants": "Fire-and-forget delivery with no signature, retry or delivery log.",
 "Partner API keys and quotas": "One global limit, so one partner's bug slows everyone.",
 "Behind a load balancer": "Trusting X-Forwarded-For from anyone, so clients can spoof their IP.",
 "Invoice PDFs without blocking": "@Async on the default executor with unbounded queues and swallowed errors.",
 "Live order status with Server-Sent Events": "Never timing out emitters, leaking connections and threads.",
 "Testing asynchronous code reliably": "Thread.sleep in tests, making them slow and flaky.",
 "Expiring unpaid hotel holds": "A @Scheduled job that runs on every server at once.",
 "Task queue with RabbitMQ": "Auto-ack, so messages are lost when a worker crashes.",
 "Ticket sale when the pool runs dry": "Calling remote services inside a transaction while holding a connection.",
 "Exchange rates with an in-memory cache": "Caching without TTL or size limits.",
 "Calling a legacy SOAP service": "No timeout on a slow legacy service, and SOAP faults turned into 500s.",
 "Support ticket summaries with an LLM API": "Sending personal data and untrusted text to the model with no cost limit.",
 "Partial refund approvals": "Checking the refund total only in Java, so concurrent refunds exceed the order.",
 "Referral rewards without abuse": "Rewarding at sign-up instead of after a real order, with no idempotency.",
 "Tenant isolation in a CRM": "Taking the tenant id from the request body, or forgetting it in one query.",
 "Account deletion and data export": "Deleting from one table while copies remain in logs, backups and other tables.",
 "Subscription plan changes": "Charging the full new price without crediting unused time.",
 "Seller bulk price upload": "One huge transaction, so one bad row rolls back 200,000 good ones.",
 "Reviewing a pull request": "Approving because the happy path works.",
 "Fixing a dependency conflict": "Pinning random versions until it compiles, without reading the dependency tree.",
 "Upgrading to a new Spring Boot major version": "Jumping several majors at once with no tests.",
 "API security audit (OWASP API Top 10)": "Binding request bodies straight to entities, so clients can set fields like role or balance.",
 "Finding the slow travel search": "Optimising by guesswork without measuring.",
 "Load testing checkout": "Testing average latency on a laptop instead of percentiles at realistic load.",
 "Nearby drivers": "Computing distance to every driver in the city on each request.",
 "Ingesting driver locations": "Unbounded queues that hide overload until memory runs out.",
 "Product pages with Redis cache-aside": "Caching without TTL and serialising with Java serialisation.",
 "Flash-sale prices and stale caches": "Letting every request reload an expired key at the same moment (stampede).",
 "Login attempt limits across servers": "GET then SET in Redis, which races; or failing open when Redis is down.",
 "Live fantasy cricket leaderboard": "ORDER BY over millions of rows for every rank request.",
 "Like counts on a viral post": "UPDATE ... SET likes = likes + 1 on one row for every like.",
 "Delayed jobs for scheduled reminders": "Scanning the whole table every minute, with two workers sending the same job.",
 "Chat with delivery receipts": "Assuming all users connect to the same server.",
 "Push notifications to millions": "Sending one by one with no batching, ignoring provider limits.",
 "One driver per ride": "A Redis lock without a lease or fencing token; a slow holder overwrites after expiry.",
 "Receiving bank payment webhooks": "Processing before verifying the signature, with no deduplication.",
 "Fraud rules for transactions": "Slow inline checks that block every payment, with no fallback.",
 "Flight fare aggregator": "Sequential calls with no per-call timeout, so one slow airline delays everything.",
 "Streaming stock prices with WebFlux": "Calling blocking code inside a reactive pipeline.",
 "Pincode serviceability from another service": "Default timeouts (infinite), so a hung dependency hangs checkout.",
 "Internal pricing over gRPC": "No deadlines, so slow calls pile up.",
 "GraphQL for the streaming home screen": "Resolvers that query per item (N+1) and no limit on query depth.",
 "Retrying the SMS provider safely": "Immediate retries of non-idempotent calls, multiplying load during an outage.",
 "Circuit breaker for a payment partner": "Treating a breaker as a retry; or a fallback that pretends the payment succeeded.",
 "Respecting a courier partner's rate limit": "Bursting past the partner's limit and getting the account blocked.",
 "Home screen that survives a slow dependency": "Sharing one thread pool, so one slow dependency starves everything.",
 "Publishing order events": "Sending events without keys, losing per-order ordering.",
 "Trip events in order": "More consumers than partitions, or keys that break ordering.",
 "Loyalty points from order events, exactly once in effect": "Assuming Kafka delivers once; a restart credits points twice.",
 "Kafka transactions for payment events": "Believing Kafka transactions also cover the database or a payment provider.",
 "Email consumer and poison messages": "Infinite retries on a bad message, blocking the partition.",
 "Account opening with an outbox": "Writing to the database and Kafka separately (dual write); consumers must still dedupe.",
 "Shipment events that evolve": "Removing or renaming fields in events that consumers still read.",
 "Order tracking read model": "Assuming the read model is always current.",
 "Product search with OpenSearch": "Treating the search index as the source of truth.",
 "Surge pricing with Kafka Streams": "Ignoring late events and state-store recovery.",
 "Event-sourced insurance claims": "Event sourcing everything, including simple CRUD data.",
 "Semantic search with pgvector": "Re-embedding everything on every change, with no cost control.",
 "Splitting hotel booking from inventory": "Splitting services that share one database.",
 "Contract tests between services": "Relying on mocks written by the consumer that never check the real provider.",
 "Replacing a legacy endpoint with a strangler fig": "A big-bang rewrite with no way to compare old and new results.",
 "Ports and adapters for a payments module": "Layers of interfaces with no second adapter and no benefit.",
 "Food order saga by events": "Expecting a distributed transaction; a failure leaves money taken and no order.",
 "Orchestrated trip booking": "Steps that are not idempotent, so a retry books twice.",
 "API gateway and service discovery": "Putting business logic in the gateway.",
 "Service-to-service security for payouts": "Trusting any caller inside the network.",
 "Tracing a checkout across services": "Losing the trace context at async and Kafka boundaries.",
 "Health, metrics and alerts for payments": "A health check that says UP while payments fail, and alerts on causes instead of symptoms.",
 "Structured logs without patient data": "Logging whole request bodies with personal data.",
 "Encrypting Aadhaar and PAN at rest": "Keys stored next to the data, with no rotation or access control.",
 "Containerising a pharmacy service": "Running as root, with JVM memory not sized to the container limit.",
 "Local stack with Docker Compose": "Assuming the database is ready as soon as its container starts.",
 "A CI pipeline for a service": "Skipping tests to make the build green.",
 "Patching a vulnerable dependency": "Not knowing which services include the vulnerable library.",
 "Secrets and per-environment configuration": "Secrets committed to Git or printed in logs.",
 "Feature flags and gradual rollout": "Flags that never get removed, and random rollout per request instead of per user.",
 "Releasing a ride app on AWS without downtime": "No graceful shutdown and no tested rollback.",
 "Running on Kubernetes with autoscaling": "A liveness probe that checks the database, so a database blip restarts every pod.",
 "Large video uploads to S3": "Streaming huge uploads through the API servers.",
 "Infrastructure as code with Terraform": "Changing infrastructure by hand so it drifts from Terraform state.",
 "Order processing with Amazon SQS": "A visibility timeout shorter than processing time, so messages run twice.",
 "Fan-out with SNS and SQS": "Subscribers that are not idempotent, under at-least-once delivery.",
 "Thumbnails with AWS Lambda": "Ignoring cold starts and retries, so a failing image loops forever.",
 "Shopping cart on DynamoDB": "Designing tables like SQL and then needing scans.",
 "Secrets from AWS Secrets Manager": "Fetching the secret on every request, or never refreshing it after rotation.",
 "Monitoring with CloudWatch": "High-cardinality metrics and verbose logs that run up the bill.",
 "Testing AWS code with LocalStack": "Assuming LocalStack behaves exactly like AWS.",
 "Zero-downtime schema change": "Renaming a column in one release, breaking the running old version.",
 "Recovering from an accidental DELETE": "Having backups that were never restored and checked.",
 "Order history from read replicas": "Reading your own write from a lagging replica.",
 "Partitioning a huge tracking-events table": "Queries without the partition key, which scan every partition.",
 "Sharding chat messages": "A shard key that creates hot shards, or needs cross-shard queries for common reads.",
 "Disaster recovery across regions": "A failover plan that has never been rehearsed.",
 "Troubleshooting a ticketing incident": "Restarting the service before capturing evidence.",
 "JVM memory and garbage collection tuning": "Tuning GC flags before reducing allocation.",
 "Deadlocks in wallet transfers": "Locking accounts in request order instead of a consistent order.",
 "A double-entry wallet ledger": "Updating a balance column without immutable entries.",
 "Payment reconciliation with bank files": "Matching on amount alone.",
 "Nightly merchant settlement": "A job that restarts from zero and pays some merchants twice.",
 "Usage metering for billing": "Counting from logs, where duplicates and late events skew the bill.",
 "Capstone: quick-commerce order flow": "Building it in one go, with no milestones, failure drills or design records.",
 "Capstone: ride-hailing dispatch platform": "Designing only for the happy path, with no degraded modes.",
 "Capstone: payments platform": "Trusting that totals balance in the demo without testing failures in the middle of a payment.",
}

# Round 5: follow the merges, renames and additions in round5.py.
import sys; sys.path.insert(0, os.path.join(W, "curriculum")); import round5
for _gone in round5.MERGES:
    TRAP.pop(_gone)
for _old, _new in round5.RENAMES.items():
    TRAP[_new] = TRAP.pop(_old)
TRAP.update({
 "Help-centre answers with RAG": "Answering from the model's memory with no retrieval, citations or evaluation, so wrong answers sound confident.",
 "Passkey sign-in with WebAuthn": "Not checking the challenge, origin and relying-party id, so a phishing site can replay a sign-in.",
 "Health, metrics and SLOs for payments": "A health check that says UP while payments fail, and alerts on raw error counts instead of SLO burn rate.",
 "Large media uploads and CDN delivery": "Streaming huge files through the API servers, and overwriting files at the same URL so the CDN serves stale copies.",
 "Expose an API to AI agents with MCP": "Exposing every endpoint as a tool with the server's own privileges, so any agent can do anything.",
 "Document sharing with relationship-based permissions": "Copying permissions onto each document, so removing someone from a team leaves old access behind.",
 "Saving cards with network tokens": "Keeping the card number 'just for retries', which breaks RBI rules and pulls every system into PCI scope.",
 "Subscriptions with UPI AutoPay mandates": "Debiting without the 24-hour pre-debit notice, or retrying a debit that actually succeeded.",
 "Enterprise integration with Apache Camel": "Processing the same file twice after a restart because nothing records what was already consumed.",
 "Tests that catch weak tests": "Trusting a high coverage number when the tests assert nothing that matters.",
 "Change data capture with Debezium": "Assuming change data capture delivers each change exactly once and in one global order.",
 "A tool-calling agent with guardrails": "Giving the agent write tools with no limits and no human approval.",
 "An AI gateway for many models": "Hard-coding one provider with no per-team budget, so one bug burns the month's spend.",
 "Cell-based architecture for a SaaS": "Calling it cells while every cell still shares one database.",
 "COBOL-to-Java with characterisation tests": "Rewriting from the written spec alone without comparing outputs on real historical data.",
 "ISO 20022 payment messages": "Squeezing structured XML into old free-text fields and losing data needed for screening.",
 "Loan checks with Account Aggregator consent": "Keeping consented financial data after the consent expires or is revoked.",
})
SPECIALISATIONS -= set(round5.MERGES) | {"Semantic search with pgvector"}
SPECIALISATIONS |= {"ISO 20022 payment messages", "Loan checks with Account Aggregator consent"}

MILESTONES = {
 "Capstone: quick-commerce order flow": [
  "M1 Order API with validation, errors and migrations",
  "M2 Inventory reservations: reserve, confirm, release, with concurrency tests",
  "M3 Payments with idempotency keys and webhook handling",
  "M4 Events with an outbox, idempotent consumers and a dead-letter topic",
  "M5 Redis caching, observability, Docker Compose, failure drills and design records"],
 "Capstone: ride-hailing dispatch platform": [
  "M1 Rider and driver APIs with authentication",
  "M2 Location ingest and nearby search",
  "M3 Matching with locks and fencing, then pricing",
  "M4 Trip events, surge pricing and the tracking read model",
  "M5 Degraded modes, load test, observability and failure drills"],
 "Capstone: payments platform": [
  "M1 Payment intents with idempotency and provider adapters",
  "M2 Unknown outcomes: status checks and webhooks",
  "M3 Double-entry ledger with reversals",
  "M4 Settlement and reconciliation with bank files",
  "M5 Audit, encryption at rest, alerts and failure drills"],
}

# Required tests by station type. Matched with word boundaries on the station's own words, then corrected by hand
# in TYPE_FIX after reading the full list. Every station also gets the baseline.
import re
TYPES = [
 ("Database", r"\b(postgres|mysql|mongodb|jdbc|sql|jpa|flyway|migrations?|index(es)?|transactions?|constraints?|dynamodb|database|replicas?|partition(ing)?|ledger)\b",
  "rollback and constraint tests against a real database"),
 ("Security", r"\b(auth\w*|jwt|tokens?|passwords?|roles?|idor|tenant\w*|xss|ssrf|oauth\w*|totp|api keys?|signatures?|encrypt\w*|masking|owasp|secrets?|personal data|fraud|security)\b",
  "401, 403 and one user accessing another user's data; malicious input"),
 ("Concurrency", r"\b(race\w*|concurren\w*|locks?|locking|oversell\w*|deadlocks?|contention|atomic|lost update|write skew|skip locked|hot rows?|fencing)\b",
  "a real concurrency test that proves the invariant holds"),
 ("Messaging", r"\b(kafka|rabbitmq|sqs|sns|consumers?|events?|queues?|webhooks?|outbox|sagas?)\b",
  "duplicate-delivery, retry and dead-letter tests"),
 ("Idempotency", r"\b(idempoten\w*|replay\w*|retr(y|ies|ied))\b",
  "a replay test: the same request twice gives one effect"),
 ("Operations", r"\b(docker|k8s|kubernetes|aws|terraform|ci|metrics?|alerts?|alarms?|health|tracing|traces|release\w*|recover\w*|incident|garbage|disaster|load test\w*|cloudwatch|deploy\w*|rollout|containers?)\b",
  "operations section: metric, alert, rollback and runbook; a controlled failure drill"),
]
TYPE_FIX = {
 'Event registration form': (set(), {'Messaging', 'Operations'}),
 'One error shape for a banking API': ({'Security'}, {'Operations'}),
 'Recently viewed products with an LRU cache': ({'Concurrency'}, set()),
 'Request ids for parcel tracking': ({'Operations'}, set()),
 'Short links with click counts': ({'Concurrency'}, {'Idempotency'}),
 'Hotel room availability calendar': ({'Concurrency'}, set()),
 'Loyalty points tested on real PostgreSQL': (set(), {'Operations'}),
 'Two-factor login with TOTP': (set(), {'Operations'}),
 'One API for many payment providers': ({'Idempotency'}, set()),
 'KYC document upload': ({'Security'}, set()),
 'Order export to CSV': ({'Security'}, set()),
 'Partner API keys and quotas': (set(), {'Idempotency'}),
 'Behind a load balancer': ({'Security'}, set()),
 'Expiring unpaid hotel holds': ({'Concurrency'}, set()),
 'Task queue with RabbitMQ': ({'Idempotency'}, set()),
 'Partial refund approvals': ({'Concurrency'}, set()),
 'Upgrading to a new Spring Boot major version': (set(), {'Database', 'Security'}),
 'Login attempt limits across servers': ({'Security'}, set()),
 'Chat with delivery receipts': ({'Messaging'}, set()),
 'Push notifications to millions': ({'Messaging'}, {'Security'}),
 'One driver per ride': (set(), {'Security'}),
 'Flight fare aggregator': ({'Concurrency'}, set()),
 'Home screen that survives a slow dependency': ({'Concurrency'}, set()),
 'Contract tests between services': (set(), {'Messaging'}),
 'Structured logs without patient data': ({'Operations'}, set()),
 'Zero-downtime schema change': ({'Operations'}, set()),
 'Partitioning a huge tracking-events table': (set(), {'Messaging'}),
 'Payment reconciliation with bank files': (set(), {'Messaging'}),
 'Bank statement pages': (set(), {'Database'}),
 'Capstone: quick-commerce order flow': ({'Security', 'Operations', 'Idempotency', 'Concurrency', 'Database', 'Messaging'}, set()),
 'Capstone: ride-hailing dispatch platform': ({'Security', 'Operations', 'Idempotency', 'Concurrency', 'Database', 'Messaging'}, set()),
 'Capstone: payments platform': ({'Security', 'Operations', 'Idempotency', 'Concurrency', 'Database', 'Messaging'}, set()),
}
TYPE_FIX.update({
 "Document sharing with relationship-based permissions": ({"Security"}, set()),
 "Expose an API to AI agents with MCP": (set(), {"Operations"}),
 "Subscriptions with UPI AutoPay mandates": ({"Messaging"}, set()),
 "Cell-based architecture for a SaaS": ({"Operations"}, {"Security"}),
 "Help-centre answers with RAG": ({"Security"}, set()),
 "A tool-calling agent with guardrails": ({"Security"}, set()),
 "Large media uploads and CDN delivery": ({"Security"}, set()),
})
BASELINE = "HTTP contract tests (valid, invalid, not found) and a test that reproduces the failure before the fix"

def text(r):
    return " ".join([r["title"], r["scenario"], " ".join(r["concepts"]), r["infra"]]).lower()

for r in R:
    r["stage"] = STAGE[r["level"]]
    r["suggested_experience"] = r["level"] + " years"
    r["track"] = "Specialisation" if r["title"] in SPECIALISATIONS else "Core"
    assert r["title"] in TRAP, "missing trap: " + r["title"]
    r["trap"] = TRAP[r["title"]]
    t = text(r)
    kinds = [name for name, rx, _ in TYPES if re.search(rx, t)]
    add, remove = TYPE_FIX.get(r["title"], (set(), set()))
    kinds = [k for k, _, _ in TYPES if (k in kinds or k in add) and k not in remove]
    r["station_types"] = kinds
    r["required_tests"] = [BASELINE] + [desc for name, keys, desc in TYPES if name in kinds]
    r["reviewer_view"] = r["stage"] == "Production Scale" or any(k in kinds for k in ("Security", "Concurrency"))
    if r["title"] in MILESTONES:
        r["milestones"] = MILESTONES[r["title"]]
assert set(TRAP) == {r["title"] for r in R}, set(TRAP) ^ {r["title"] for r in R}
assert all(r["track"] == "Core" for r in R if r["title"].startswith("Capstone"))

doc.update(version=3.0, name="200 API & Backend Engineering Stations",
           note="Companies are fictional and inspired by real industries. Finishing the stations builds the skills, "
                "judgement and portfolio needed for backend roles at these levels; it is not the same as years of production experience.")
open(P + ".tmp", "w").write(json.dumps(doc, indent=1, ensure_ascii=False))
json.load(open(P + ".tmp")); os.replace(P + ".tmp", P)
from collections import Counter
print(len(R), "stations;", Counter(r["track"] for r in R), Counter(k for r in R for k in r["station_types"]),
      "reviewer views:", sum(r["reviewer_view"] for r in R))
