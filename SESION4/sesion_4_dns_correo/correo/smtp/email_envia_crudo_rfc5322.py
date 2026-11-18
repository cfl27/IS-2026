"""Ejercicios 8 y 9 (sesión 4, apartados 3.1.2 y 3.1.3): SMTP en crudo + mensaje RFC 5322.

Qué hace: el mismo diálogo que email_envia_crudo.py (ej. 7), pero el mensaje
ya no es una plantilla: se construye con email.message.EmailMessage, se
convierte a bytes con as_bytes() y se le añade el punto final a mano.
Con --adjunto [F] adjunta logoatc.gif (o F): ejercicio 9.
Con --tildes usa nombres, asunto y cuerpo con tildes (experimento 3.1.2).

Ejecución:
    IS_FROM=uoXXXXXX@uniovi.es IS_TO=uoXXXXXX@uniovi.es python3 correo/smtp/email_envia_crudo_rfc5322.py [--adjunto] [--tildes]
  (o contra el simulador: IS_SMTP_SERVER=localhost IS_SMTP_PORT=2525 ..., ver README)

Concepto: separar FORMATO (RFC 5322: cabeceras, MIME, codificaciones; lo
resuelve la biblioteca email) de PROTOCOLO (RFC 5321: el diálogo con el
servidor; aquí, a mano). Dos detalles del protocolo que la plantilla del
ej. 7 ignoraba y aquí sí se cumplen (ver mensajes.preparar_para_data):
finales de línea CRLF y "dot-stuffing" de las líneas que empiezan por ".".
Experimento del guion: enviarlo a Gmail y abrir "Mostrar original": cada
MTA por el que pasa añade arriba su cabecera Received: (con la IP de origen).
"""
import argparse
import os
import socket
import sys

DIR_SESION = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, DIR_SESION)
sys.path.insert(0, os.path.join(DIR_SESION, "correo", "mensajes"))
from comun import config_servidor, error_conexion, obtener_direcciones
from mensajes import bytes_para_smtp, construir_mensaje, preparar_para_data, ruta_logo


def RecvReply(sock, codigo):
    """Lee una respuesta SMTP completa y exige `codigo` (ver email_envia_crudo.py)."""
    respuesta = b""
    while True:
        trozo = sock.recv(1024)
        if not trozo:
            print("ERROR: el servidor cerró la conexión")
            sys.exit(1)
        respuesta += trozo
        if respuesta.endswith(b"\r\n"):
            ultima = respuesta.rstrip(b"\r\n").split(b"\r\n")[-1]
            if len(ultima) < 4 or ultima[3:4] == b" ":
                break
    print("S:", respuesta.decode("utf-8", "replace").rstrip().replace("\r\n", "\n   "))
    if respuesta[:3] != codigo:
        print(f"ERROR: se esperaba {codigo.decode()} y el servidor respondió "
              f"{respuesta[:3].decode()}")
        sys.exit(1)
    return respuesta


def enviar(sock, orden):
    print("C:", orden)
    sock.sendall(orden.encode("utf-8") + b"\r\n")


opciones = argparse.ArgumentParser(description="SMTP en crudo con mensaje RFC 5322")
opciones.add_argument("--adjunto", nargs="?", const="", metavar="FICHERO")
opciones.add_argument("--tildes", action="store_true")
args = opciones.parse_args()

server, port = config_servidor("SMTP", "relay.uniovi.es", 25)
fromaddr, toaddr = obtener_direcciones()
subject = "Prueba SMTP con mensaje RFC 5322"
data = "Hola, este mensaje lo ha construido la biblioteca email de Python.\n"
if args.tildes:
    subject = "Prueba con tildes: ¿qué tal, Ñandú?"
    data = "Cuerpo con acentos: canción, pingüino, año.\n"

adjunto = None
if args.adjunto is not None:
    adjunto = args.adjunto or ruta_logo()
mensaje = construir_mensaje(fromaddr, toaddr, subject, data, adjunto=adjunto)
binario = bytes_para_smtp(mensaje)          # as_bytes() con CRLF

try:
    s = socket.create_connection((server, port), timeout=15)
except OSError as e:
    error_conexion(e, server, port)

RecvReply(s, b"220")
enviar(s, f"HELO {socket.gethostname()}")
RecvReply(s, b"250")
enviar(s, f"MAIL FROM:<{fromaddr}>")
RecvReply(s, b"250")
for destinatario in toaddr.split(","):
    enviar(s, f"RCPT TO:<{destinatario.strip()}>")
    RecvReply(s, b"250")
enviar(s, "DATA")
RecvReply(s, b"354")
# as_bytes() NO trae el punto final: lo añade preparar_para_data()
print(f"C: [mensaje RFC 5322 de {len(binario)} bytes"
      f"{', multipart con adjunto' if adjunto else ''}] + \\r\\n.\\r\\n")
s.sendall(preparar_para_data(binario))
RecvReply(s, b"250")
enviar(s, "QUIT")
RecvReply(s, b"221")
s.close()
print("Mensaje enviado.")
