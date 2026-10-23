"""A merchant's server for docs/capture.sh, written apart from the Java code: it checks each signature itself.
Answers 503 to the first request (down for maintenance), 200 after. Usage: test-merchant.py PORT SECRET"""
import base64, hashlib, hmac, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT, SECRET = int(sys.argv[1]), sys.argv[2]
KEY = base64.b64decode(SECRET.removeprefix("whsec_"))
count = 0


class Merchant(BaseHTTPRequestHandler):
    def do_POST(self):
        global count
        count += 1
        body = self.rfile.read(int(self.headers["Content-Length"]))
        wid, ts, sig = self.headers["webhook-id"], self.headers["webhook-timestamp"], self.headers["webhook-signature"]
        expected = "v1," + base64.b64encode(hmac.new(KEY, f"{wid}.{ts}.".encode() + body, hashlib.sha256).digest()).decode()
        valid = any(hmac.compare_digest(expected, s) for s in sig.split(" "))
        recent = abs(time.time() - int(ts)) <= 300
        status = 503 if count == 1 else 200
        print(f"request {count}: webhook-id {wid}\n  body {body.decode()}\n  signature valid: {'yes' if valid else 'NO'}, "
              f"timestamp within 5 minutes: {'yes' if recent else 'NO'}\n  answered {status}", flush=True)
        self.send_response(status)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, *args):
        pass


ThreadingHTTPServer(("127.0.0.1", PORT), Merchant).serve_forever()
