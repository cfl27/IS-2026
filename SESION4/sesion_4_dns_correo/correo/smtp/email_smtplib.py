"""Ejercicio 12 (sesión 4, apartado 3.1.6): enviar con smtplib (Gmail).

Qué hace: lo mismo que email_envia_crudo_ssl.py (STARTTLS + login + envío),
pero con la biblioteca estándar smtplib. set_debuglevel(1) muestra el
diálogo, así se comprueba que por debajo pasa EXACTAMENTE lo mismo que en la
versión en crudo.

Ejecución (Gmail: usuario = tu dirección, clave = contraseña de aplicación):
    IS_FROM=tucuenta@gmail.com IS_TO=tucuenta@gmail.com python3 correo/smtp/email_smtplib.py
  (contra el simulador, ver README)

Concepto:
  - smtplib hace por nosotros: leer respuestas multilínea, comprobar códigos
    (lanza excepciones SMTPxxxError), EHLO automático, AUTH (elige el método
    entre los que anuncia el servidor), dot-stuffing y el punto final.
  - sendmail(remitente, [destinatarios], mensaje): los dos primeros
    argumentos son el SOBRE (MAIL FROM / RCPT TO); el tercero, el mensaje.
    Por eso as_bytes() va SIN el punto final.
  - OJO con starttls() sin argumentos: usa un contexto que NO verifica el
    certificado (ssl._create_stdlib_context). Se le pasa
    ssl.create_default_context() para que sí lo haga.
"""
import getpass
import os
import smtplib
import ssl
import sys

DIR_SESION = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, DIR_SESION)
sys.path.insert(0, os.path.join(DIR_SESION, "correo", "mensajes"))
from comun import config_servidor, error_conexion, obtener_direcciones
from mensajes import bytes_para_smtp, construir_mensaje

server, port = config_servidor("SMTP", "smtp.gmail.com", 587)
fromaddr, toaddr = obtener_direcciones()
username = os.getenv("IS_USER") or input("Usuario: ")
password = os.getenv("IS_PASS") or getpass.getpass("Contraseña: ")

mensaje = construir_mensaje(fromaddr, toaddr, "Prueba con smtplib",
                            "Enviado con smtplib: starttls(), login() y sendmail().\n")

try:
    s = smtplib.SMTP(server, port, timeout=15)   # conecta y lee el 220
    s.set_debuglevel(1)                          # muestra "send:" / "reply:"
    s.starttls(context=ssl.create_default_context())  # EHLO + STARTTLS + TLS
    s.login(username, password)                  # EHLO + AUTH
    s.sendmail(fromaddr, [d.strip() for d in toaddr.split(",")],
               bytes_para_smtp(mensaje))         # MAIL, RCPT, DATA, "."
    s.quit()                                     # QUIT
except smtplib.SMTPAuthenticationError as e:
    print(f"\nERROR {e.smtp_code}: usuario o contraseña incorrectos.\n"
          "  En Gmail hace falta una CONTRASEÑA DE APLICACIÓN, no la normal.")
    sys.exit(1)
except smtplib.SMTPException as e:
    print(f"\nERROR SMTP: {e}")
    sys.exit(1)
except OSError as e:
    error_conexion(e, server, port)
print("Mensaje enviado con smtplib.")
