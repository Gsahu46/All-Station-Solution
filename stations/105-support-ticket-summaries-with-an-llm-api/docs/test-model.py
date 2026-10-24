"""A simulated model provider for docs/capture.sh, in the shape of Anthropic's Messages API. It does not summarise: it
answers a hand-written summary for each demo ticket, counts tokens roughly (4 characters a token), and saves each
request exactly as it arrived, so the page can show what left Taskloom.
POST /v1/messages. POST /control {"delay": s, "status": n}. Usage: test-model.py PORT"""
import json, re, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[1])
STATE = {"delay": 0.0, "status": 200}
SUMMARIES = {
    "T-1001": "- The customer was charged twice (₹1,499 each) for the Pro plan on 3 October.\n- The agent confirmed the second charge is a duplicate and raised a refund request.\n- The customer wants a refund to the card, not credit; refunds take 5 to 7 working days.",
    "T-1002": "- The parcel shows as delivered but the customer did not receive it.\n- A claim has been opened with the courier.",
    "T-1003": "- The invoice showed the wrong company name.\n- The agent corrected it and sent a new invoice.",
    "T-1004": "- Tasks stopped syncing with the calendar after the update.\n- Reconnecting, clearing the cache and signing in again did not help; the error is 4031.",
}


class Model(BaseHTTPRequestHandler):
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
            STATE.update(json.loads(raw))
            return self.reply(200, {"delay": STATE["delay"], "status": STATE["status"]})
        req = json.loads(raw)
        ticket = re.search(r'<ticket id="(T-\d{4})">', req["messages"][0]["content"])
        ticket = ticket.group(1) if ticket else "unknown"
        with open(f"sent-{ticket}.json", "w") as f:
            json.dump({"headers": {"x-api-key": "(" + str(len(self.headers.get("x-api-key", ""))) + " characters, not shown)",
                                   "anthropic-version": self.headers.get("anthropic-version")}, "body": req}, f, indent=2, ensure_ascii=False)
        time.sleep(STATE["delay"])
        if STATE["status"] != 200:
            return self.reply(STATE["status"], {"type": "error", "error": {"type": "overloaded_error", "message": "Overloaded"}})
        text = SUMMARIES.get(ticket, "- (no summary for this ticket in the simulation)")
        self.reply(200, {"id": "msg_simulated", "type": "message", "role": "assistant", "content": [{"type": "text", "text": text}],
                         "stop_reason": "end_turn",
                         "usage": {"input_tokens": (len(req["system"]) + len(req["messages"][0]["content"])) // 4, "output_tokens": len(text) // 4}})

    def reply(self, status, body):
        out = json.dumps(body).encode()
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)
        except (BrokenPipeError, ConnectionResetError):
            pass   # the app stopped waiting

    def log_message(self, *args):
        pass


ThreadingHTTPServer(("127.0.0.1", PORT), Model).serve_forever()
