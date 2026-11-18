"""Ejercicio 14 (sesión 4, apartado 3.2.1): Subject y From de TODOS los mensajes, en crudo.

Qué hace: copia del ejercicio 13 (email_pop3_recibe_crudo.py) que, tras STAT,
recorre los mensajes 1..N con RETR y muestra Subject y From de cada uno.
(Las funciones son las mismas que en el ej. 13: allí están comentadas.)

Ejecución:
    python3 correo/pop3/email_pop3_recibe_crudo2.py     (pide usuario y clave)
  o con IS_USER / IS_PASS, e IS_POP_SERVER / IS_POP_PORT para el simulador.

Concepto: STAT da el número de mensajes N; en POP3 los mensajes se numeran
de 1 a N durante TODA la sesión (aunque se marque alguno con DELE, los
demás no se renumeran: el borrado real es en el estado UPDATE, tras QUIT).
Si solo interesan las cabeceras sería mejor "TOP n 0" (cabeceras + 0
líneas de cuerpo): no descarga adjuntos de varios MB para leer un asunto.
"""
import os
import socket
import ssl
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from comun import config_servidor, error_conexion, obtener_clave, obtener_usuario


def RecvReply(sock):
    """Lee una respuesta de UNA línea, la muestra y exige que empiece por +OK."""
    respuesta = b""
    while not respuesta.endswith(b"\r\n"):
        trozo = sock.recv(1024)
        if not trozo:
            print("ERROR: el servidor cerró la conexión")
            sys.exit(1)
        respuesta += trozo
    print("S:", respuesta.decode("utf-8", "replace").rstrip())
    if respuesta[:3] != b"+OK":
        print("ERROR: el servidor respondió -ERR"
              + (" (¿usuario o contraseña incorrectos?)" if b"PASS" in ultima_orden else ""))
        sys.exit(1)
    return respuesta


def enviar(sock, orden, mostrar=None):
    global ultima_orden
    ultima_orden = orden.encode()
    print("C:", mostrar or orden)
    sock.sendall(orden.encode("utf-8") + b"\r\n")


def recibir_multilinea(sock):
    """Lee una respuesta multilínea (+OK ...\\r\\n datos \\r\\n.\\r\\n) y devuelve los datos.

    Bucle hasta ver el terminador: un mensaje ocupa muchos recv() y no se
    sabe de antemano cuántos. Luego se quitan la 1ª línea (+OK), el punto
    final y el dot-stuffing (".." al principio de línea -> ".").
    """
    datos = b""
    while not datos.endswith(b"\r\n.\r\n"):
        trozo = sock.recv(1024)
        if not trozo:
            print("ERROR: conexión cerrada a mitad de mensaje")
            sys.exit(1)
        datos += trozo
        if datos.startswith(b"-ERR"):
            print("S:", datos.decode().rstrip())
            sys.exit(1)
    estado, _, cuerpo = datos.partition(b"\r\n")
    print("S:", estado.decode(), f"[+ {len(cuerpo)} bytes hasta el punto final]")
    cuerpo = cuerpo[:-3]                                  # quita ".\r\n"
    lineas = [l[1:] if l.startswith(b"..") else l for l in cuerpo.split(b"\r\n")]
    return b"\r\n".join(lineas)


def cabecera(mensaje, nombre):
    """Valor de una cabecera buscando a mano en la parte de cabeceras.

    Las cabeceras acaban en la primera línea en blanco. Una cabecera larga
    puede estar "plegada": las líneas que empiezan por espacio o tabulador
    continúan la anterior. OJO: si lleva tildes saldrá codificada en RFC 2047
    (=?utf-8?...?=): decodificarla bien es el ejercicio 16.
    """
    cabeceras = mensaje.split(b"\r\n\r\n", 1)[0].split(b"\r\n")
    valor = None
    for linea in cabeceras:
        if valor is not None and linea[:1] in (b" ", b"\t"):
            valor += b" " + linea.strip()          # continuación (plegado)
        elif valor is not None:
            break
        elif linea.lower().startswith(nombre.lower().encode() + b":"):
            valor = linea.split(b":", 1)[1].strip()
    return valor.decode("utf-8", "replace") if valor is not None else "<no hay>"


ultima_orden = b""
server, port = config_servidor("POP", "pop.gmail.com", 995)
usuario = obtener_usuario()
clave = obtener_clave()

# --- Conexión y canal seguro desde el primer byte (SSL implícito)
try:
    s = socket.socket()
    s.settimeout(15)
    s.connect((server, port))
    context = ssl.create_default_context()
    sc = context.wrap_socket(s, server_hostname=server)
except OSError as e:
    error_conexion(e, server, port)
RecvReply(sc)                     # saludo: "+OK Gpop ready..."

# --- AUTHORIZATION
enviar(sc, f"USER {usuario}")
RecvReply(sc)
enviar(sc, f"PASS {clave}", mostrar="PASS ********")
RecvReply(sc)                     # +OK: pasamos a TRANSACTION

# --- TRANSACTION: STAT = "+OK <nº de mensajes> <bytes totales>"
enviar(sc, "STAT")
num = int(RecvReply(sc).split()[1])
if num == 0:
    print("El buzón no tiene mensajes nuevos.")
for n in range(1, num + 1):
    enviar(sc, f"RETR {n}")
    mensaje = recibir_multilinea(sc)
    print(f"\nMensaje {n}:")
    print("  Subject:", cabecera(mensaje, "Subject"))
    print("  From:   ", cabecera(mensaje, "From"))
    print()

# --- QUIT: UPDATE (no hemos marcado nada con DELE: no se borra nada)
enviar(sc, "QUIT")
RecvReply(sc)
sc.close()
