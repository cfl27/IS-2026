#!/bin/bash
# Elimina el usuario de pruebas "isprueba", su home y sus procesos.
#
# Por qué primero pkill: userdel se niega a borrar un usuario con procesos
# en marcha (p. ej. el servidor UDP que lanza telnet2_lanza_servidor.py).
#
# Uso:  servidores/borrar_usuario_pruebas.sh    (probar_sesion3.sh lo llama al salir)
DIR="$(cd "$(dirname "$0")/.." && pwd)"
# pkill -u: termina todos los procesos de ese usuario
sudo pkill -u isprueba 2>/dev/null
sleep 1
# userdel -r: borra también el home y el buzón de correo
sudo userdel -r isprueba 2>/dev/null
rm -f "$DIR/.clave_pruebas"
echo "Usuario isprueba eliminado"
