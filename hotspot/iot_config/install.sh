#!/bin/bash

echo "Iniciando a instalação e configuração do ambiente IoT..."


# Desativa o gerenciador de rede padrão do DietPi para liberar o Wi-Fi
if [ -f /etc/network/interfaces ]; then
    echo "Desativando o ifupdown..."
    mv /etc/network/interfaces /etc/network/interfaces.bak
fi

# 1. Instala as dependências, adicionando o dnsmasq-base
apt-get update
apt-get install -y python3-flask network-manager dnsmasq-base

# 2. Configura o Redirecionamento DNS (Portal Cativo)
# Cria o diretório de configs compartilhadas do NetworkManager caso não exista
mkdir -p /etc/NetworkManager/dnsmasq-shared.d/
# Copia a nossa regra que aponta tudo para 10.42.0.1
cp /opt/iot_config/dns/captive.conf /etc/NetworkManager/dnsmasq-shared.d/
# Reinicia o NetworkManager para ele ler a nova regra
systemctl restart NetworkManager

# 3. Move o serviço para a pasta do sistema e recarrega os daemons
cp /opt/iot_config/iot-config.service /etc/systemd/system/
systemctl daemon-reload

# 4. Ativa o serviço para iniciar com o sistema e inicia agora
systemctl enable iot-config.service
systemctl restart iot-config.service

echo "Instalação concluída! O portal cativo está rodando."