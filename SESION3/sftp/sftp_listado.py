# Ejercicio 12: lista un directorio del usuario remoto con SFTP (paramiko).

import sys

import paramiko

import os

# comun.py está en la carpeta padre (la de la sesión)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from comun import HOST, USUARIO, obtener_clave

carpeta = sys.argv[1] if len(sys.argv) > 1 else "."

# --- Conexión SSH. load_system_host_keys usa ~/.ssh/known_hosts: si el host
#     ya está ahí, se verifica su clave; si no, WarningPolicy avisa y sigue
client = paramiko.SSHClient()
client.load_system_host_keys()                       # usa ~/.ssh/known_hosts
client.set_missing_host_key_policy(paramiko.WarningPolicy())
client.connect(HOST, username=USUARIO, password=obtener_clave())

# --- Canal SFTP sobre esa conexión y listado
sftp = client.open_sftp()
for nombre in sorted(sftp.listdir(carpeta)):
    print(nombre)

# --- Cierre: primero el canal SFTP y después la conexión SSH
sftp.close()
client.close()
