# Ejercicio 11: conexión SSH segura a la máquina de OTRO compañero.
# Concepto: igual que el ejercicio 10, pero la clave del host no se puede leer
# de un fichero local: la proporciona el usuario. Si el servidor presenta otra
# clave, paramiko (RejectPolicy) rechaza la conexión antes de enviar la
# contraseña. Este script no usa comun.py porque la IP llega como argumento.
# El docstring de arriba es también el mensaje de uso que se muestra si
# faltan argumentos (sys.exit(__doc__)).

import base64
import getpass
import os
import sys

import paramiko

# --- Argumentos: IP y línea de la clave pública ("tipo base64 [comentario]")
if len(sys.argv) != 3:
    sys.exit(__doc__)
ip, linea_clave = sys.argv[1], sys.argv[2]
tipo, b64 = linea_clave.split()[:2]

usuario = os.getenv("IS_USER") or input("Usuario remoto: ")
clave = os.getenv("IS_PASS") or getpass.getpass(f"Clave de {usuario}@{ip}: ")

# --- Conexión verificada: solo se acepta un host con esa clave exacta
client = paramiko.SSHClient()
client.get_host_keys().add(ip, tipo, paramiko.Ed25519Key(data=base64.b64decode(b64)))
client.connect(ip, username=usuario, password=clave)
print(f"Conectado de forma segura a {ip}")

# --- Ejecución remota: read() recoge toda la salida de una vez
stdin, stdout, stderr = client.exec_command("hostname; ls")
print(stdout.read().decode(), end="")
client.close()
