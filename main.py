import os
import threading
import socket
import webview
import sys
import logging
from flask import Flask, render_template_string, request, send_from_directory, jsonify, redirect, url_for
from werkzeug.utils import secure_filename
from datetime import datetime

# --- Configurações ---
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'arquivos_recebidos')
PUBLIC_FOLDER = os.path.join(os.getcwd(), 'arquivos_publicos')
ALLOWED_EXTENSIONS = None # Aceita tudo

# Criar pastas se não existirem
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PUBLIC_FOLDER, exist_ok=True)

# Configuração do Flask
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PUBLIC_FOLDER'] = PUBLIC_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 * 1024  # Limite de 16GB por arquivo

# Silenciar logs do Flask no terminal para manter clean
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

def get_local_ip():
    """Descobre o IP local da máquina para compartilhamento na rede."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Tenta conectar a um DNS público (não envia dados)
        s.connect(('8.8.8.8', 80))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

LOCAL_IP = get_local_ip()
PORT = 5000
BASE_URL = f"http://{LOCAL_IP}:{PORT}"

# --- Templates HTML (Estilo Google Material Design 3) ---

BASE_LAYOUT = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SwiftSend</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0" />
    <link rel="icon" href="icon.png" type="image/png">
    <style>
        body { font-family: 'Roboto', sans-serif; background-color: #F8F9FA; color: #1F1F1F; }
        .google-card { background: white; border-radius: 24px; box-shadow: 0 1px 2px 0 rgba(60,64,67,0.3), 0 1px 3px 1px rgba(60,64,67,0.15); transition: box-shadow 0.2s; }
        .google-card:hover { box-shadow: 0 1px 3px 0 rgba(60,64,67,0.3), 0 4px 8px 3px rgba(60,64,67,0.15); }
        .btn-primary { background-color: #0B57D0; color: white; border-radius: 9999px; padding: 10px 24px; font-weight: 500; transition: all 0.2s; }
        .btn-primary:hover { background-color: #0842A0; box-shadow: 0 1px 2px rgba(0,0,0,0.3); }
        .btn-tonal { background-color: #D3E3FD; color: #041E49; border-radius: 16px; padding: 10px 20px; font-weight: 500; transition: background 0.2s; }
        .btn-tonal:hover { background-color: #C2D7FC; }
        .nav-link { color: #444746; border-radius: 9999px; padding: 8px 16px; font-weight: 500; transition: background 0.2s; }
        .nav-link:hover { background-color: #E8EAED; }
        .nav-link.active { background-color: #C2E7FF; color: #001D35; }
        /* Scrollbar customizada */
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #DADCE0; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #BDC1C6; }
    </style>
</head>
<body class="flex flex-col h-screen">
    <!-- Header Simples -->
    <header class="flex items-center justify-between px-6 py-4 bg-white border-b border-gray-200">
        <div class="flex items-center gap-2 text-[#0B57D0]">
            <span class="material-symbols-outlined text-3xl">cloud_sync</span>
            <h1 class="text-xl font-medium tracking-tight">SwiftSend</h1>
        </div>
        {% if is_desktop %}
        <div class="bg-blue-50 text-blue-700 px-4 py-2 rounded-full text-sm font-medium flex items-center gap-2">
            <span class="material-symbols-outlined text-lg">wifi</span>
            {{ base_url }}
        </div>
        {% endif %}
    </header>

    <!-- Conteúdo Principal -->
    <main class="flex-1 overflow-auto p-4 md:p-8">
        <div class="max-w-5xl mx-auto">
            {% block content %}{% endblock %}
        </div>
    </main>
</body>
</html>
"""

