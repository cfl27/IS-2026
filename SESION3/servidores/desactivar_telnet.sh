#!/bin/bash
# Tras la práctica: desactiva Telnet comentando su línea en /etc/inetd.conf.
#
# Por qué: Telnet envía usuario y contraseña en texto claro; cualquiera que
# vea el tráfico los lee. No debe quedar abierto. El paquete sigue instalado;
# para reactivarlo basta con servidores/instalar_telnet.sh.
#
# Uso:  servidores/desactivar_telnet.sh
# sed -i: edita el fichero en el sitio; pone "#" delante de la línea telnet
sudo sed -i 's/^telnet[[:space:]]/#telnet /' /etc/inetd.conf
# Reiniciar inetd para que vuelva a leer la configuración y cierre el puerto 23
sudo systemctl restart inetd
sleep 1
ss -ltn | grep -q ':23 ' && echo "AVISO: el puerto 23 sigue abierto" || echo "Telnet desactivado"
