"""Apartado 3.1.2 (+ experimento de tildes) y ejercicio 9: crear mensajes RFC 5322.

Qué hace: construye un mensaje con la biblioteca `email` y lo imprime TAL
CUAL viajaría por SMTP, para ver qué cabeceras añade Python y cómo codifica.
  (sin opciones)  el código exacto del guion
  --tildes        experimento: tildes en nombres, asunto y cuerpo, y el mismo
                  cuerpo con las tres codificaciones (8bit, quoted-printable,
                  base64)
  --adjunto [F]   ejercicio 9: añade logoatc.gif (o el fichero F) -> multipart
  --guardar F     además, guarda el mensaje en F (.eml) para analizarlo con
                  email_decodificar.py o enviarlo

Ejecución:
    python3 correo/mensajes/email_crear_mensaje_prueba.py
    python3 correo/mensajes/email_crear_mensaje_prueba.py --tildes
    python3 correo/mensajes/email_crear_mensaje_prueba.py --adjunto

Concepto:
  - Python añade MIME-Version, Content-Type (text/plain; charset=...) y
    Content-Transfer-Encoding: el receptor necesita saber en qué juego de
    caracteres y con qué codificación va el cuerpo.
  - Las CABECERAS solo pueden llevar ASCII. Un "Asunto: Ñandú" se codifica
    según RFC 2047 como "encoded-word":   =?utf-8?q?=C3=91and=C3=BA?=
        =?charset?codificación?texto?=   con q (tipo quoted-printable) o
        b (base64). El cliente de correo lo deshace al mostrarlo.
  - El CUERPO con tildes: Python elige "8bit" (UTF-8 tal cual: válido si el
    servidor anuncia 8BITMIME en su EHLO). Para canales de 7 bits:
        quoted-printable  "canci=C3=B3n": legible si hay pocas tildes
        base64            todo ilegible, 4 caracteres por cada 3 bytes
  - El mensaje NO lleva el punto final: eso es cosa del protocolo SMTP, no
    del formato del mensaje (smtplib lo añade; en crudo, nosotros).
"""
import argparse
import email.header
import email.message
import email.policy
import email.utils
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mensajes import construir_mensaje, ruta_logo

opciones = argparse.ArgumentParser(description=__doc__.split("\n")[0])
opciones.add_argument("--tildes", action="store_true", help="experimento con tildes")
opciones.add_argument("--adjunto", nargs="?", const="", metavar="FICHERO",
                      help="ejercicio 9: adjuntar (por defecto logoatc.gif)")
opciones.add_argument("--guardar", metavar="FICHERO.eml")
args = opciones.parse_args()

if not args.tildes and args.adjunto is None:
    # ------------------------------------------------ El código del guion
    mensaje = email.message.EmailMessage()
    mensaje['To'] = 'Desti Natario <destinatario@example.com>'
    mensaje['From'] = 'Remi Tente <remitente@example.com>'
    mensaje['Subject'] = 'Mensaje de prueba'
    mensaje['Date'] = email.utils.formatdate(localtime=True)
    mensaje['Message-ID'] = email.utils.make_msgid()
    mensaje.set_content("Esto es una prueba")

    binario = mensaje.as_bytes()
    print(binario.decode("utf-8"))

elif args.tildes:
    # ------------------------------------------------ Experimento de tildes
    para = "Désti Ñatario <destinatario@example.com>"
    de = "Remi Tênte <remitente@example.com>"
    asunto = "Prueba con tildes: ¿qué tal, Ñandú?"
    cuerpo = "Cuerpo con acentos: canción, pingüino, año y €.\n"
    for cte in (None, "quoted-printable", "base64"):
        mensaje = construir_mensaje(de, para, asunto, cuerpo, cte=cte)
        print("=" * 25, f"cuerpo con cte={cte or 'automático (8bit)'}", "=" * 25)
        print(mensaje.as_bytes().decode("utf-8"))
    # Las cabeceras se codifican igual en los tres: se ve deshaciendo el
    # "encoded-word" del asunto
    crudo = mensaje.as_bytes().split(b"\n")
    linea = next(l for l in crudo if l.startswith(b"Subject:")).decode()
    print("Asunto codificado (RFC 2047):", linea)
    print("Decodificado:", email.header.make_header(email.header.decode_header(linea[9:])))

else:
    # ------------------------------------------------ Ejercicio 9: adjunto
    fichero = args.adjunto or ruta_logo()
    mensaje = construir_mensaje("Remi Tente <remitente@example.com>",
                                "Desti Natario <destinatario@example.com>",
                                "Mensaje con adjunto", "Va un GIF adjunto.\n",
                                adjunto=fichero)
    print(mensaje.as_bytes().decode("ascii"))
    # Lo que hay que observar:
    print("-" * 70)
    print("Content-Type raíz:", mensaje.get_content_type(),
          "| boundary (aleatorio):", mensaje.get_boundary())
    for parte in mensaje.iter_parts():
        print(f"  parte {parte.get_content_type():<11} codificada en "
              f"{parte['Content-Transfer-Encoding']:<7} nombre={parte.get_filename()}")

if args.guardar:
    # Con la política SMTP (CRLF), igual que se enviaría
    with open(args.guardar, "wb") as f:
        f.write(mensaje.as_bytes(policy=email.policy.SMTP))
    print(f"(guardado en {args.guardar})")