DASHBOARD_TEMPLATE = BASE_LAYOUT.replace("{% block content %}{% endblock %}", """
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- Cartão de Status -->
        <div class="google-card p-6 flex flex-col justify-between h-64">
            <div>
                <h2 class="text-2xl font-normal mb-2">Servidor Ativo</h2>
                <p class="text-gray-500 mb-6">Seus arquivos estão acessíveis na rede local.</p>
                <div class="bg-gray-100 p-4 rounded-xl flex items-center justify-between">
                    <code class="text-lg text-gray-700 select-all">{{ base_url }}</code>
                    <button onclick="navigator.clipboard.writeText('{{ base_url }}')" class="text-blue-600 hover:bg-blue-100 p-2 rounded-full transition">
                        <span class="material-symbols-outlined">content_copy</span>
                    </button>
                </div>
            </div>
            <div class="flex gap-2 mt-4">
                <a href="/upload_manager" class="btn-tonal flex-1 text-center flex items-center justify-center gap-2">
                    <span class="material-symbols-outlined">folder_open</span> Abrir Pasta Recebidos
                </a>
                <a href="/public_manager" class="btn-tonal flex-1 text-center flex items-center justify-center gap-2">
                     <span class="material-symbols-outlined">public</span> Gerenciar Públicos
                </a>
            </div>
        </div>

        <!-- Estatísticas Rápidas -->
        <div class="google-card p-6 flex flex-col justify-center items-center h-64 text-center">
             <div class="w-16 h-16 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center mb-4">
                <span class="material-symbols-outlined text-3xl">download</span>
            </div>
            <h3 class="text-4xl font-normal text-gray-800">{{ received_count }}</h3>
            <p class="text-gray-500">Arquivos Recebidos</p>
            <p class="text-sm text-gray-400 mt-2">Salvo em: {{ upload_path }}</p>
        </div>
    </div>

    <!-- Instruções -->
    <div class="mt-8">
        <h3 class="text-lg font-medium mb-4 ml-1">Como usar</h3>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div class="p-4 rounded-2xl bg-white border border-gray-100">
                <div class="text-blue-600 font-bold mb-1">Passo 1</div>
                <p class="text-gray-600 text-sm">Copie o endereço IP acima.</p>
            </div>
            <div class="p-4 rounded-2xl bg-white border border-gray-100">
                <div class="text-blue-600 font-bold mb-1">Passo 2</div>
                <p class="text-gray-600 text-sm">Envie para quem estiver na mesma rede Wi-Fi.</p>
            </div>
            <div class="p-4 rounded-2xl bg-white border border-gray-100">
                <div class="text-blue-600 font-bold mb-1">Passo 3</div>
                <p class="text-gray-600 text-sm">Eles podem baixar seus arquivos públicos ou enviar arquivos para você.</p>
            </div>
        </div>
    </div>
""")

PUBLIC_HOME_TEMPLATE = BASE_LAYOUT.replace("{% block content %}{% endblock %}", """
    <div class="text-center mb-10">
        <h2 class="text-3xl font-normal text-gray-800">Compartilhamento Local</h2>
        <p class="text-gray-500 mt-2">Escolha uma ação abaixo</p>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-3xl mx-auto">
        <!-- Card Baixar -->
        <a href="/browse" class="google-card p-8 flex flex-col items-center text-center group cursor-pointer no-underline">
            <div class="w-20 h-20 bg-green-50 text-green-600 rounded-full flex items-center justify-center mb-6 group-hover:bg-green-100 transition">
                <span class="material-symbols-outlined text-4xl">cloud_download</span>
            </div>
            <h3 class="text-xl font-medium text-gray-800">Baixar Arquivos</h3>
            <p class="text-gray-500 mt-2 text-sm">Acesse arquivos disponibilizados pelo host.</p>
        </a>

        <!-- Card Enviar -->
        <a href="/upload" class="google-card p-8 flex flex-col items-center text-center group cursor-pointer no-underline">
            <div class="w-20 h-20 bg-blue-50 text-blue-600 rounded-full flex items-center justify-center mb-6 group-hover:bg-blue-100 transition">
                <span class="material-symbols-outlined text-4xl">cloud_upload</span>
            </div>
            <h3 class="text-xl font-medium text-gray-800">Enviar Arquivos</h3>
            <p class="text-gray-500 mt-2 text-sm">Envie arquivos pesados para o host.</p>
        </a>
    </div>
""")

BROWSE_TEMPLATE = BASE_LAYOUT.replace("{% block content %}{% endblock %}", """
    <div class="flex items-center justify-between mb-6">
        <h2 class="text-2xl font-normal">Arquivos Disponíveis</h2>
        <a href="/" class="btn-tonal text-sm">Voltar</a>
    </div>

    <div class="google-card overflow-hidden">
        <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse">
                <thead class="bg-gray-50 text-gray-600 text-xs uppercase font-medium">
                    <tr>
                        <th class="px-6 py-4">Nome do Arquivo</th>
                        <th class="px-6 py-4">Tamanho</th>
                        <th class="px-6 py-4 text-right">Ação</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-gray-100">
                    {% if files %}
                        {% for file in files %}
                        <tr class="hover:bg-gray-50 transition">
                            <td class="px-6 py-4 flex items-center gap-3">
                                <span class="material-symbols-outlined text-gray-400">description</span>
                                <span class="font-medium text-gray-700">{{ file.name }}</span>
                            </td>
                            <td class="px-6 py-4 text-gray-500 text-sm">{{ file.size }}</td>
                            <td class="px-6 py-4 text-right">
                                <a href="/download/{{ file.name }}" class="text-blue-600 hover:text-blue-800 font-medium text-sm flex items-center justify-end gap-1">
                                    Baixar <span class="material-symbols-outlined text-sm">download</span>
                                </a>
                            </td>
                        </tr>
                        {% endfor %}
                    {% else %}
                        <tr>
                            <td colspan="3" class="px-6 py-12 text-center text-gray-500">
                                <span class="material-symbols-outlined text-4xl mb-2 text-gray-300">folder_off</span><br>
                                Nenhum arquivo público disponível no momento.
                            </td>
                        </tr>
                    {% endif %}
                </tbody>
            </table>
        </div>
    </div>
""")

