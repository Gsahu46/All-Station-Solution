# Station 098 plan: Invoice PDFs without blocking

**Problem.** Billora (fictional invoicing company): making a 300-page invoice PDF held a request thread for 40 s.
Moving it to `@Async` on Spring Boot's default pool fixed the wait but queued every request without limit, and a
failed render left its job "running" for ever (the exception only reached a log).

**Endpoints.** `POST /invoices/{id}/pdf-jobs`: 202 with Location /pdf-jobs/{uuid} and the operation; the same invoice
while its job is queued or running: 200, the same job; unknown invoice 404, bad id 400; pool and queue full 503 with
Retry-After 30. `GET /pdf-jobs/{jobId}`: the operation (AIP-151 shape: name, done, metadata {invoiceId, state,
pagesDone, pagesTotal, createdAt}, then response {pdfUrl, pages, bytes} or error {code, message}); 404, 400. `GET
/pdf-jobs/{jobId}/pdf`: the PDF (attachment); 409 not ready or failed.

**Execution.** A ThreadPoolTaskExecutor bean "pdfExecutor": 2 workers, queue 20 (demo rules), AbortPolicy, waits for
running renders on shutdown. Renderer is a separate bean (@Async works through a proxy), `@Async("pdfExecutor")`,
returns CompletableFuture; PdfJobs attaches whenComplete: SUCCEEDED with the PDF, or FAILED with the cause's message
(unwrapped from CompletionException). Simulated: invoice INV-2026-n has n pages, 130 ms a page; INV-2026-0013 fails.
The PDF is a real minimal one (one line per page). In memory (shortcut).

**Trap.** `AsyncTrapTest`: Boot's default pool settings (8 threads, queue Integer.MAX_VALUE, read from Boot's own
TaskExecutionProperties) accept 1,000 jobs with no refusal (8 running, 992 waiting); an `@Async void` method's
exception leaves the job RUNNING. The API: 503 when full; FAILED with the reason.

**Tests.** 5 ms a page, 2 workers, queue 3. Awaitility everywhere a test waits.

**Review.** Boot's default executor; `thenAccept` instead of `whenComplete`.

**Practice.** 1: Retry-After on unfinished jobs. 2: `POST /pdf-jobs/{id}:cancel`. 3 (paper): many servers.
