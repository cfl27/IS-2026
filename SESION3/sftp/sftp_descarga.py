# Ejercicio 13: descarga con SFTP todos los ficheros regulares de una carpeta remota.

# Concepto: listdir() solo devuelve nombres; para saber si cada uno es un
# fichero o una carpeta hay que pedir sus atributos con stat() y mirar el
# campo st_mode con S_ISDIR (igual que con os.stat en local). sftp.get() no
# sabe descargar carpetas, por eso se saltan.
# El docstring de arriba es también el mensaje de uso (sys.exit(__doc__)).
import os
import posixpath
import sys
from stat import S_ISDIR

import paramiko


# comun.py está en la carpeta padre (la de la sesión)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from comun import HOST, USUARIO, obtener_clave

# --- Argumentos y carpeta local de destino
if len(sys.argv) < 2:
    sys.exit(__doc__)
remota = sys.argv[1]
local = sys.argv[2] if len(sys.argv) > 2 else "descargas"
os.makedirs(local, exist_ok=True)

# --- Conexión SSH + canal SFTP
client = paramiko.SSHClient()
client.load_system_host_keys()
client.set_missing_host_key_policy(paramiko.WarningPolicy())
client.connect(HOST, username=USUARIO, password=obtener_clave())
sftp = client.open_sftp()

# --- Descarga de los ficheros regulares
n = 0
for nombre in sftp.listdir(remota):
    # posixpath y no os.path: la ruta es del servidor (Linux, siempre con
    # "/"), aunque este script se ejecute en Windows
    ruta = posixpath.join(remota, nombre)          # rutas remotas siempre con "/"
    if not S_ISDIR(sftp.stat(ruta).st_mode):
        sftp.get(ruta, os.path.join(local, nombre))
        print("descargado:", ruta)
        n += 1
print(f"{n} fichero(s) en '{local}'")

sftp.close()
client.close()
