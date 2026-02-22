#!/usr/bin/env python3
"""
Wishlist API server (HTTP) per sincronizzare dashboard <-> database SQLite.

Avvio:
    python scripts/wishlist_api_server.py --db data/current/games.db --host 127.0.0.1 --port 8787
"""

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

# Import DatabaseManager dal modulo scraper
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scraper"))
from database_manager import DatabaseManager


class WishlistAPIHandler(BaseHTTPRequestHandler):
    db = None

    def _send_json(self, status: int, payload: dict):
        body = b""
        if status != 204:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()

        if body:
            self.wfile.write(body)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return None

    def _path(self) -> str:
        return urlparse(self.path).path.rstrip("/") or "/"

    def _wishlist_item_id(self):
        path = self._path()
        parts = path.split("/")
        if len(parts) == 4 and parts[1] == "api" and parts[2] == "wishlist":
            try:
                return int(parts[3])
            except ValueError:
                return None
        return None

    def do_OPTIONS(self):
        self._send_json(204, {})

    def do_GET(self):
        path = self._path()
        if path == "/api/health":
            return self._send_json(200, {"ok": True})

        if path == "/api/wishlist/ids":
            return self._send_json(200, {"wishlist": self.db.get_wishlist_ids()})

        if path == "/api/wishlist":
            items = self.db.get_wishlist()
            return self._send_json(200, {
                "items": items,
                "wishlist": [int(item["game_id"]) for item in items]
            })

        return self._send_json(404, {"error": "Not found"})

    def do_PUT(self):
        path = self._path()
        if path != "/api/wishlist/ids":
            return self._send_json(404, {"error": "Not found"})

        payload = self._read_json()
        if payload is None:
            return self._send_json(400, {"error": "Invalid JSON body"})

        ids = payload.get("wishlist", [])
        if not isinstance(ids, list):
            return self._send_json(400, {"error": "'wishlist' must be a list"})

        result = self.db.set_wishlist_ids(ids)
        return self._send_json(200, {
            "ok": True,
            "wishlist": self.db.get_wishlist_ids(),
            **result
        })

    def do_POST(self):
        game_id = self._wishlist_item_id()
        if game_id is None:
            return self._send_json(404, {"error": "Not found"})

        payload = self._read_json()
        if payload is None:
            return self._send_json(400, {"error": "Invalid JSON body"})

        target_price = payload.get("target_price")
        notes = payload.get("notes")
        ok = self.db.add_to_wishlist(game_id, target_price=target_price, notes=notes)
        if not ok:
            return self._send_json(409, {"ok": False, "error": "Game already in wishlist"})

        return self._send_json(200, {"ok": True, "wishlist": self.db.get_wishlist_ids()})

    def do_DELETE(self):
        game_id = self._wishlist_item_id()
        if game_id is None:
            return self._send_json(404, {"error": "Not found"})

        removed = self.db.remove_from_wishlist(game_id)
        return self._send_json(200, {
            "ok": True,
            "removed": bool(removed),
            "wishlist": self.db.get_wishlist_ids()
        })


def parse_args():
    parser = argparse.ArgumentParser(description="Wishlist API server")
    parser.add_argument(
        "--db",
        default="data/current/games.db",
        help="Percorso database SQLite (default: data/current/games.db)"
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8787, help="Port bind (default: 8787)")
    return parser.parse_args()


def main():
    args = parse_args()
    db = DatabaseManager(args.db)
    db.init_database()

    handler_cls = type("BoundWishlistAPIHandler", (WishlistAPIHandler,), {})
    handler_cls.db = db

    server = ThreadingHTTPServer((args.host, args.port), handler_cls)
    base = f"http://{args.host}:{args.port}"

    print("=" * 60)
    print("🚀 Wishlist API Server")
    print(f"📂 DB: {Path(args.db).resolve()}")
    print(f"🌐 Base URL: {base}")
    print(f"🩺 Health:   {base}/api/health")
    print(f"⭐ Wishlist: {base}/api/wishlist/ids")
    print("=" * 60)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n⏹️  Arresto server...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
