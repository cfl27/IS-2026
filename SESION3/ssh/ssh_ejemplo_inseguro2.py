# Ejercicio 9: WarningPolicy, que acepta la clave del host pero avisa.

import paramiko

import os
import sys

# comun.py está en la carpeta padre (la de la sesión)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from comun import HOST, USUARIO, obtener_clave

# --- Conexión: acepta el host desconocido, pero lo avisa
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.WarningPolicy())
client.connect(HOST, username=USUARIO, password=obtener_clave())
print("Conectado!! (fíjate en el aviso 'Unknown ssh-ed25519 host key' de arriba)")

# --- Ejecución remota
stdin, stdout, stderr = client.exec_command("ls")
for line in stdout:
    print(line.rstrip())
client.close()