UPLOAD_TEMPLATE = BASE_LAYOUT.replace("{% block content %}{% endblock %}", """
    <div class="flex items-center justify-between mb-6">
        <h2 class="text-2xl font-normal">Enviar Arquivos</h2>
        <a href="/" class="btn-tonal text-sm">Voltar</a>
    </div>

    <div class="max-w-2xl mx-auto">
        <div class="google-card p-8">
            <form id="uploadForm" action="/api/upload" method="post" enctype="multipart/form-data" class="flex flex-col gap-6">
                
                <div class="border-2 border-dashed border-gray-300 rounded-xl p-10 text-center hover:bg-blue-50 hover:border-blue-300 transition cursor-pointer relative" id="dropZone">
                    <input type="file" name="file" id="fileInput" class="absolute inset-0 w-full h-full opacity-0 cursor-pointer" multiple required onchange="updateFileName()">
                    <div class="pointer-events-none">
                        <span class="material-symbols-outlined text-4xl text-blue-500 mb-2">cloud_upload</span>
                        <p class="text-gray-600 font-medium">Arraste arquivos ou clique para selecionar</p>
                        <p class="text-gray-400 text-sm mt-1">Suporta arquivos grandes</p>
                    </div>
                </div>

                <div id="fileList" class="hidden">
                    <p class="text-sm font-medium text-gray-700 mb-2">Selecionado:</p>
                    <div class="bg-gray-100 rounded-lg p-3 flex items-center gap-2">
                        <span class="material-symbols-outlined text-gray-500">attach_file</span>
                        <span id="fileNameDisplay" class="text-sm text-gray-800 truncate"></span>
                    </div>
                </div>

                <!-- Progress Bar -->
                <div id="progressContainer" class="hidden w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-200 mt-2">
                    <div id="progressBar" class="bg-blue-600 h-2.5 rounded-full" style="width: 0%"></div>
                </div>
                <p id="statusText" class="text-center text-sm text-gray-500 hidden"></p>

                <button type="submit" id="submitBtn" class="btn-primary w-full flex justify-center items-center gap-2">
                    <span class="material-symbols-outlined">send</span> Enviar Agora
                </button>
            </form>
        </div>
    </div>

    <script>
        const fileInput = document.getElementById('fileInput');
        const fileNameDisplay = document.getElementById('fileNameDisplay');
        const fileList = document.getElementById('fileList');
        const form = document.getElementById('uploadForm');
        const progressBar = document.getElementById('progressBar');
        const progressContainer = document.getElementById('progressContainer');
        const statusText = document.getElementById('statusText');
        const submitBtn = document.getElementById('submitBtn');

        function updateFileName() {
            if(fileInput.files.length > 0) {
                fileList.classList.remove('hidden');
                if(fileInput.files.length === 1) {
                    fileNameDisplay.textContent = fileInput.files[0].name;
                } else {
                    fileNameDisplay.textContent = fileInput.files.length + " arquivos selecionados";
                }
            }
        }

        form.onsubmit = function(event) {
            event.preventDefault();
            
            const formData = new FormData(form);
            const xhr = new XMLHttpRequest();
            
            progressContainer.classList.remove('hidden');
            statusText.classList.remove('hidden');
            statusText.textContent = "Iniciando upload...";
            submitBtn.disabled = true;
            submitBtn.classList.add('opacity-50', 'cursor-not-allowed');

            xhr.upload.onprogress = function(e) {
                if (e.lengthComputable) {
                    const percentComplete = (e.loaded / e.total) * 100;
                    progressBar.style.width = percentComplete + '%';
                    statusText.textContent = Math.round(percentComplete) + '% enviado';
                }
            };

            xhr.onload = function() {
                if (xhr.status == 200) {
                    statusText.textContent = "Envio concluído com sucesso!";
                    statusText.classList.add('text-green-600');
                    setTimeout(() => window.location.reload(), 2000);
                } else {
                    statusText.textContent = "Erro ao enviar.";
                    statusText.classList.add('text-red-600');
                    submitBtn.disabled = false;
                    submitBtn.classList.remove('opacity-50', 'cursor-not-allowed');
                }
            };

            xhr.open('POST', '/api/upload', true);
            xhr.send(formData);
        };
    </script>
""")

