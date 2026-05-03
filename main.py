import requests
import json
import os
import psutil
import tiktoken
from datetime import datetime

MODELO = "granite4.1:8b"
URL_OLLAMA = "http://localhost:11434/api/generate"

def obter_contexto_otimizado(limite_ram=0.7):
    """Calcula o tamanho ideal do contexto (num_ctx) baseado na RAM disponível."""
    try:
        memoria = psutil.virtual_memory()
        ram_disponivel_gb = memoria.available / (1024**3)
        ram_permitida_gb = ram_disponivel_gb * limite_ram

        # Estimativa de uso de RAM por modelo
        modelo_nome = MODELO.lower()
        if "phi" in modelo_nome:
            peso_modelo_gb = 2.5
        elif "3b" in modelo_nome:
            peso_modelo_gb = 4.0
        elif "7b" in modelo_nome:
            peso_modelo_gb = 8.0
        elif "20b" in modelo_nome:
            peso_modelo_gb = 14.0
        else:
            peso_modelo_gb = 6.0

        if ram_permitida_gb <= peso_modelo_gb:
            return 2048

        ram_para_kv_gb = ram_permitida_gb - peso_modelo_gb
        tokens_por_gb = 2048 # Estimativa conservadora
        num_ctx = int(ram_para_kv_gb * tokens_por_gb)

        return max(2048, min(num_ctx, 131072))
    except Exception as e:
        print(f"Erro ao calcular contexto via RAM: {e}. Usando 4096.")
        return 4096

def contar_tokens(texto):
    """Conta tokens usando tiktoken ou fallback simples."""
    try:
        codificador = tiktoken.get_encoding("cl100k_base")
        return len(codificador.encode(texto))
    except:
        return max(1, len(texto) // 4)

def consultar_modelo(prompt, contexto):
    """Envia uma requisição para a API do Ollama."""
    payload = {
        "model": MODELO,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0,
            "seed": 42,
            "num_ctx": contexto
        }
    }

    try:
        resposta = requests.post(URL_OLLAMA, json=payload, timeout=100000000)
        resposta.raise_for_status()
        dados = resposta.json()
        return dados.get("response", "")
    except Exception as e:
        print(f"Erro na consulta ao Ollama: {e}")
        return None

def limpar_markdown(texto):
    """Extrai o conteúdo de dentro de blocos de código Markdown, se existirem."""
    if not texto: return ""
    if "```" not in texto: return texto.strip()
    
    blocos = texto.split("```")
    # O conteúdo real geralmente está no segundo bloco (índice 1) ou alternados
    para_processar = ""
    for i, bloco in enumerate(blocos):
        if i % 2 != 0: # É um conteúdo dentro de ```
            linhas = bloco.split("\n")
            if len(linhas) > 1 and linhas[0].strip().lower() in ["html", "json", "python", "bash", "md", "markdown", "css", "xml"]:
                para_processar += "\n".join(linhas[1:])
            else:
                para_processar += bloco
    
    return para_processar.strip() if para_processar else texto.strip()

def carregar_arquivo(caminho):
    """Lê um arquivo se ele existir."""
    if os.path.exists(caminho):
        with open(caminho, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return None

def salvar_em_html(caminho_saida, conteudo, caminho_template):
    """Insere o conteúdo no template e salva o arquivo final."""
    data_hora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    if os.path.exists(caminho_template):
        with open(caminho_template, 'r', encoding='utf-8') as f:
            template = f.read()
        html_final = template.replace("{{TIMESTAMP}}", data_hora).replace("{{CONTENT}}", conteudo)
    else:
        html_final = f"<html><body><h1>Relatório {data_hora}</h1>{conteudo}</body></html>"

    os.makedirs(os.path.dirname(caminho_saida), exist_ok=True)
    with open(caminho_saida, 'w', encoding='utf-8') as f:
        f.write(html_final)

def main():
    base = os.path.dirname(os.path.abspath(__file__))
    
    path_input = os.path.join(base, "input")
    path_output = os.path.join(base, "output")
    path_templates = os.path.join(base, "templates")
    arquivo_prompt = os.path.join(path_input, "prompt.txt")
    arquivo_formato = os.path.join(path_input, "formato_da_saida.txt")
    arquivo_revisao = os.path.join(path_input, "prompt_revisao.txt")
    arquivo_template = os.path.join(path_templates, "template.html")
    arquivo_saida = os.path.join(path_output, "resposta.html")
    corpo_prompt = carregar_arquivo(arquivo_prompt)
    formato = carregar_arquivo(arquivo_formato) or "Texto estruturado para HTML."
    prompt_revisao = carregar_arquivo(arquivo_revisao)

    if not corpo_prompt:
        print(f"Erro: Arquivo de prompt não encontrado ou vazio: {arquivo_prompt}")
        return


    prompt_geracao = f"Tarefa: {corpo_prompt}\n\nFormato obrigatório: {formato}"
    
    ctx_max = obter_contexto_otimizado()
    ctx_inicial = min(ctx_max, contar_tokens(prompt_geracao) + 3000)
    
    print(f"contexto: {ctx_inicial}")
    resultado_inicial = consultar_modelo(prompt_geracao, ctx_inicial)

    if not resultado_inicial:
        print("Erro ao gerar resposta inicial.")
        return

    resultado_final = resultado_inicial
    if prompt_revisao:
        print("-> Executando revisão...")
        prompt_final_revisao = (
            f"Conteúdo Original:\n{resultado_inicial}\n\n"
            f"Instruções de Melhora:\n{prompt_revisao}\n\n"
            f"Mantenha o Formato:\n{formato}"
        )
        ctx_revisao = min(ctx_max, contar_tokens(prompt_final_revisao) + 3000)
        resultado_revisado = consultar_modelo(prompt_final_revisao, ctx_revisao)
        if resultado_revisado:
            resultado_final = resultado_revisado

    conteudo_limpo = resultado_final
    salvar_em_html(arquivo_saida, conteudo_limpo, arquivo_template)
    
    print(f"Sucesso! Resultado em: {arquivo_saida}")

if __name__ == "__main__":
    main()
