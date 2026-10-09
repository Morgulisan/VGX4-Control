"""Loopback-only HTTP app. No hardware connection on startup."""
import argparse
import json
import logging
from logging.handlers import RotatingFileHandler
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import secrets
import webbrowser
from controller import Controller

ROOT = Path(__file__).resolve().parent

def make_handler(controller, token, port):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def reply(self, body, status=200, content_type='application/json; charset=utf-8'):
            if not isinstance(body, bytes):
                body = json.dumps(body, ensure_ascii=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' blob:; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(body)
        def trusted_host(self):
            return self.headers.get('Host') in (f'127.0.0.1:{port}', f'localhost:{port}')
        def do_GET(self):
            if not self.trusted_host():
                return self.reply({'error':'Host nicht erlaubt.'},403)
            if self.path == '/api/state':
                return self.reply({**controller.snapshot(), 'token':token})
            if self.path == '/api/ports':
                if controller.demo:
                    return self.reply({'ports':[{'port':'DEMO','description':'Simulierter Schreibroboter'}]})
                from serial.tools.list_ports import comports
                return self.reply({'ports':[{'port':p.device,'description':p.description} for p in comports()]})
            if self.path.split('?')[0] == '/api/preview':
                with controller.lock:
                    svg = controller.job['svg'] if controller.job else ''
                return self.reply(svg.encode(), content_type='image/svg+xml')
            if self.path in ('/api/download/write','/api/download/dryrun'):
                with controller.lock:
                    if not controller.job:
                        return self.reply({'error':'Kein Auftrag.'},404)
                    code = controller.job['code' if self.path.endswith('/write') else 'dry']
                return self.reply(code.encode(),content_type='text/plain; charset=utf-8')
            assets={'/':('index.html','text/html; charset=utf-8'),'/style.css':('style.css','text/css; charset=utf-8'),'/app.js':('app.js','text/javascript; charset=utf-8'),'/theme.js':('theme.js','text/javascript; charset=utf-8')}
            if self.path in assets:
                file,mime=assets[self.path]
                return self.reply((ROOT/'web'/file).read_bytes(),content_type=mime)
            self.reply({'error':'Nicht gefunden.'},404)
        def do_POST(self):
            origin=self.headers.get('Origin')
            if (not self.trusted_host() or self.headers.get('X-Control-Token') != token or
                (origin and origin not in (f'http://127.0.0.1:{port}',f'http://localhost:{port}'))):
                return self.reply({'error':'Lokaler Zugriffstoken erforderlich.'},403)
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0 < size <= 16384:
                    raise ValueError('Ungültige Anfragegröße.')
                data=json.loads(self.rfile.read(size))
                if not isinstance(data,dict):
                    raise ValueError('JSON-Objekt erwartet.')
                if self.path == '/api/prepare':
                    return self.reply(controller.prepare(data))
                if self.path.startswith('/api/action/'):
                    controller.action(self.path.removeprefix('/api/action/'),data)
                    return self.reply({'ok':True})
                self.reply({'error':'Nicht gefunden.'},404)
            except (ValueError,RuntimeError,TypeError) as exc:
                self.reply({'error':str(exc)},400)
            except Exception:
                logging.exception('HTTP error')
                self.reply({'error':'Interner Fehler; siehe logs/control.log.'},500)
    return Handler

def main():
    parser=argparse.ArgumentParser(description='VG-X4 lokale Steuerung')
    parser.add_argument('--demo',action='store_true',help='Nur Simulation, keine echten Roboter (Standard: live)')
    parser.add_argument('--no-browser',action='store_true')
    parser.add_argument('--port',type=int,default=8765)
    args=parser.parse_args()
    (ROOT/'logs').mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(message)s',
        handlers=[RotatingFileHandler(ROOT/'logs'/'control.log',maxBytes=1_000_000,backupCount=3,encoding='utf-8')])
    controller=Controller(ROOT/'jobs',demo=args.demo)
    server=ThreadingHTTPServer(('127.0.0.1',args.port),make_handler(controller,secrets.token_urlsafe(32),args.port))
    url=f'http://127.0.0.1:{args.port}'
    print(f'VG-X4 {"SIMULATION (--demo, keine echten Roboter)" if args.demo else "Steuerung"}: {url}\nBeenden mit Strg+C. Verbindung erst per Button.')
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if controller.device:
            if controller.state['busy']:
                controller.device.realtime('stop')
            controller.device.close()
        server.server_close()

if __name__ == '__main__':
    main()
