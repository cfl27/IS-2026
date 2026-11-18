"""Ejercicio 16 (sesión 4, apartado 3.2.3, opcional): resumen BIEN decodificado de cada mensaje.

Qué hace: descarga con poplib todos los mensajes y de cada uno imprime From,
Subject (con las tildes decodificadas) y los primeros 500 caracteres del
cuerpo, usando la función imprime_resumen_mensaje() del guion.
Con --mejorada usa una versión con la API moderna de `email` que además
decodifica bien cuerpos en base64 / quoted-printable.

Ejecución:
    python3 correo/pop3/email_pop3_poplib2.py [--mejorada]
  (IS_USER / IS_PASS, IS_POP_SERVER / IS_POP_PORT como en los demás)

Concepto: de bytes en bruto a texto legible hay tres capas:
  1. el FORMATO del mensaje (RFC 5322): cabeceras + línea en blanco + cuerpo;
     email.message_from_bytes() lo analiza;
  2. las CABECERAS no ASCII, en "encoded-words" RFC 2047
     (=?utf-8?q?...?=): decode_header() las trocea y make_header() las une;
  3. el CUERPO MIME: puede ser multipart (lista de partes) y cada parte ir
     en base64 o quoted-printable con un charset.
Nota sobre el código del guion (se deja tal cual, es el del ejercicio):
  - no importa email.header (hay que importarlo, como aquí);
  - "el cuerpo ya vendrá correctamente decodificado" solo es cierto si va en
    7bit/8bit: get_payload() sin decode=True NO deshace base64 ni
    quoted-printable (se ve con un mensaje enviado con cte=base64). La
    versión --mejorada lo resuelve con policy=default y get_content().
"""
import argparse
import email
import email.header
import email.policy
import os
import poplib
import ssl
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from comun import config_servidor, error_conexion, obtener_clave, obtener_usuario


def imprime_resumen_mensaje(msg_bytes):
    # Parsear los bytes recibidos y construir con ellos un objeto EmailMessage
    msg = email.message_from_bytes(msg_bytes)

    # Extraemos las cabeceras "From" y "Subject"
    remite = msg.get("From", "<desconocido>")
    asunto = msg.get("Subject", "<sin asunto>")

    # Si estas cabeceras contienen unicode hay que decodificarlas
    # lo que es un poco enrevesado
    remite = email.header.make_header(email.header.decode_header(remite))
    asunto = email.header.make_header(email.header.decode_header(asunto))

    # Extraemos el cuerpo (este ya vendrá correctamente decodificado)
    cuerpo = msg.get_payload()

    # Pero si es multi-part, lo anterior nos retorna una lista
    # En ese caso nos quedamos con el primer elemento, que será a su
    # vez un mensaje con su propio payload
    if type(cuerpo) == list:
        parte_1 = cuerpo[0].get_payload()
        cuerpo = "---Multipart. Parte 1\n" + parte_1

    # Finalmente imprimimos un resumen, que son las cabeceras
    # extraidas y los primeros 200 caracteres del mensaje
    print("From:", remite)
    print("Subject:", asunto)
    print(cuerpo[:500])
    if len(cuerpo) > 500:
        print("...[omitido]")
    print("-" * 80)


def imprime_resumen_mensaje_mejorada(msg_bytes):
    """Igual, con la API moderna: policy=default decodifica las cabeceras
    sola, get_body() elige la parte de texto aunque esté anidada, y
    get_content() deshace base64/quoted-printable y aplica el charset."""
    msg = email.message_from_bytes(msg_bytes, policy=email.policy.default)
    print("From:", msg.get("From", "<desconocido>"))
    print("Subject:", msg.get("Subject", "<sin asunto>"))
    texto = msg.get_body(preferencelist=("plain", "html"))
    cuerpo = texto.get_content() if texto else "<sin parte de texto>"
    adjuntos = [p.get_filename() for p in msg.iter_attachments()]
    if adjuntos:
        cuerpo = f"---Adjuntos: {', '.join(adjuntos)}\n" + cuerpo
    print(cuerpo[:500])
    if len(cuerpo) > 500:
        print("...[omitido]")
    print("-" * 80)


opciones = argparse.ArgumentParser(description="Resumen de cada mensaje POP3")
opciones.add_argument("--mejorada", action="store_true")
args = opciones.parse_args()
resumen = imprime_resumen_mensaje_mejorada if args.mejorada else imprime_resumen_mensaje

server, port = config_servidor("POP", "pop.gmail.com", 995)
usuario = obtener_usuario()
clave = obtener_clave()

try:
    pop3_mail = poplib.POP3_SSL(server, port, timeout=15,
                                context=ssl.create_default_context())
    pop3_mail.user(usuario)
    pop3_mail.pass_(clave)
    num, _ = pop3_mail.stat()
    print(f"{num} mensajes\n" + "-" * 80)
    for n in range(1, num + 1):
        _respuesta, lineas, _octetos = pop3_mail.retr(n)
        # poplib entrega las líneas sin "\r\n": se vuelven a unir con CRLF
        # para tener los bytes del mensaje que espera message_from_bytes()
        resumen(b"\r\n".join(lineas))
    pop3_mail.quit()
except poplib.error_proto as e:
    print(f"ERROR POP3: {e.args[0].decode(errors='replace')}\n"
          "  ¿Usuario o contraseña incorrectos? En Gmail: contraseña de aplicación y POP activado.")
    sys.exit(1)
except OSError as e:
    error_conexion(e, server, port)
