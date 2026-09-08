#!/usr/bin/env python3
"""Local static server with a small Yahoo Finance chart relay."""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlparse
from urllib.request import Request, urlopen
import json
import os
import re


class AppHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/chart":
            self.proxy_chart(parse_qs(parsed.query))
            return
        super().do_GET()

    def proxy_chart(self, query):
        symbol = query.get("symbol", [""])[0]
        market_range = query.get("range", ["1y"])[0]
        interval = query.get("interval", ["1d"])[0]
        if not re.fullmatch(r"[A-Za-z0-9^=./-]{1,20}", symbol):
            self.send_error(400, "Symbole invalide")
            return

        target = (
            "https://query1.finance.yahoo.com/v8/finance/chart/"
            f"{quote(symbol, safe='') }?range={quote(market_range)}&interval={quote(interval)}&events=history"
        )
        try:
            request = Request(target, headers={"User-Agent": "TDSequentialLocal/1.0"})
            with urlopen(request, timeout=20) as response:
                body = response.read()
            json.loads(body)
        except Exception as error:
            self.send_error(502, f"Yahoo Finance: {error}")
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", os.environ.get("TD_PORT", "8787")))
    host = os.environ.get("HOST", "127.0.0.1")
    print(f"Application disponible sur http://{host}:{port}", flush=True)
    ThreadingHTTPServer((host, port), AppHandler).serve_forever()
