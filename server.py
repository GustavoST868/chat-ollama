from http.server import HTTPServer, SimpleHTTPRequestHandler
import webbrowser
import threading
import os
import json
from datetime import datetime
import socket

HOST = "localhost"
PORT = 8081  # altere para outra porta se a 8080 estiver ocupada
DIRECTORY = os.getcwd()
CHATS_DIR = os.path.join(DIRECTORY, "chats")
os.makedirs(CHATS_DIR, exist_ok=True)

class Handler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/save-chat":
            length = int(self.headers['Content-Length'])
            data = json.loads(self.rfile.read(length).decode('utf-8'))
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"chat_{ts}.html"
            filepath = os.path.join(CHATS_DIR, filename)
            
            html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>Chat {ts}</title>
<style>
body {{ font-family: monospace; max-width: 900px; margin: 2rem auto; padding: 1rem; }}
.user {{ border-left: 3px solid #000; margin: 1rem 0; padding-left: 1rem; }}
.assistant {{ border-left: 3px solid #ccc; margin: 1rem 0; padding-left: 1rem; }}
</style>
</head>
<body>
<h1>Conversa salva em {ts}</h1>
<p>Modelo: {data.get('model', 'desconhecido')}</p>
"""
            for msg in data.get('history', []):
                role = msg['role']
                content = msg['content']
                css_class = "user" if role == "user" else "assistant"
                html += f'<div class="{css_class}"><strong>{role}:</strong><br>{content}</div>\n'
            html += "</body></html>"
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html)
                
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "file": filename}).encode())
        else:
            self.send_response(404)
            self.end_headers()

def start():
    server = HTTPServer((HOST, PORT), Handler)
    server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    print(f"✅ Servidor rodando em http://{HOST}:{PORT}")
    print(f"📁 Chats serão salvos em: {CHATS_DIR}")
    server.serve_forever()

if __name__ == "__main__":
    thread = threading.Thread(target=start, daemon=True)
    thread.start()
    webbrowser.open(f"http://{HOST}:{PORT}")
    print("🟢 Pressione CTRL+C para encerrar.")
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("\n🔴 Servidor encerrado.")
