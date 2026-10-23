"""A load balancer for docs/capture.sh: takes requests on PORT, forwards them to the app on APP_PORT, and adds what a
real one adds: the client's address appended to X-Forwarded-For, X-Forwarded-Proto https (as if it ended TLS) and
X-Forwarded-Host maps.mapwise.example. Usage: test-balancer.py PORT APP_PORT"""
import http.client, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT, APP = int(sys.argv[1]), int(sys.argv[2])
HOP = {"connection", "keep-alive", "transfer-encoding", "host"}


class Balancer(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def forward(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        headers = {k: v for k, v in self.headers.items() if k.lower() not in HOP}
        prior = self.headers.get("X-Forwarded-For")
        headers["X-Forwarded-For"] = (prior + ", " if prior else "") + self.client_address[0]   # appended, never replaced
        headers["X-Forwarded-Proto"] = "https"
        headers["X-Forwarded-Host"] = "maps.mapwise.example"
        app = http.client.HTTPConnection("127.0.0.1", APP, timeout=60)
        app.request(self.command, self.path, body=body, headers=headers)
        r = app.getresponse()
        data = r.read()
        self.send_response(r.status)
        for k, v in r.getheaders():
            if k.lower() not in HOP | {"content-length"}:
                self.send_header(k, v)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    do_GET = do_POST = forward

    def log_message(self, *args):
        pass


ThreadingHTTPServer(("127.0.0.1", PORT), Balancer).serve_forever()
