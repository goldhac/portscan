"""Local practice lab: fake services on 127.0.0.1 for the scanner to find.

Run:  python lab/lab.py      (Ctrl-C to stop)

Everything binds to 127.0.0.1 only, so nothing is reachable from your network.
High ports (above 1024) mean no admin rights are needed.
"""

import http.server
import socketserver
import threading
import time

HOST = "127.0.0.1"

# Services that speak first: they send a banner as soon as you connect.
BANNERS = {
    2222: ("SSH", b"SSH-2.0-OpenSSH_9.6\r\n"),
    2121: ("FTP", b"220 (vsFTPd 3.0.5)\r\n"),
    2525: ("SMTP", b"220 lab.local ESMTP Postfix\r\n"),
}


class BannerHandler(socketserver.BaseRequestHandler):
    """Send the port's banner, then hang up."""

    def handle(self):
        port = self.server.server_address[1]
        self.request.sendall(BANNERS[port][1])


class RedisHandler(socketserver.BaseRequestHandler):
    """Redis stays silent until the client sends PING."""

    def handle(self):
        self.request.settimeout(5)
        try:
            data = self.request.recv(1024)
        except TimeoutError:
            return
        if b"PING" in data.upper():
            self.request.sendall(b"+PONG\r\n")


class TarpitHandler(socketserver.BaseRequestHandler):
    """Accept the connection, then say nothing (tests scanner timeouts)."""

    def handle(self):
        self.request.settimeout(30)
        try:
            self.request.recv(1024)  # wait for the client to give up
        except (TimeoutError, OSError):
            pass


class QuietHTTP(http.server.SimpleHTTPRequestHandler):
    """Normal HTTP server, minus the per-request log spam."""

    def log_message(self, *args):
        pass


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True  # don't let open connections block Ctrl-C


def main():
    services = [(port, name, BannerHandler) for port, (name, _) in BANNERS.items()]
    services += [
        (8080, "HTTP", QuietHTTP),
        (6379, "Redis", RedisHandler),
        (9999, "Tarpit", TarpitHandler),
    ]
    services.sort()

    servers = []
    for port, name, handler in services:
        srv = Server((HOST, port), handler)
        # Each service runs in its own background thread.
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        servers.append(srv)

    print(f"Lab running on {HOST}  (Ctrl-C to stop)")
    print(f"{'PORT':<6} SERVICE")
    for port, name, _ in services:
        print(f"{port:<6} {name}")

    try:
        while True:
            time.sleep(1)  # sleep until Ctrl-C (sleep stays interruptible on Windows)
    except KeyboardInterrupt:
        print("\nStopping lab...")
    finally:
        for srv in servers:
            srv.shutdown()
            srv.server_close()


if __name__ == "__main__":
    main()
