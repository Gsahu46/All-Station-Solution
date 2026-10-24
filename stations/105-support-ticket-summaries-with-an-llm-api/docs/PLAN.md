# Station 105 plan: Support ticket summaries with an LLM API

**Problem.** Taskloom (fictional work-management SaaS): agents read 40-message threads before replying. A summary
button must not send customers' personal data to the model provider, must not let a customer's text steer the model,
and must not run up the bill.

**Endpoint.** `POST /tickets/{id}/summary` (HTTP Basic, role AGENT): 200 {ticketId, summary, cached, inputTokens,
outputTokens, omittedMessages, removed{kind: count}}; 400 bad id; 401; 403 customers; 404 unknown or another team's
ticket (the same answer, nothing sent); 429 team budget spent; 503 provider busy (429/529/5xx, Retry-After 60);
504 no answer in 20 s; 502 provider refused our request (logged).

**Fix.** Redactor (email, Luhn-checked card, Aadhaar, Indian mobile, PAN, the customer's name) before sending; our
instructions only in `system`; the thread in the user message inside `<ticket>` with `<` and `>` escaped; the first
message plus the newest that fit in 12,000 characters; max_tokens 400; a team budget of tokens per day (checked
before, charged with real usage after); the last summary per ticket kept by prompt hash; the answer redacted again and
cut to 2,000 characters; logs carry token counts, never text. Not retried.

**Trap.** `SummaryLeakTrapTest`: the old request (the whole thread pasted into `system`, max_tokens 4096) carries the
email, phone, card, PAN and name, the customer's "ignore all previous instructions", and 50,000+ characters.

**Review.** No redaction or escaping ("the provider does not train on API data"); no budget check ("max_tokens caps
it").

**Practice.** 1: tokens left today in each answer. 2: warn when a message looks like instructions to a model.
3 (paper): what may leave Taskloom, and on what terms.

**Simulation.** The model provider is simulated in the shape of Anthropic's Messages API (TestModel in tests,
docs/test-model.py in captures). No real model was called: no key here.
