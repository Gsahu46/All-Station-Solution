"""A simulated wallet service for docs/capture.sh. Credits once per Idempotency-Key; answers the statuses planned
through /control, then 200; logs every request to wallet.txt.
POST /credits. POST /control {"plan": [503, 400]}. Usage: test-wallet.py PORT"""
import json, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[1])
STATE = {"plan": [], "credited": {}}


class Wallet(BaseHTTPRequestHandler):
    def body(self):
        if self.headers.get("Transfer-Encoding", "").lower() == "chunked":
            data = b""
            while (size := int(self.rfile.readline().strip(), 16)) > 0:
                data += self.rfile.read(size)
                self.rfile.readline()
            self.rfile.readline()
            return data
        return self.rfile.read(int(self.headers.get("Content-Length", 0)))

    def do_POST(self):
        raw = self.body()
        if self.path == "/control":
            STATE["plan"] = json.loads(raw)["plan"]
            return self.answer(200)
        key = self.headers.get("Idempotency-Key")
        status = STATE["plan"].pop(0) if STATE["plan"] else 200
        note = ""
        if status == 200:
            note = "credited" if key not in STATE["credited"] else "already credited for this key: nothing more"
            STATE["credited"].setdefault(key, json.loads(raw))
        with open("wallet.txt", "a") as f:
            f.write(f"Idempotency-Key: {key}  body: {raw.decode()}  -> {status} {note}\n")
        self.answer(status)

    def answer(self, status):
        self.send_response(status)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, *args):
        pass


ThreadingHTTPServer(("127.0.0.1", PORT), Wallet).serve_forever()
