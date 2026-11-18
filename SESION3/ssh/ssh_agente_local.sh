#!/bin/bash
# Ejercicios 4-7 con OpenSSH (equivalente en Linux/WSL a PuTTYgen/PuTTY/Pageant).
#
# Concepto: autenticación con clave pública.
#   - Se genera un PAR de claves: la privada se queda en el cliente (protegida
#     con una frase de paso) y la pública se copia al servidor, a
#     ~/.ssh/authorized_keys. Al conectar, el cliente demuestra que tiene la
#     privada sin enviarla nunca; ninguna contraseña viaja por la red.
#   - El agente (ssh-agent, como Pageant) guarda la privada ya descifrada en
#     memoria: la frase de paso se teclea una vez y no en cada conexión.
#
# Pasos:
#   1. ssh-keygen  -> par de claves ed25519 con frase de paso   (= PuTTYgen)
#   2. ssh-copy-id -> añade la pública a authorized_keys del servidor
#   3. ssh-agent + ssh-add -> carga la privada en el agente     (= Pageant)
#
# Uso: ssh/ssh_agente_local.sh [usuario@maquina]   (por defecto usuario@localhost)
DESTINO="${1:-$USER@localhost}"
CLAVE=~/.ssh/id_ed25519_is

# 1. Generar el par solo si no existe (-t tipo, -f fichero, -C comentario)
[ -f "$CLAVE" ] || ssh-keygen -t ed25519 -f "$CLAVE" -C "practica-IS"   # pide passphrase
# 2. Instalar la pública en el servidor (pide la contraseña de la cuenta una vez)
ssh-copy-id -i "$CLAVE.pub" "$DESTINO"

# 3. Arrancar un agente: "ssh-agent -s" imprime órdenes "export SSH_AUTH_SOCK=..."
#    y eval las ejecuta en este shell, para que ssh/ssh-add sepan dónde está
eval "$(ssh-agent -s)"
ssh-add "$CLAVE"                      # pide la passphrase una sola vez
ssh -i "$CLAVE" "$DESTINO" 'echo "Entrada con clave pública OK en $(hostname)"'

# Limpieza: vaciar el agente y pararlo
ssh-add -D                            # equivale a cerrar Pageant
kill "$SSH_AGENT_PID"
