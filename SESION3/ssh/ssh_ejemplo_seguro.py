# Ejercicio 10: conexión SEGURA, registrando explícitamente la clave del host.

import base64
import sys

import paramiko

import os

# comun.py está en la carpeta padre (la de la sesión)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from comun import HOST, USUARIO, obtener_clave

# --- Clave esperada del host: tipo y clave (en base64) del fichero .pub
fichero = sys.argv[1] if len(sys.argv) > 1 else "/etc/ssh/ssh_host_ed25519_key.pub"
with open(fichero) as f:
    tipo, b64 = f.read().split()[:2]          # "ssh-ed25519", "AAAA..."

# --- Registro: equivale a tener la línea en ~/.ssh/known_hosts
client = paramiko.SSHClient()
key = paramiko.Ed25519Key(data=base64.b64decode(b64))
client.get_host_keys().add(HOST, tipo, key)   # <- host conocido y verificado

# --- Conexión: no hay set_missing_host_key_policy, así que rige RejectPolicy
client.connect(HOST, username=USUARIO, password=obtener_clave())
print("Conectado de forma segura!!")

stdin, stdout, stderr = client.exec_command("ls")
for line in stdout:
    print(line.rstrip())
client.close()
