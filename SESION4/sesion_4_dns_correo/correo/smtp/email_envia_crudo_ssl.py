"""Ejercicio 11 (sesión 4, apartado 3.1.5): SMTP en crudo con STARTTLS y AUTH LOGIN (Gmail).

Qué hace: como email_envia_crudo_rfc5322.py, pero contra un servidor de
"envío" (submission) que exige cifrado y contraseña, por defecto
smtp.gmail.com:587:
    EHLO -> ¿anuncia STARTTLS? -> STARTTLS (220) -> TLS con wrap_socket
    -> EHLO otra vez -> AUTH LOGIN (334) -> usuario b64 (334) -> clave b64 (235)
    -> MAIL FROM / RCPT TO / DATA / QUIT, todo ya por el canal cifrado.

Ejecución (Gmail: usuario = tu dirección, clave = CONTRASEÑA DE APLICACIÓN):
    IS_FROM=tucuenta@gmail.com IS_TO=tucuenta@gmail.com python3 correo/smtp/email_envia_crudo_ssl.py
  pide usuario y contraseña (o IS_USER / IS_PASS). Contra el simulador, ver README.

Concepto:
  - STARTTLS (puertos 587 y 25): la conexión EMPIEZA en claro y el cliente
    pide "pasemos a TLS"; tras el 220 ambos negocian TLS SOBRE EL MISMO
    socket. SSL/TLS IMPLÍCITO (puerto 465 en SMTP, 995 en POP3): el TLS
    empieza nada más conectar, antes de cualquier orden.
  - wrap_socket() devuelve un socket NUEVO (sc) que cifra y descifra. El
    viejo (s) ya no se toca: lo que se escribiera por él iría en claro y
    rompería el TLS.
  - Tras STARTTLS hay que repetir EHLO (RFC 3207): el servidor olvida todo
    lo dicho en claro (un atacante pudo haberlo alterado) y ahora anuncia
    extensiones nuevas, como AUTH.
  - create_default_context() VERIFICA el certificado y que sea de
    server_hostname: sin eso, TLS no protege de un intermediario (MITM).
  - AUTH LOGIN manda usuario y clave en BASE64. Base64 NO es cifrado: es
    una forma de escribir bytes con 64 caracteres ASCII, reversible por
    cualquiera ("Y2xhdmU=" -> "clave"). La protección la da el TLS de
    debajo; por eso el servidor solo ofrece AUTH después de STARTTLS.
  - Gmail no acepta la contraseña normal: hace falta una contraseña de
    aplicación (o OAuth2, que es lo que usan los clientes modernos).
"""
import base64
import getpass
import os
import socket
import ssl
import sys

DIR_SESION = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, DIR_SESION)
sys.path.insert(0, os.path.join(DIR_SESION, "correo", "mensajes"))
from comun import config_servidor, error_conexion, obtener_direcciones
from mensajes import bytes_para_smtp, construir_mensaje, preparar_para_data

# Pistas para los errores típicos de este ejercicio
PISTAS = {b"535": "usuario o contraseña incorrectos (en Gmail: ¿es una contraseña de APLICACIÓN?)",
          b"530": "el servidor exige autenticarse (o STARTTLS) antes de MAIL FROM",
          b"534": "Gmail pide iniciar sesión vía web / contraseña de aplicación"}


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
        if respuesta[:3] in PISTAS:
            print("  ->", PISTAS[respuesta[:3]])
        sys.exit(1)
    return respuesta


def enviar(sock, orden, mostrar=None):
    """Manda una orden; `mostrar` permite no imprimir secretos en pantalla."""
    print("C:", mostrar if mostrar is not None else orden)
    sock.sendall(orden.encode("ascii") + b"\r\n")


server, port = config_servidor("SMTP", "smtp.gmail.com", 587)
fromaddr, toaddr = obtener_direcciones()
subject = "Prueba SMTP con STARTTLS y AUTH LOGIN"
data = "Enviado en crudo, pero cifrado con TLS y autenticado.\n"

# --- Conexión en claro y EHLO
try:
    s = socket.create_connection((server, port), timeout=15)
except OSError as e:
    error_conexion(e, server, port)
RecvReply(s, b"220")
enviar(s, f"EHLO {socket.gethostname()}")
extensiones = RecvReply(s, b"250")      # lista "250-EXTENSION"
if b"STARTTLS" not in extensiones.upper():
    print("ERROR: el servidor no anuncia STARTTLS: no mando la clave en claro")
    sys.exit(1)

# --- STARTTLS: a partir del 220, TLS sobre el mismo socket
enviar(s, "STARTTLS")
RecvReply(s, b"220")
context = ssl.create_default_context()
try:
    sc = context.wrap_socket(s, server_hostname=server)
except ssl.SSLError as e:
    error_conexion(e, server, port)
print(f"   [canal cifrado: {sc.version()}, {sc.cipher()[0]}]")

# --- EHLO otra vez, ya cifrado: ahora sí aparece AUTH
enviar(sc, f"EHLO {socket.gethostname()}")
RecvReply(sc, b"250")

# --- AUTH LOGIN: el servidor pregunta en base64 ("VXNlcm5hbWU6" = "Username:")
enviar(sc, "AUTH LOGIN")
reto = RecvReply(sc, b"334")
print("   (el 334 trae en base64:", base64.b64decode(reto[4:].strip() or b"").decode(), ")")
# Usuario y clave como en el guion (input/getpass), o de IS_USER / IS_PASS
username = os.getenv("IS_USER") or input("Usuario: ")
password = os.getenv("IS_PASS") or getpass.getpass("Contraseña: ")

sc.send(base64.b64encode(username.encode("ascii")) + b'\r\n')
print("C:", base64.b64encode(username.encode("ascii")).decode(), " (usuario en base64)")
RecvReply(sc, b"334")             # esperamos 334: ahora pide la contraseña
sc.send(base64.b64encode(password.encode("utf8")) + b'\r\n')
print("C: ******** (contraseña en base64: NO se muestra, base64 se revierte)")
RecvReply(sc, b"235")             # esperamos 235: autenticado

# --- Envío normal, todo por sc
enviar(sc, f"MAIL FROM:<{fromaddr}>")
RecvReply(sc, b"250")
for destinatario in toaddr.split(","):
    enviar(sc, f"RCPT TO:<{destinatario.strip()}>")
    RecvReply(sc, b"250")
enviar(sc, "DATA")
RecvReply(sc, b"354")
mensaje = construir_mensaje(fromaddr, toaddr, subject, data)
print("C: [mensaje RFC 5322] + \\r\\n.\\r\\n")
sc.sendall(preparar_para_data(bytes_para_smtp(mensaje)))
RecvReply(sc, b"250")
enviar(sc, "QUIT")
RecvReply(sc, b"221")
sc.close()
print("Mensaje enviado por canal cifrado.")
