import socket

import os
import sys

# comun.py está en la carpeta padre (la de la sesión)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from comun import HOST

# Valores de las órdenes Telnet (RFC 854)
IAC, DONT, DO, WONT, WILL = 255, 254, 253, 252, 251

# --- Conexión y lectura: lo primero que manda el servidor es la negociación
s = socket.socket()
s.connect((HOST, 23))
respuesta = s.recv(1024)
s.close()

print("Bytes recibidos:", respuesta)
print("En hexadecimal :", respuesta.hex(" "))

# --- Decodificación: se recorren las órdenes "IAC <orden> <opción>" (grupos
#     de 3 bytes) mientras el byte actual sea IAC
nombres = {DO: "DO", DONT: "DONT", WILL: "WILL", WONT: "WONT"}
i = 0
while i + 2 < len(respuesta) and respuesta[i] == IAC:
    print(f"  IAC {nombres.get(respuesta[i+1], respuesta[i+1])} opción {respuesta[i+2]}")
    i += 3
