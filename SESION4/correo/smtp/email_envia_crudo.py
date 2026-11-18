"""Ejercicio 7 (sesión 4, apartado 3.1.1): enviar un correo hablando SMTP "a mano".

Qué hace: abre un socket TCP al servidor SMTP (por defecto relay.uniovi.es:25)
y mantiene el diálogo completo HELO / MAIL FROM / RCPT TO / DATA / QUIT,
comprobando el código de cada respuesta con RecvReply(). El mensaje se
construye con la plantilla "artesanal" del guion.

Ejecución (relay.uniovi.es solo acepta conexiones desde la red de Uniovi):
    IS_FROM=uoXXXXXX@uniovi.es IS_TO=uoXXXXXX@uniovi.es python3 correo/smtp/email_envia_crudo.py
  contra el simulador local (ver README):
    IS_SMTP_SERVER=localhost IS_SMTP_PORT=2525 IS_FROM=a@example.com \\
    IS_TO=b@example.com python3 correo/smtp/email_envia_crudo.py

Concepto: SMTP (RFC 5321) es texto, línea a línea, terminadas en CRLF. El
cliente manda una ORDEN y el servidor contesta con un CÓDIGO de 3 cifras y
un texto. La primera cifra es lo que importa:
    2xx  bien          (220 listo, 250 OK, 221 adiós)
    3xx  sigue         (354 "manda el mensaje", 334 en AUTH)
    4xx  error temporal: reintenta más tarde (p. ej. 421, 450 buzón ocupado)
    5xx  error permanente: no insistas (550 no existe, 535 mala clave)
Ojo: relay.uniovi.es no pide contraseña (SMTP original no autentica); se
protege aceptando solo conexiones de dentro de la Universidad.
"""
import os
import socket
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from comun import config_servidor, error_conexion, obtener_direcciones


def RecvReply(sock, codigo):
    """Lee la respuesta del servidor, la muestra y exige que empiece por `codigo`.

    Como pide el guion se lee en bloques de 1024 bytes, pero no UNA sola vez:
    TCP es un flujo y una respuesta puede llegar partida en varios recv(), y
    las respuestas multilínea (EHLO) son "250-..." hasta una última "250 ...".
    Se sigue leyendo hasta tener una línea completa cuyo 4º carácter sea un
    espacio: esa es la última (RFC 5321, 4.2.1).
    """
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
    """Manda una orden SMTP (añadiendo CRLF) y la muestra."""
    print("C:", orden)
    sock.sendall(orden.encode("utf-8") + b"\r\n")


# --- Variables del programa principal (como las nombra el guion)
server, port = config_servidor("SMTP", "relay.uniovi.es", 25)
fromaddr, toaddr = obtener_direcciones()
subject = "Prueba SMTP en crudo"
data = "Hola, esto se ha enviado hablando SMTP directamente por un socket."

# Plantilla artesanal del guion, sin tocar. Fíjate en que las líneas del
# triple-comillado acaban en "\n" a secas (no CRLF): los servidores suelen
# tolerarlo, pero no es correcto. El ejercicio 8 lo arregla con la
# biblioteca email. Partes clave:
#   "\r\n\r\n"  línea en blanco: separa CABECERAS de CUERPO (RFC 5322)
#   "\r\n.\r\n" una línea con solo un punto: FIN de DATA (RFC 5321)
message = """To: %s
From: %s
Subject: %s\r\n\r\n
%s
\r\n.\r\n""" % (toaddr, fromaddr, subject, data)

# --- Conexión TCP
try:
    s = socket.create_connection((server, port), timeout=15)
except OSError as e:
    error_conexion(e, server, port)

RecvReply(s, b"220")        # 220 = saludo: "servicio listo"

# HELO: "soy esta máquina". Abre la sesión (EHLO sería la versión extendida)
enviar(s, f"HELO {socket.gethostname()}")
RecvReply(s, b"250")

# MAIL FROM: remitente del SOBRE (envelope). Es a quien se devuelven los
# errores (rebotes) y lo que mira SPF; NO es la cabecera From: del mensaje
enviar(s, f"MAIL FROM:<{fromaddr}>")
RecvReply(s, b"250")

# RCPT TO: destinatario del SOBRE; se repite una vez por destinatario.
# Las cabeceras To:/Cc: son solo informativas: decide el sobre (así funciona
# la copia oculta, Bcc: está en el sobre pero no en las cabeceras)
for destinatario in toaddr.split(","):
    enviar(s, f"RCPT TO:<{destinatario.strip()}>")
    RecvReply(s, b"250")

# DATA: el servidor responde 354 "adelante, termina con <CRLF>.<CRLF>"
enviar(s, "DATA")
RecvReply(s, b"354")
print("C: [mensaje de", len(message), "caracteres, terminado en \\r\\n.\\r\\n]")
s.sendall(message.encode("utf-8"))
RecvReply(s, b"250")        # 250 = aceptado y en cola para entregar

# QUIT: 221 = el servidor cierra la conexión
enviar(s, "QUIT")
RecvReply(s, b"221")
s.close()
print("Mensaje enviado.")
