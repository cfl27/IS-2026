# Ejemplo mínimo con paramiko, DELIBERADAMENTE INCORRECTO (previo al ej. 8).

import time

import paramiko

import os
import sys

# comun.py está en la carpeta padre (la de la sesión)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from comun import HOST, USUARIO, obtener_clave

# --- Conexión: sin política ni claves conocidas -> RejectPolicy -> excepción
client = paramiko.SSHClient()
client.connect(HOST, username=USUARIO, password=obtener_clave())   # <- falla
print("Conectado!!")

# (No se llega aquí) ejecución remota y lectura de la salida línea a línea
stdin, stdout, stderr = client.exec_command("ls")
for line in stdout:
    print(line.rstrip())

time.sleep(1)
client.close()
