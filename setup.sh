#!/bin/bash
# Interrompe o script se ocorrer algum erro
set -e 

echo "=== Iniciando configuração do Raspberry Pi ==="

# Define as variáveis do seu repositório (Altere para o seu usuário/repo)
GITHUB_REPO="https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git"

echo "--- 1. Baixando e instalando o Hotspot ---"
# Cria um diretório temporário para clonar o repositório
TMP_DIR=$(mktemp -d)
git clone $GITHUB_REPO $TMP_DIR

# Cria a pasta de destino e copia os arquivos
sudo mkdir -p /opt/iot_config
sudo cp -r $TMP_DIR/hotspot/* /opt/iot_config/

# Executa os comandos do hotspot
sudo chmod +x /opt/iot_config/install.sh
sudo /opt/iot_config/install.sh

# Limpa os arquivos temporários baixados
rm -rf $TMP_DIR

echo "--- 2. Instalando Tailscale ---"
curl -fsSL https://tailscale.com/install.sh | sh

echo "--- 3. Habilitando VNC (WayVNC) ---"
# Utiliza a ferramenta raspi-config em modo não-interativo para habilitar o VNC. 
# O número 0 significa "Enable" (Habilitar).
sudo raspi-config nonint do_vnc 0

echo "=== Instalação finalizada com sucesso! ==="
# Opcional: Reiniciar a placa para garantir que todos os serviços subam corretamente
# sudo reboot
