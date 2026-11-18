"""Ejercicio 17 (opcional): listado FTP con MLSD (formato normalizado).

Qué hace: muestra tipo, tamaño y nombre de cada entrada de la carpeta.

Concepto: MLSD (RFC 3659) devuelve cada entrada como (nombre, {hechos}), con
claves fijas como type, size o modify, en vez del texto libre de LIST. Así
no hay que "adivinar" columnas. `type` puede ser:
  file (fichero), dir (carpeta), cdir (la propia carpeta, ".") o pdir (la
  carpeta padre, ".."). Las dos últimas son pseudo-entradas y se descartan.

Ejecución:
    IS_USER=alumno python3 ftp/ftp-ej2.py [carpeta]
"""
import ftplib
import sys

import os

# comun.py está en la carpeta padre (la de la sesión)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from comun import HOST, USUARIO, obtener_clave

carpeta = sys.argv[1] if len(sys.argv) > 1 else "."

# --- Conexión, login y cambio de directorio
f = ftplib.FTP(HOST)
f.login(USUARIO, obtener_clave())
f.cwd(carpeta)

# --- Listado estructurado (las carpetas no tienen "size": se muestra "-")
for nombre, hechos in f.mlsd():
    if hechos["type"] in ("cdir", "pdir"):
        continue
    print(f"{hechos['type']:5} {hechos.get('size', '-'):>10}  {nombre}")
f.quit()