# --- Utils ---
def get_file_size(filepath):
    """Retorna tamanho do arquivo legível"""
    size = os.path.getsize(filepath)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024

# --- Rotas do Flask ---

@app.route('/')
def index():
    # Rota "mágica": Se for acessado via localhost (app desktop), mostra dashboard.
    # Se for via IP (externo), mostra a home pública.
    host_header = request.headers.get('Host')
    
    if 'localhost' in host_header or '127.0.0.1' in host_header:
        files_received = len(os.listdir(app.config['UPLOAD_FOLDER']))
        return render_template_string(
            DASHBOARD_TEMPLATE, 
            base_url=BASE_URL, 
            received_count=files_received,
            upload_path=app.config['UPLOAD_FOLDER'],
            is_desktop=True
        )
    else:
        return render_template_string(PUBLIC_HOME_TEMPLATE, is_desktop=False)

@app.route('/upload_manager')
def open_upload_folder():
    """Abre a pasta de uploads no explorador de arquivos do SO"""
    if sys.platform == 'win32':
        os.startfile(UPLOAD_FOLDER)
    elif sys.platform == 'darwin':
        os.system(f'open "{UPLOAD_FOLDER}"')
    else:
        os.system(f'xdg-open "{UPLOAD_FOLDER}"')
    return redirect(url_for('index'))

@app.route('/public_manager')
def open_public_folder():
    """Abre a pasta pública no explorador de arquivos do SO"""
    if sys.platform == 'win32':
        os.startfile(PUBLIC_FOLDER)
    elif sys.platform == 'darwin':
        os.system(f'open "{PUBLIC_FOLDER}"')
    else:
        os.system(f'xdg-open "{PUBLIC_FOLDER}"')
    return redirect(url_for('index'))

@app.route('/browse')
def browse():
    """Lista arquivos da pasta pública"""
    files_data = []
    try:
        files = os.listdir(app.config['PUBLIC_FOLDER'])
        for f in files:
            fp = os.path.join(app.config['PUBLIC_FOLDER'], f)
            if os.path.isfile(fp):
                files_data.append({'name': f, 'size': get_file_size(fp)})
    except Exception as e:
        print(e)
        
    return render_template_string(BROWSE_TEMPLATE, files=files_data, is_desktop=False)

@app.route('/upload')
def upload_page():
    """Página de upload para visitantes"""
    return render_template_string(UPLOAD_TEMPLATE, is_desktop=False)

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    files = request.files.getlist('file')
    
    for file in files:
        if file.filename == '':
            continue
        filename = secure_filename(file.filename)
        # Adiciona timestamp para evitar sobrescrita
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], timestamp + filename))
        
    return jsonify({'success': True}), 200

@app.route('/download/<path:filename>')
def download_file(filename):
    return send_from_directory(app.config['PUBLIC_FOLDER'], filename, as_attachment=True)

# --- Inicialização ---

def start_server():
    """Inicia o servidor Flask em uma thread separada"""
    # host='0.0.0.0' permite acesso externo na rede local
    app.run(host='0.0.0.0', port=PORT, threaded=True)

@app.route('/icon.png')
def serve_icon():
    # Envia o arquivo icon.png que está na pasta raiz (onde o script roda)
    return send_from_directory(os.getcwd(), 'icon.png')

if __name__ == '__main__':
    # 1. Iniciar o servidor Flask em Background
    t = threading.Thread(target=start_server)
    t.daemon = True
    t.start()

    # 2. Criar a interface Desktop que aponta para o servidor local
    # Usamos o Pywebview para criar uma janela nativa limpa
    window_title = "SwiftSend - Transferência de Arquivos"
    
    print(f"--- Servidor Iniciado ---")
    print(f"IP Local: {LOCAL_IP}")
    print(f"Pasta Publica: {PUBLIC_FOLDER}")
    print(f"Pasta Recebidos: {UPLOAD_FOLDER}")

    webview.create_window(window_title, f"http://127.0.0.1:{PORT}", width=900, height=700)
    webview.start()