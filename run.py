import os
import sys
import json
import logging
import urllib.parse
import http.server
import socketserver
import threading
from datetime import date, datetime

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
except ImportError:
    pass

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, 'frontend')
sys.path.insert(0, os.path.join(BASE_DIR, 'backend'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)


class CAHandler(http.server.BaseHTTPRequestHandler):

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path   = parsed.path.rstrip('/')
        query  = urllib.parse.parse_qs(parsed.query)

        if path in ('', '/index.html'):
            self._file(os.path.join(FRONTEND_DIR, 'index.html'), 'text/html; charset=utf-8')

        elif path == '/api/news':
            from database import get_articles, get_article_count
            import math
            date_f    = query.get('date',            [None])[0]
            date_from = query.get('date_from',       [None])[0]
            cat_f     = query.get('category',        [None])[0]
            search    = query.get('search',          [None])[0]
            min_c     = float(query.get('min_confidence', ['0.80'])[0])
            limit     = int(query.get('limit',  ['15'])[0])
            page      = int(query.get('page',   ['1'])[0])
            offset    = (page - 1) * limit
            articles  = get_articles(date_f, cat_f, min_c, limit, offset, date_from, search)
            total     = get_article_count(date_f, cat_f, min_c, date_from, search)
            pages     = math.ceil(total / limit) if total > 0 else 1
            self._json({'articles': articles, 'count': len(articles), 'total': total,
                        'page': page, 'pages': pages,
                        'filters': {'date': date_f, 'category': cat_f, 'min_confidence': min_c}})

        elif path == '/api/categories':
            from database import get_categories
            self._json({'categories': get_categories()})

        elif path == '/api/dates':
            from database import get_dates_with_articles
            self._json({'dates': get_dates_with_articles(30)})

        elif path == '/api/stats':
            from database import get_stats
            self._json(get_stats())

        elif path == '/api/today':
            from database import get_articles
            cat_f = query.get('category', [None])[0]
            min_c = float(query.get('min_confidence', ['0.80'])[0])
            arts  = get_articles(str(date.today()), cat_f, min_c, 100, 0)
            self._json({'date': str(date.today()), 'articles': arts, 'count': len(arts)})

        else:
            rel   = path.lstrip('/')
            fpath = os.path.join(FRONTEND_DIR, rel)
            if os.path.isfile(fpath):
                ext   = os.path.splitext(fpath)[1].lstrip('.')
                ctype = {'html': 'text/html', 'css': 'text/css', 'js': 'text/javascript',
                         'json': 'application/json', 'png': 'image/png', 'ico': 'image/x-icon'}.get(ext, 'text/plain')
                self._file(fpath, ctype)
            else:
                self.send_response(404)
                self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/api/fetch':
            self._json({'status': 'started', 'message': 'Pipeline running in background...', 'timestamp': datetime.now().isoformat()})
            def _run():
                try:
                    from pipeline import run_pipeline_once
                    run_pipeline_once(use_rss=True, use_api=False)
                except Exception as e:
                    logger.error(f"Background pipeline error: {e}")
            threading.Thread(target=_run, daemon=True).start()
        else:
            self._json({'error': 'Not found'}, 404)

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def _json(self, data, status=200):
        body = json.dumps(data, default=str, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', len(body))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path, ctype):
        try:
            with open(path, 'rb') as f:
                body = f.read()
            self.send_response(200)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', len(body))
            self.end_headers()
            self.wfile.write(body)
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin',  '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def log_message(self, fmt, *args):
        if args and '/api/' in str(args[0]):
            logger.info(f"{self.address_string()} {fmt % args}")


def startup():
    from database import init_db, get_stats
    init_db()
    stats = get_stats()
    if stats['total'] == 0:
        logger.info("Empty DB — seeding demo articles...")
        from pipeline import seed_demo_data
        seed_demo_data()
        stats = get_stats()
    logger.info(f"DB ready: {stats['total']} articles across {len(stats['by_category'])} categories")
    return stats


def main(port: int = 8000):
    logger.info("=" * 55)
    logger.info("  CA Portal — SSC & RRB Current Affairs")
    logger.info("  Database: PostgreSQL")
    logger.info("=" * 55)

    stats = startup()

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("", port), CAHandler) as httpd:
        logger.info(f"Articles in DB : {stats['total']}")
        logger.info(f"Server running → http://localhost:{port}")
        logger.info("Press Ctrl+C to stop\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            logger.info("\nShutting down.")


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description='CA Portal Server (PostgreSQL)')
    p.add_argument('--port',  type=int, default=8000)
    p.add_argument('--train', action='store_true', help='Retrain classifier before starting')
    args = p.parse_args()

    if args.train:
        logger.info("Retraining classifier...")
        from classifier import train_classifier
        acc = train_classifier()
        logger.info(f"Training complete — accuracy: {acc:.4f}")

    main(args.port)
