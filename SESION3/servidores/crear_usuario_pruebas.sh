#!/bin/bash
# Crea el usuario de pruebas "isprueba" para probar_sesion3.sh.
#
# Por qué un usuario aparte: las pruebas entran por Telnet/SSH/FTP con
# contraseña, lanzan procesos y suben ficheros. Hacerlo con una cuenta
# temporal evita tocar la tuya, y servidores/borrar_usuario_pruebas.sh la
# elimina entera al terminar.
#
# Qué deja preparado:
#   - Contraseña aleatoria, guardada en ../.clave_pruebas (solo legible por
#     ti e ignorada por git).
#   - En su home: udp_servidor3_con_ok.py (ejercicio 2 de Telnet) y datos/ con
#     tres ficheros y una subcarpeta (ejercicio 13 de SFTP y los de FTP).
#
# Uso:  servidores/crear_usuario_pruebas.sh     (requiere sudo)
set -e   # parar en el primer error
DIR="$(cd "$(dirname "$0")/.." && pwd)"
U=isprueba
# useradd -m: crear el home; -s: shell de entrada (bash, para Telnet/SSH)
id "$U" >/dev/null 2>&1 || sudo useradd -m -s /bin/bash "$U"
# 14 caracteres alfanuméricos sacados de bytes aleatorios
CLAVE="$(head -c 12 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 14)"
# chpasswd lee "usuario:clave" de la entrada estándar (no queda en la línea de órdenes)
echo "$U:$CLAVE" | sudo chpasswd
# umask 077 en un subshell: el fichero se crea ya con permisos 600
( umask 077; echo "$CLAVE" > "$DIR/.clave_pruebas" )

# Ficheros del home. "sudo -u $U" los crea como ese usuario (con su dueño)
sudo cp "$DIR/telnet/udp_servidor3_con_ok.py" /home/$U/
sudo -u $U mkdir -p /home/$U/datos/subcarpeta
for n in uno dos tres; do echo "contenido de $n" | sudo -u $U tee /home/$U/datos/$n.txt >/dev/null; done
sudo chown $U:$U /home/$U/udp_servidor3_con_ok.py
echo "Usuario $U creado. Contraseña en $DIR/.clave_pruebas"
