"""A payment gateway for docs/capture.sh (simulated: no money moves, a charge is an answer). POST /charges answers
201 with a charge id, after DELAY seconds; amounts over 50,00,000 paise are declined (402). Usage: test-gateway.py PORT"""
import json, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[1])
DELAY = 0.0


class Gateway(BaseHTTPRequestHandler):
    def body(self):
        if self.headers.get("Transfer-Encoding", "").lower() == "chunked":   # Java's HttpClient streams the JSON
            data = b""
            while (size := int(self.rfile.readline().strip(), 16)) > 0:
                data += self.rfile.read(size)
                self.rfile.readline()
            self.rfile.readline()
            return json.loads(data)
        return json.loads(self.rfile.read(int(self.headers["Content-Length"])))

    def do_POST(self):
        global DELAY
        body = self.body()
        if self.path == "/delay":   # the capture script makes the gateway hang for the drill
            DELAY = float(body["seconds"])
            self.reply(200, {"delay": DELAY})
            return
        time.sleep(DELAY)
        if body["amountPaise"] > 5_000_000:
            self.reply(402, {"error": "declined"})
        else:
            self.reply(201, {"chargeId": "ch_" + str(body["orderId"])})

    def reply(self, status, data):
        out = json.dumps(data).encode()
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)
        except (BrokenPipeError, ConnectionResetError):
            pass   # the app gave up waiting

    def log_message(self, *args):
        pass


ThreadingHTTPServer(("127.0.0.1", PORT), Gateway).serve_forever()
