"""Ajustes comunes a todos los scripts de correo de la sesión 4 (SMTP y POP3).

Qué hace: decide a qué servidor se conecta cada script, con qué direcciones
y con qué credenciales, y da mensajes de error claros cuando algo falla.

Concepto: NO escribir en el código ni contraseñas ni direcciones reales. Un
script con la contraseña dentro acaba subido a git o compartido. Por eso todo
se lee de VARIABLES DE ENTORNO y, si no están, se pregunta por teclado (la
contraseña con getpass, que no hace eco ni la deja en el historial):

  IS_SMTP_SERVER  IS_SMTP_PORT   servidor SMTP  (por defecto, el del guion
                                 para cada ejercicio: relay.uniovi.es:25 o
                                 smtp.gmail.com:587)
  IS_POP_SERVER   IS_POP_PORT    servidor POP3  (por defecto pop.gmail.com:995)
  IS_FROM         IS_TO          remitente y destinatario del sobre SMTP
  IS_USER         IS_PASS        usuario y contraseña (Gmail: la dirección
                                 completa y una CONTRASEÑA DE APLICACIÓN)

Así el mismo script sirve, sin tocar una línea, contra el servidor real del
guion o contra los simuladores locales de simuladores/ (que es lo que hace
probar_sesion4.sh).

Cómo lo usan los demás scripts: están en subcarpetas (correo/smtp, ...), así
que añaden la carpeta de la sesión a sys.path antes de `from comun import ...`.

Ejemplo:
    IS_FROM=yo@example.com IS_TO=tu@example.com python3 correo/smtp/email_envia_crudo.py
"""
import getpass
import os
import socket
import ssl
import sys


def _pedir(variable, texto):
    """Valor de la variable de entorno o, si no existe, lo pregunta."""
    valor = os.getenv(variable)
    if valor:
        return valor
    return input(f"{texto} [{variable}]: ").strip()


def config_servidor(prefijo, servidor_defecto, puerto_defecto):
    """(servidor, puerto) de IS_<prefijo>_SERVER / IS_<prefijo>_PORT o los del guion."""
    servidor = os.getenv(f"IS_{prefijo}_SERVER", servidor_defecto)
    puerto = int(os.getenv(f"IS_{prefijo}_PORT", puerto_defecto))
    return servidor, puerto


def obtener_direcciones():
    """Remitente y destinatario (IS_FROM / IS_TO o por teclado)."""
    return _pedir("IS_FROM", "Remitente"), _pedir("IS_TO", "Destinatario")


def obtener_usuario():
    """Usuario para AUTH LOGIN / POP3 (IS_USER o por teclado, como el guion)."""
    return _pedir("IS_USER", "Usuario")


def obtener_clave():
    """Contraseña de IS_PASS o pedida sin eco. Nunca se guarda en disco."""
    return os.getenv("IS_PASS") or getpass.getpass("Contraseña: ")


def error_conexion(e, servidor, puerto):
    """Explica en castellano por qué no se pudo conectar y termina (código 2).

    Un traceback no enseña nada en la defensa; estas pistas sí: son los tres
    fallos típicos de la práctica.
    """
    print(f"\nERROR: no se pudo hablar con {servidor}:{puerto} -> {e!r}")
    if isinstance(e, socket.gaierror):
        print("  El nombre no se resuelve por DNS (¿hay red? ¿está bien escrito?).")
    elif isinstance(e, ssl.SSLCertVerificationError):
        print("  El certificado del servidor no es de confianza. Si es un simulador\n"
              "  local, exporta SSL_CERT_FILE con su certificado (ver README).")
    elif isinstance(e, (ConnectionRefusedError, TimeoutError, socket.timeout)):
        print("  Nadie escucha o un cortafuegos lo filtra. relay.uniovi.es solo\n"
              "  acepta conexiones desde la red de la Universidad; muchos ISP\n"
              "  bloquean además el puerto 25 de salida.")
    sys.exit(2)
