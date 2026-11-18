"""Ejercicio 15 (sesión 4, apartado 3.2.2): leer el primer correo con poplib.

Qué hace: lo mismo que el ejercicio 13 pero con la biblioteca estándar
poplib: POP3_SSL (TLS implícito), user(), pass_(), stat() y retr(1). Muestra
el resultado de retr() TAL CUAL lo devuelve poplib, para ver su forma.
set_debuglevel(2) imprime además cada orden y cada respuesta.

Ejecución:
    python3 correo/pop3/email_pop3_poplib.py      (pide usuario y clave)
  o con IS_USER / IS_PASS, e IS_POP_SERVER / IS_POP_PORT para el simulador.

Concepto: retr(n) devuelve una tupla de 3 elementos:
    (b'+OK ...', [línea1, línea2, ...], tamaño_en_octetos)
  - las líneas son bytes SIN el "\\r\\n" final, ya sin el punto final y sin
    dot-stuffing (poplib hace lo que en crudo hacíamos a mano);
  - para reconstruir el mensaje: b"\\r\\n".join(líneas) (ejercicio 16).
Los errores "-ERR" se convierten en la excepción poplib.error_proto.
OJO: POP3_SSL sin `context` NO verifica el certificado; se le pasa
ssl.create_default_context() para que sí lo haga (igual que en smtplib).
"""
import os
import poplib
import ssl
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from comun import config_servidor, error_conexion, obtener_clave, obtener_usuario

server, port = config_servidor("POP", "pop.gmail.com", 995)
usuario = obtener_usuario()
clave = obtener_clave()

try:
    pop3_mail = poplib.POP3_SSL(server, port, timeout=15,
                                context=ssl.create_default_context())
    pop3_mail.set_debuglevel(2)
    pop3_mail.user(usuario)          # AUTHORIZATION
    # Con debug 2 poplib imprimiría "*cmd* 'PASS <clave>'" en claro: se baja
    # a 0 solo para esta orden y se vuelve a subir
    pop3_mail.set_debuglevel(0)
    print("*cmd* 'PASS ********'")
    pop3_mail.pass_(clave)           # -> TRANSACTION
    pop3_mail.set_debuglevel(2)
    num, octetos = pop3_mail.stat()
    print(f"\nSTAT: {num} mensajes, {octetos} bytes")
    if num:
        respuesta = pop3_mail.retr(1)
        print("\nretr(1) devuelve una tupla de", len(respuesta), "elementos:")
        print(respuesta)
    pop3_mail.quit()                 # -> UPDATE
except poplib.error_proto as e:
    print(f"\nERROR POP3: {e.args[0].decode(errors='replace')}\n"
          "  ¿Usuario o contraseña incorrectos? En Gmail: contraseña de aplicación y POP activado.")
    sys.exit(1)
except OSError as e:
    error_conexion(e, server, port)
