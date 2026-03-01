"""
Minimal HTTPS server for secure localhost (e.g. OAuth redirect).
Run once you have cert.pem and key.pem (see README "Secure localhost").
"""
import ssl
import http.server
import os

PORT = int(os.getenv("PORT", "8888"))
CERT_FILE = os.getenv("SSL_CERT", "cert.pem")
KEY_FILE = os.getenv("SSL_KEY", "key.pem")


def main():
    if not os.path.isfile(CERT_FILE) or not os.path.isfile(KEY_FILE):
        print(f"Missing {CERT_FILE} or {KEY_FILE}. Create them first, e.g.:")
        print('  openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes -subj "/CN=localhost"')
        return 1

    handler = http.server.SimpleHTTPRequestHandler
    with http.server.HTTPServer(("localhost", PORT), handler) as httpd:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(CERT_FILE, KEY_FILE)
        httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
        print(f"HTTPS server at https://localhost:{PORT}/ (Ctrl+C to stop)")
        httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
