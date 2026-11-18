"""Ejercicio 16 (opcional): listado de un directorio FTP con retrlines('LIST').

Qué hace: entra en el servidor FTP, cambia a la carpeta indicada y muestra el
listado tal como lo envía el servidor (parecido a `ls -l`).

Concepto: FTP usa DOS conexiones TCP:
  - Control (puerto 21): órdenes de texto (USER, PASS, CWD, LIST...) y
    respuestas con código numérico.
  - Datos: una conexión nueva por cada listado o fichero transferido.
ftplib oculta esto: retrlines("LIST", callback) envía LIST, abre la conexión
de datos y llama a callback con cada línea recibida.
El formato de LIST no está normalizado (depende del servidor), así que
analizarlo es frágil; ftp-ej2.py usa MLSD, que sí lo está.

Seguridad: FTP envía usuario y contraseña en texto claro, como Telnet.

Ejecución (con servidores/instalar_ftp.sh):
    IS_USER=alumno python3 ftp/ftp-ej1.py [carpeta]
"""
import ftplib
import sys

import os

# comun.py está en la carpeta padre (la de la sesión)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from comun import HOST, USUARIO, obtener_clave

carpeta = sys.argv[1] if len(sys.argv) > 1 else "."
lista = []

# --- Conexión de control, login y cambio de directorio
f = ftplib.FTP(HOST)
f.login(USUARIO, obtener_clave())
f.cwd(carpeta)

# --- Listado por la conexión de datos
f.retrlines("LIST", lista.append)     # el callback recibe cada línea del listado
for linea in lista:
    print(linea)

# --- quit() envía QUIT (cierre educado) en vez de cortar la conexión
f.quit()
