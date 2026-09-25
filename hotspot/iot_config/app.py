import os
import json
import subprocess
import time
import threading
from flask import Flask, request, render_template, redirect, url_for

app = Flask(__name__)
CONFIG_FILE = "/opt/iot_config/config.json"

# Variável global para armazenar as redes encontradas ANTES do hotspot ligar
WIFI_LIST = []

def is_connected():
    try:
        # Pega o código numérico do status do wlan0 (100 significa conectado)
        estado = subprocess.check_output("nmcli -t -f GENERAL.STATE dev show wlan0", shell=True).decode()
        
        if "100" in estado:
            # Verifica o nome da rede atual para garantir que não é o nosso próprio hotspot enganando o sistema
            rede_atual = subprocess.check_output("nmcli -t -f GENERAL.CONNECTION dev show wlan0", shell=True).decode()
            if "WHR-rpi" not in rede_atual:
                return True
        return False
    except Exception as e:
        print(f"Erro na verificação de rede: {e}", flush=True)
        return False

def start_hotspot():
    print("Iniciando Hotspot...", flush=True)
    # O "2>/dev/null" esconde erros caso a placa já esteja desconectada
    os.system("nmcli dev disconnect wlan0 2>/dev/null")
    time.sleep(3)
    # Cria o hotspot com segurança
    os.system("nmcli dev wifi hotspot ifname wlan0 ssid WHR-rpi password 12345678")

def scan_and_save_networks():
    global WIFI_LIST
    print("Buscando redes antes de travar a antena no Hotspot...", flush=True)
    try:
        # Força o Raspberry a buscar redes novas ao redor com a antena livre
        os.system("nmcli dev wifi rescan")
        time.sleep(4) # Aguarda a busca terminar e o hardware escutar todos os canais
        
        # Pega a lista de SSIDs
        output = subprocess.check_output(['nmcli', '-t', '-f', 'SSID', 'dev', 'wifi']).decode('utf-8')
        networks = list(set([line.strip() for line in output.split('\n') if line.strip()]))
        
        # Remove o próprio hotspot da lista ou redes vazias
        if "WHR-rpi" in networks:
            networks.remove("WHR-rpi")
            
        WIFI_LIST = [net for net in networks if net]
        print(f"Redes encontradas: {WIFI_LIST}", flush=True)
    except Exception as e:
        print(f"Erro ao buscar redes: {e}", flush=True)

def transicao_de_rede(ssid, password):
    """Roda em segundo plano para não travar a resposta do celular"""
    time.sleep(2) 
    print(f"Criando perfil salvo para a rede: {ssid}", flush=True)
    
    # 1. Deleta a conexão se ela já existir (ignorando erros silenciosamente)
    subprocess.run(['nmcli', 'connection', 'delete', ssid], stderr=subprocess.DEVNULL)
    
    # 2. Adiciona a rede aos perfis salvos
    subprocess.run(['nmcli', 'connection', 'add', 'type', 'wifi', 'ifname', 'wlan0', 'con-name', ssid, 'ssid', ssid])
    
    # 3. Configura a senha (agora imune a caracteres especiais, espaços e aspas)
    subprocess.run(['nmcli', 'connection', 'modify', ssid, 'wifi-sec.key-mgmt', 'wpa-psk', 'wifi-sec.psk', password])
    
    # 4. Tira o hotspot do piloto automático
    subprocess.run(['nmcli', 'connection', 'modify', 'WHR-rpi', 'autoconnect', 'no'], stderr=subprocess.DEVNULL)
    
    # 5. Reinicia o NetworkManager
    print("Reiniciando o NetworkManager para ele assumir a conexao automatica...", flush=True)
    subprocess.run(['systemctl', 'restart', 'NetworkManager'])
    
    # 6. Aguarda conectar
    print("Aguardando 20 segundos para o hardware estabilizar e conectar...", flush=True)
    time.sleep(20) 
    
    if is_connected():
        print("Sucesso! O dispositivo conectou usando o perfil salvo.", flush=True)
    else:
        print("Falha ao conectar pelo perfil salvo! Voltando para o modo Hotspot...", flush=True)
        start_hotspot()


@app.route('/')
def index():
    # Busca as redes na memória e manda para a página HTML
    networks = WIFI_LIST
    return render_template('index.html', networks=networks)

@app.route('/salvar', methods=['POST'])
def salvar():
    ssid = request.form.get('ssid')
    password = request.form.get('password')
    produto_id = request.form.get('produto_id')
    intervalo = request.form.get('intervalo')

    if not produto_id or not intervalo or not ssid:
        return "Erro: ID do Produto, Intervalo e Rede são obrigatórios!", 400

    # Salva o arquivo JSON
    config_data = {
        "produto_id": produto_id,
        "intervalo_aquisicao": int(intervalo)
    }
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config_data, f)

    # Inicia a transição de rede em segundo plano (Thread)
    thread = threading.Thread(target=transicao_de_rede, args=(ssid, password))
    thread.start()

    # Retorna a mensagem para o celular imediatamente
    return "Configuração salva com sucesso! O dispositivo está conectando à internet. Você já pode fechar esta página."

@app.errorhandler(404)
def catch_all(e):
    # Rota que captura os testes de internet dos celulares (Apple/Android)
    return redirect(url_for('index'))

def wait_for_connection(timeout_seconds=60):
    """Aguarda um tempo para ver se o NetworkManager conecta em alguma rede salva no boot"""
    print(f"Aguardando até {timeout_seconds} segundos pela conexão automática...", flush=True)
    for _ in range(timeout_seconds):
        if is_connected():
            print("Conectado com sucesso a uma rede conhecida!", flush=True)
            return True
        time.sleep(1)
    
    print("Tempo esgotado. Nenhuma rede conhecida encontrada.", flush=True)
    return False

if __name__ == '__main__':
    # No momento de ligar: Espera achar uma rede salva
    if not wait_for_connection(60):
        # Se não achou, escaneia o ambiente e abre o portal cativo
        scan_and_save_networks()
        start_hotspot()
    
    # O servidor Flask roda em background (mesmo se conectou, assim a página fica acessível via IP)
    app.run(host='0.0.0.0', port=80)