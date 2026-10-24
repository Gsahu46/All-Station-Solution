# Station 101 plan: Task queue with RabbitMQ

**Problem.** Mediqo (fictional diagnostics lab): lab report PDFs were made in the request thread; at peak, a server
restart lost the reports being made. A first move to a queue used auto-ack, which loses a message the moment a
worker that has it dies.

**Endpoints.** `POST /lab-reports/{id}/render`: 202 once the broker has confirmed the message (publisher confirms);
asked again for a report queued, ready or failed: 200 with its state, nothing sent; broker unreachable or refusing:
503 and nothing recorded. `GET /lab-reports/{id}`: QUEUED, READY (with pdfUrl) or FAILED (with the reason); 404 if
never requested. `GET /lab-reports/{id}/pdf`. Bad id 400, unknown 404. Simulated lab: LR-n has n pages (1 to 500);
LR-0013's scan is damaged; LR-0042's lab system is busy once.

**Topology.** Direct exchange lab-reports, routing key render, durable queue report-render with a dead-letter
exchange lab-reports.dlx to the durable queue report-render.dlq. JSON messages, persistent.

**Worker.** @RabbitListener, Spring's acknowledge-mode auto (ack after the listener returns), prefetch 1, two
consumers. Retry: 3 tries, 1 s then 2 s; after the last, GiveUp records the reason on the report and rejects without
requeue, so the broker dead-letters it. Idempotent: a report already rendered is skipped. A worker whose channel has
closed stops rendering. Reports on disk (requested marker, PDF written then moved, failure note); shortcut: one
machine's disk.

**Trap.** `AutoAckTrapTest` with the plain RabbitMQ client: autoAck, the worker's channel closes before it renders:
the queue is empty and nothing says so. Manual ack: the message is back, flagged redelivered.

**Tests.** Testcontainers RabbitMQ with the management API (used to cut the app's connection mid-render), 5 ms a
page, 100 ms retries.

**Review.** A listener factory with AcknowledgeMode.NONE ("faster").

**Practice.** 1: POST /dead-letters/replay. 2: urgent reports on a priority queue. 3 (paper): RabbitMQ or Kafka.
