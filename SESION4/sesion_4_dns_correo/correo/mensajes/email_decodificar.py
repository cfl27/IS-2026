"""Utilidad: analizar un mensaje (.eml) como lo hace un cliente de correo.

Qué hace: lee un mensaje en bruto (fichero o entrada estándar), muestra cada
cabecera importante CODIFICADA (tal como viaja) y DECODIFICADA (como la ve el
usuario), y recorre su árbol MIME: tipo de cada parte, codificación de
transferencia, nombre de fichero y contenido ya decodificado. Es una
"Mostrar original" de Gmail, pero al revés: del original a lo legible.

Ejecución:
    python3 correo/mensajes/email_decodificar.py mensaje.eml
    python3 correo/mensajes/email_crear_mensaje_prueba.py --adjunto --guardar /tmp/m.eml
    python3 correo/mensajes/email_decodificar.py /tmp/m.eml
(probar_sesion4.sh lo usa para comprobar lo que llega al buzón del simulador.)

Concepto: con policy=email.policy.default el parser devuelve un EmailMessage
"moderno": msg["Subject"] ya viene decodificado de RFC 2047 y
get_content() deshace base64 / quoted-printable y aplica el charset. Es la
forma recomendada hoy; la del guion (ej. 16, email.header.decode_header)
corresponde a la API antigua (policy compat32), que es la de por defecto.
"""
import email
import email.policy
import sys

datos = open(sys.argv[1], "rb").read() if len(sys.argv) > 1 else sys.stdin.buffer.read()

crudo = email.message_from_bytes(datos)                          # API antigua
msg = email.message_from_bytes(datos, policy=email.policy.default)  # moderna

print("=== Cabeceras (codificada -> decodificada)")
for nombre in ("Return-Path", "Received", "From", "To", "Subject", "Date", "Message-ID"):
    if msg[nombre] is not None:
        original = " ".join(str(crudo[nombre]).split())   # sin pliegues
        decodificada = str(msg[nombre])
        print(f"{nombre}: {original}")
        if decodificada != original:
            print(f"{' ' * len(nombre)}  -> {decodificada}")

print("\n=== Estructura MIME")
for parte in msg.walk():
    profundidad = 0 if parte is msg else 1
    sangria = "  " * profundidad
    linea = f"{sangria}{parte.get_content_type()}"
    if parte.get_content_charset():
        linea += f"; charset={parte.get_content_charset()}"
    if parte.get_boundary():
        linea += f"; boundary={parte.get_boundary()}"
    if parte["Content-Transfer-Encoding"]:
        linea += f"  [cte {parte['Content-Transfer-Encoding']}]"
    if parte.get_filename():
        linea += f"  ADJUNTO filename={parte.get_filename()}"
    print(linea)
    if parte.is_multipart():
        continue
    contenido = parte.get_content()       # ya decodificado
    if isinstance(contenido, str):
        for l in contenido.splitlines()[:10]:
            print(f"{sangria}  | {l}")
    else:
        print(f"{sangria}  | {len(contenido)} bytes binarios, empiezan por {contenido[:6]!r}")
