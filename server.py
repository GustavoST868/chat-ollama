from http.server import HTTPServer, SimpleHTTPRequestHandler
import webbrowser
import threading
import os
import json
from datetime import datetime
import socket
from pypdf import PdfReader

HOST = "localhost"
PORT = 8081  # altere para outra porta se a 8080 estiver ocupada
DIRECTORY = os.getcwd()
CHATS_DIR = os.path.join(DIRECTORY, "chats")
CONTEXT_DIR = os.path.join(DIRECTORY, "contexto")
os.makedirs(CHATS_DIR, exist_ok=True)
os.makedirs(CONTEXT_DIR, exist_ok=True)

def extract_text_from_pdfs():
    text_content = ""
    files_processed = []
    if not os.path.exists(CONTEXT_DIR):
        return "", []
    
    for filename in os.listdir(CONTEXT_DIR):
        if filename.lower().endswith(".pdf"):
            filepath = os.path.join(CONTEXT_DIR, filename)
            try:
                reader = PdfReader(filepath)
                file_text = f"\n--- INÍCIO DO ARQUIVO: {filename} ---\n"
                for i, page in enumerate(reader.pages):
                    page_num = i + 1
                    file_text += f"\n[PÁGINA {page_num}]\n"
                    file_text += (page.extract_text() or "") + "\n"
                file_text += f"--- FIM DO ARQUIVO: {filename} ---\n"
                text_content += file_text
                files_processed.append(filename)
            except Exception as e:
                print(f"Erro ao ler {filename}: {e}")
    return text_content, files_processed

class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/get-context":
            text, files = extract_text_from_pdfs()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"context": text, "files": files}).encode())
        else:
            super().do_GET()

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
    port = PORT
    server = None
    while server is None:
        try:
            server = HTTPServer((HOST, port), Handler)
        except OSError:
            port += 1
            
    server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    print(f"✅ Servidor rodando em http://{HOST}:{port}")
    print(f"📁 Chats serão salvos em: {CHATS_DIR}")
    print(f"📂 Pasta de contexto: {CONTEXT_DIR}")
    
    # Abre o navegador na porta correta
    threading.Timer(0.5, lambda: webbrowser.open(f"http://{HOST}:{port}")).start()
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🔴 Servidor encerrado.")

if __name__ == "__main__":
    print("🟢 Pressione CTRL+C para encerrar.")
    start()
