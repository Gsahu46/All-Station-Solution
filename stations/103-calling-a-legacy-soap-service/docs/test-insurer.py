"""The insurer's SOAP service for docs/capture.sh (simulated). SOAP 1.1 envelopes written by hand, as an old system
sends them. Saves the last request and answer under the names the capture script asks for.
POST /policy: IssuePolicy. POST /control {"delay": s, "broken": bool, "save": "name"}. Usage: test-insurer.py PORT"""
import json, re, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[1])
STATE = {"delay": 0.0, "broken": False, "save": None, "issued": 0}
NS = "http://insurer.example/policy/v1"


def envelope(content):
    return ('<?xml version="1.0" encoding="UTF-8"?><soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
            f"<soap:Body>{content}</soap:Body></soap:Envelope>")


def fault(code, reason, detail_code=None, detail_message=None):
    detail = "" if detail_code is None else (f'<detail><p:PolicyFault xmlns:p="{NS}"><p:code>{detail_code}</p:code>'
                                             f"<p:message>{detail_message}</p:message></p:PolicyFault></detail>")
    return envelope(f"<soap:Fault><faultcode>{code}</faultcode><faultstring>{reason}</faultstring>{detail}</soap:Fault>")


class Insurer(BaseHTTPRequestHandler):
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
            return self.reply(200, "application/json", json.dumps({k: STATE[k] for k in ("delay", "broken")}))
        xml = raw.decode()
        time.sleep(STATE["delay"])
        field = lambda name: (re.search(rf"<(?:\w+:)?{name}>([^<]*)</", xml) or [None, None])[1]
        product, total = field("productCode"), int(field("sumInsuredPaise"))
        if STATE["broken"]:
            status, answer = 500, fault("soap:Server", "Internal error")
        elif product not in ("TERM10", "HEALTH5"):
            status, answer = 500, fault("soap:Client", "Validation failed", "PRODUCT_UNKNOWN", f"Product {product} is not sold.")
        elif total > 50_000_000_000:
            status, answer = 500, fault("soap:Client", "Validation failed", "SUM_TOO_HIGH", "The sum insured is above the limit for online issuance.")
        else:
            STATE["issued"] += 1
            status, answer = 200, envelope(f'<p:IssuePolicyResponse xmlns:p="{NS}"><p:policyNumber>SG-2026-{STATE["issued"]:06d}</p:policyNumber>'
                                           f"<p:premiumPaise>{total // 1000}</p:premiumPaise></p:IssuePolicyResponse>")
        if STATE["save"]:
            with open(STATE["save"] + ".txt", "w") as f:
                f.write("SOAPAction: " + str(self.headers.get("SOAPAction")) + "\n\n" + xml + "\n\n--- answer (HTTP " + str(status) + ") ---\n\n" + answer + "\n")
        self.reply(status, "text/xml; charset=utf-8", answer)

    def reply(self, status, content_type, text):
        out = text.encode()
        try:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)
        except (BrokenPipeError, ConnectionResetError):
            pass   # the app stopped waiting

    def log_message(self, *args):
        pass


ThreadingHTTPServer(("127.0.0.1", PORT), Insurer).serve_forever()
