"""Ejercicio 19 (opcional): descarga desatendida de todos los ficheros de un directorio FTP.

Uso:
    IS_USER=alumno python3 ftp/ftp-ej4.py <carpeta_remota> [carpeta_local]
(carpeta_local por defecto: ./descargas_ftp, ignorada por git)
"""
# Concepto: combina los ejercicios 17 y 18. MLSD dice qué entradas son
# ficheros (type == "file"), sin tener que interpretar el texto de LIST, y
# cada uno se descarga con retrbinary. "Desatendida" = sin preguntar nada,
# apta para un cron o un script de copias.
# El docstring de arriba es también el mensaje de uso (sys.exit(__doc__)).
import ftplib
import os
import sys


# comun.py está en la carpeta padre (la de la sesión)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from comun import HOST, USUARIO, obtener_clave

# --- Argumentos y carpeta local de destino
if len(sys.argv) < 2:
    sys.exit(__doc__)
carpeta = sys.argv[1]
local = sys.argv[2] if len(sys.argv) > 2 else "descargas_ftp"
os.makedirs(local, exist_ok=True)

# --- Conexión, login y cambio de directorio
f = ftplib.FTP(HOST)
f.login(USUARIO, obtener_clave())
f.cwd(carpeta)

# --- Selección de ficheros (se descartan dir/cdir/pdir) y descarga de cada uno
ficheros = [n for n, h in f.mlsd() if h["type"] == "file"]
for nombre in ficheros:
    with open(os.path.join(local, nombre), "wb") as destino:
        f.retrbinary(f"RETR {nombre}", destino.write)
    print("descargado:", nombre)
print(f"{len(ficheros)} fichero(s) en '{local}'")
f.quit()
