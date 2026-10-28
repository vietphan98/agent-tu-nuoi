#!/usr/bin/env python3
"""agent-tu-nuoi: dashboard theo dõi AI agent tự đi làm nuôi chính nó.
Chỉ dùng Python stdlib. Chạy: python3 server.py  (mặc định bật chế độ giả lập)
"""
import argparse, json, random, threading, time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path

HERE = Path(__file__).parent
STATE = {"balance": 0.0, "cost": 0.0, "value": 0.0, "jobs": 0, "log": [], "started": time.time(), "plan": 20.0}
LOCK = threading.Lock()

GOOD = [("Viết mô tả sản phẩm cho shop online", 3.0, 6.0), ("Dịch 1 trang tài liệu Anh → Việt", 2.0, 4.5),
        ("Sửa bug CSS cho landing page", 4.0, 8.0), ("Tóm tắt 20 email khách hàng", 1.5, 3.5),
        ("Viết script Python đổi tên file", 2.5, 5.0)]
BAD = [("Thử lại build lỗi lần thứ 7", -0.1, 0.2), ("Đọc lại toàn bộ codebase 'cho chắc'", 0, 0.3),
       ("Gọi model lớn để viết commit message", 0, 0.1), ("Vòng lặp tự sửa test vô hạn", 0, 0)]

def add(kind, text, cost, value):
    with LOCK:
        STATE["cost"] += cost; STATE["value"] += value; STATE["jobs"] += 1
        STATE["balance"] = STATE["value"] - STATE["cost"]
        STATE["log"].insert(0, {"t": time.strftime("%H:%M:%S"), "kind": kind, "text": text,
                                "cost": round(cost, 2), "value": round(value, 2)})
        del STATE["log"][40:]

def simulate(speed, scenario):
    """Giai đoạn 1: làm ăn có lãi. Giai đoạn 2: đốt token vô ích (nếu scenario=crash)."""
    random.seed(7); add("info", "Agent thức dậy. Mục tiêu: tự trả gói Pro.", 0, 0)
    tick = 0
    while True:
        time.sleep(1.0 / speed); tick += 1
        broke = scenario == "crash" and tick > 12 or scenario == "random" and random.random() < 0.45
        if scenario == "comeback": broke = tick <= 12
        if broke:
            text, lo, hi = random.choice(BAD); add("burn", text, random.uniform(4.0, 7.0), random.uniform(max(lo, 0), hi))
        else:
            text, lo, hi = random.choice(GOOD); add("job", text, random.uniform(0.3, 1.0), random.uniform(lo, hi))

def snapshot():
    with LOCK:
        s = dict(STATE); s["log"] = list(STATE["log"])
    b = s["balance"]
    s["mood"] = "happy" if b >= 5 else "ok" if b >= 0 else "worried" if b > -10 else "dying"
    return s

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path == "/events":
            self.send_response(200); self.send_header("Content-Type", "text/event-stream"); self.send_header("Cache-Control", "no-cache"); self.end_headers()
            try:
                while True:
                    self.wfile.write(f"data: {json.dumps(snapshot(), ensure_ascii=False)}\n\n".encode()); self.wfile.flush(); time.sleep(0.5)
            except (BrokenPipeError, ConnectionResetError): return
        elif self.path == "/api/state":
            body = json.dumps(snapshot(), ensure_ascii=False).encode(); ct = "application/json; charset=utf-8"
        elif self.path in ("/", "/index.html"):
            body = (HERE / "index.html").read_bytes(); ct = "text/html; charset=utf-8"
        else:
            self.send_error(404); return
        self.send_response(200); self.send_header("Content-Type", ct); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_POST(self):
        # Agent thật gửi sự kiện: {"text":..., "cost":..., "value":...}
        if self.path != "/api/event": self.send_error(404); return
        d = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        add(d.get("kind", "job"), d.get("text", "việc không tên"), float(d.get("cost", 0)), float(d.get("value", 0)))
        self.send_response(204); self.end_headers()

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=8787)
    p.add_argument("--no-sim", action="store_true", help="tắt giả lập, chỉ nhận sự kiện qua POST /api/event")
    p.add_argument("--scenario", choices=["crash", "comeback", "random"], default="crash")
    p.add_argument("--speed", type=float, default=1.0)
    a = p.parse_args()
    if not a.no_sim: threading.Thread(target=simulate, args=(a.speed, a.scenario), daemon=True).start()
    print(f"agent-tu-nuoi đang chạy: http://localhost:{a.port}  (giả lập: {'tắt' if a.no_sim else a.scenario})")
    ThreadingHTTPServer(("", a.port), H).serve_forever()
