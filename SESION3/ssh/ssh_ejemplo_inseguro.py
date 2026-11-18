#Ejercicio 8: AutoAddPolicy, que acepta CUALQUIER clave de host.

import paramiko

import os
import sys

# comun.py está en la carpeta padre (la de la sesión)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from comun import HOST, USUARIO, obtener_clave

# --- Conexión: la política decide qué hacer con un host desconocido
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())   # ¡inseguro!
client.connect(HOST, username=USUARIO, password=obtener_clave())
print("Conectado!!")

# --- Ejecución remota: exec_command devuelve los tres flujos estándar del
#     proceso remoto; stdout se puede recorrer línea a línea
stdin, stdout, stderr = client.exec_command("ls")
for line in stdout:
    print(line.rstrip())
client.close()
