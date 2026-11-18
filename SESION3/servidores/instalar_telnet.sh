#!/bin/bash
# Apartado 2.1.1: instala y activa el servidor Telnet (INSEGURO: texto claro).

set -e   # parar en el primer error
sudo apt-get install -y telnetd openbsd-inetd

# Línea del superservidor inetd; con tcpd (wrappers) si está disponible
if [ -x /usr/sbin/tcpd ]; then
    LINEA="telnet stream tcp nowait root /usr/sbin/tcpd /usr/sbin/telnetd"
else
    LINEA="telnet stream tcp nowait root /usr/sbin/telnetd telnetd"
fi
# Añadirla solo si no hay ya una línea telnet activa (sin comentar)
grep -q "^telnet[[:space:]]" /etc/inetd.conf || echo "$LINEA" | sudo tee -a /etc/inetd.conf

# inetd solo lee inetd.conf al arrancar: hay que reiniciarlo
sudo systemctl enable inetd
sudo systemctl restart inetd
sleep 1
ss -ltn | grep -q ':23 ' && echo "Telnet escuchando en el puerto 23" || { echo "ERROR: nada escucha en el puerto 23"; exit 1; }
