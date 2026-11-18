"""Utilidades para CONSTRUIR mensajes de correo (sesión 4, apartados 3.1.2 y 3.1.3).

Qué hace: lo que se repite en varios ejercicios, en un solo sitio:
  - construir_mensaje(): un EmailMessage conforme a RFC 5322 (ejs. 8, 9, 11, 12).
  - bytes_para_smtp(): los bytes del mensaje con CRLF, listos para smtplib.
  - preparar_para_data(): además "dot-stuffing" y el punto final, para
    mandarlo A MANO tras el comando DATA (clientes en crudo).
  - ruta_logo(): el GIF del ejercicio 9 (lo descarga con wget si hay red y,
    si no, genera un GIF diminuto de prueba: no depende de Internet).

No se ejecuta directamente: lo importan los demás scripts, que añaden esta
carpeta a sys.path.

Concepto: ¿por qué la biblioteca `email` y no una plantilla de texto (la del
ejercicio 7)? Porque un mensaje de verdad tiene reglas que la plantilla no
cumple: cabeceras SOLO en ASCII (las tildes se codifican según RFC 2047),
líneas de como mucho 998 bytes, finales de línea CRLF, Date y Message-ID
bien formados, MIME para indicar el juego de caracteres y para los adjuntos
(multipart/mixed con boundary)... EmailMessage lo hace todo.
"""
import email.message
import email.policy
import email.utils
import mimetypes
import os
import shutil
import subprocess
import tempfile

URL_LOGO = "http://www.atc.uniovi.es/estilo_atc/logoatc.gif"

# GIF de 1x1 píxel (43 bytes) escrito a mano: cabecera "GIF89a", tamaño,
# paleta de 2 colores, extensión de control, imagen y fin (";"). Sirve de
# adjunto cuando no hay red para descargar el logo del guion.
GIF_PRUEBA = (b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff"
              b"!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00"
              b"\x00\x02\x02D\x01\x00;")


def construir_mensaje(fromaddr, toaddr, subject, data, adjunto=None, cte=None):
    """EmailMessage con To, From, Subject, Date, Message-ID y cuerpo `data`.

    adjunto: ruta de un fichero a adjuntar (el mensaje pasa a multipart/mixed).
    cte: "quoted-printable" o "base64" para forzar la codificación del cuerpo
         (None = que elija Python: 7bit si es ASCII, 8bit si no).
    """
    mensaje = email.message.EmailMessage()   # política email.policy.default
    mensaje["To"] = toaddr
    mensaje["From"] = fromaddr
    mensaje["Subject"] = subject
    # Date en el formato de RFC 5322 ("Sat, 07 Nov 2026 19:42:00 +0100")
    mensaje["Date"] = email.utils.formatdate(localtime=True)
    # Identificador único mundial: <numeros.aleatorios@nombre-de-esta-máquina>
    mensaje["Message-ID"] = email.utils.make_msgid()
    if cte:
        mensaje.set_content(data, cte=cte)
    else:
        mensaje.set_content(data)

    if adjunto:
        with open(adjunto, "rb") as f:
            contenido = f.read()
        # El tipo MIME se deduce de la extensión (.gif -> image/gif), como
        # sugiere el guion con la biblioteca mimetypes
        tipo, _ = mimetypes.guess_type(adjunto)
        principal, subtipo = (tipo or "application/octet-stream").split("/")
        # El nombre con el que lo verá el destinatario ("atc.gif" en el guion)
        nombre = "atc.gif" if os.path.basename(adjunto).startswith("logoatc") \
            else os.path.basename(adjunto)
        # add_attachment convierte el mensaje en multipart/mixed: parte 1 el
        # texto, parte 2 el fichero en base64 (binario -> ASCII seguro)
        mensaje.add_attachment(contenido, principal, subtipo, filename=nombre)
    return mensaje


def bytes_para_smtp(mensaje):
    """Bytes del mensaje con finales de línea CRLF.

    OJO: mensaje.as_bytes() a secas usa la política del mensaje (default),
    cuyos finales de línea son "\\n". SMTP exige "\\r\\n" (RFC 5321) y hoy
    muchos servidores rechazan los "LF sueltos" (son la base del ataque
    "SMTP smuggling"). La política email.policy.SMTP es la misma pero con
    linesep="\\r\\n". (smtplib.send_message lo hace solo; sendmail no.)
    """
    return mensaje.as_bytes(policy=email.policy.SMTP)


def preparar_para_data(binario):
    """Lo que hay que mandar tras "354" en un cliente en crudo.

    1. Dot-stuffing (RFC 5321, 4.5.2): el fin de DATA es una línea con solo
       un punto. Si el texto tuviera una línea que empieza por ".", el
       servidor la confundiría con el final; por eso se le añade otro punto
       ("..") y el servidor lo quita al recibir.
    2. El terminador "\\r\\n.\\r\\n" (as_bytes NO lo incluye: smtplib lo añade
       solo, pero en crudo es cosa nuestra).
    """
    if not binario.endswith(b"\r\n"):
        binario += b"\r\n"
    if binario.startswith(b"."):
        binario = b"." + binario
    return binario.replace(b"\r\n.", b"\r\n..") + b".\r\n"


def ruta_logo():
    """Ruta a logoatc.gif: ya descargado, descargado ahora con wget o generado.

    Se guarda en el directorio temporal para no ensuciar el repositorio.
    Con IS_SIN_RED=1 no se intenta la descarga (lo usa probar_sesion4.sh
    para que la prueba no dependa de Internet).
    """
    ruta = os.path.join(tempfile.gettempdir(), "logoatc.gif")
    if os.path.exists(ruta) and os.path.getsize(ruta) > 0:
        return ruta
    if shutil.which("wget") and not os.getenv("IS_SIN_RED"):
        # El mismo wget del guion, con timeout para no colgarse sin red
        r = subprocess.run(["wget", "-q", "-T", "5", "-t", "1", "-O", ruta, URL_LOGO])
        if r.returncode == 0 and os.path.getsize(ruta) > 0:
            return ruta
    with open(ruta, "wb") as f:      # sin red: GIF de prueba
        f.write(GIF_PRUEBA)
    return ruta
