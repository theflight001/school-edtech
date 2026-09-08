# 로컬 미리보기 — Vercel의 rewrites와 같게, 파일이 없으면 index.html을 돌려준다.
import http.server, os, socketserver
class H(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        p = self.path.split("?")[0].lstrip("/")
        if p and not os.path.exists(p) and "." not in p.split("/")[-1]:
            self.path = "/index.html"
        return super().do_GET()
    def log_message(self, *a): pass
socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("", 8912), H) as s:
    print("http://localhost:8912 에서 미리보기 중"); s.serve_forever()
