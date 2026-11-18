"""Ejercicio 18 (opcional): descarga de UN fichero por FTP con retrbinary.

Uso:
    IS_USER=alumno python3 ftp/ftp-ej3.py <carpeta_remota> <fichero_remoto> [fichero_local]
"""
# Concepto: retrbinary("RETR nombre", callback) pide el fichero en modo
# binario (TYPE I) y llama a callback con cada bloque de bytes recibido; aquí
# el callback es destino.write, que los va escribiendo en disco. En modo
# texto (retrlines) se convertirían los finales de línea y se estropearía
# cualquier fichero que no sea texto.
# El docstring de arriba es también el mensaje de uso (sys.exit(__doc__)).
import ftplib
import sys

import os

# comun.py está en la carpeta padre (la de la sesión)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from comun import HOST, USUARIO, obtener_clave

# --- Argumentos
if len(sys.argv) < 3:
    sys.exit(__doc__)
carpeta, remoto = sys.argv[1], sys.argv[2]
local = sys.argv[3] if len(sys.argv) > 3 else remoto

# --- Conexión, login y cambio de directorio
f = ftplib.FTP(HOST)
f.login(USUARIO, obtener_clave())
f.cwd(carpeta)

# --- Descarga en binario directamente al fichero local
with open(local, "wb") as destino:          # "wb": transferencia binaria, sin alterar bytes
    f.retrbinary(f"RETR {remoto}", destino.write)
print("Descargado", remoto, "->", local)
f.quit()
