# Station 092 plan: KYC document upload

**Problem.** Tijori (fictional): a 2 GB "PAN card" upload took the server down (getBytes() held it in memory); a file
named ../../etc/passwd was written outside the upload folder; a program sent as application/pdf was stored as a PDF.

**Endpoints.** `POST /kyc/{customerId}/documents` (multipart: type, file): 201 with id, type, cleaned-up fileName,
detected contentType, sizeBytes, sha256; over 5 MB 413 (Tomcat's multipart limit, before our code); not PDF/PNG/JPEG
by its first bytes 415; empty 400; bad type 400. `GET /kyc/{customerId}/documents`: own list; reviewer any; unknown
customer (reviewer) 404. HTTP Basic: asha (1), rohan (2), kavya (reviewer). Others 403, none 401.

**Storage.** Local folder standing for object storage: root/customerId/random-UUID. Streamed in 8 KB pieces with a
second 5 MB limit of our own, hashed with DigestInputStream; parts above 64 KB go to a temporary file, not memory.
The list is in memory (shortcut comment).

**Trap.** `TrustedFileNameTrapTest`: the old code's resolve(originalFilename) writes two folders up and trusts the
header; the API keeps the file in its folder under a UUID and refuses an EXE sent as application/pdf.

**Found while building.** (1) MockMvc never applies multipart limits: the size test runs on a real port. (2) Far over
the limit, Tomcat answers 413 and closes the connection; curl reads the 413, Java's HttpClient (still sending) sees
the connection close; both store nothing. (3) With our own copy limit in place, removing the server limit changed no
test: the size test now checks the 413 comes from the server's limit. (4) The first stream test never ended under
its mutation: bounded at 64 MB.

**Mutations.** client name as path -> 3; no sniffing -> 3; no server limit -> 1; no copy limit -> 1; full name kept
-> 2; leading dots kept -> 1; no owner check on upload -> 1; anyone may list -> 1; empty file accepted -> 1.

**Review.** Customer's own file name (getFileName()) and type by extension: 6 of 12 fail.

**Practice.** 1: download as an attachment with the detected type. 2: the same bytes uploaded twice are one document.
3 (paper): direct uploads to object storage with pre-signed URLs, and virus scanning.
