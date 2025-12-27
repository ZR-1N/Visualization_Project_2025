import http.server
import socketserver
import threading
from pathlib import Path
from playwright.sync_api import sync_playwright

PORT = 8123
WEB_DIR = Path(__file__).resolve().parent.parent / "web"


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)


def main():
    httpd = socketserver.TCPServer(("", PORT), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    logs = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.on("console", lambda msg: logs.append(f"{msg.type}: {msg.text}"))
        try:
            page.goto(f"http://127.0.0.1:{PORT}/index.html",
                      wait_until="networkidle", timeout=60000)
            try:
                page.click('[data-action="enter"]', timeout=3000)
            except Exception:
                pass
            page.wait_for_timeout(1500)
            page.screenshot(
                path=str(WEB_DIR / "playwright_landscape.png"), full_page=True)
            page.wait_for_timeout(2000)
        finally:
            browser.close()
            httpd.shutdown()

    for entry in logs:
        print(entry)


if __name__ == "__main__":
    main()
