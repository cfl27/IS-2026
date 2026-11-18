import getpass
import os
import sys
import warnings

HOST = os.getenv("IS_HOST", "localhost")
USUARIO = os.getenv("IS_USER", getpass.getuser())


def obtener_clave():
    # getpass no muestra lo que se teclea (ni lo deja en el historial del shell)
    return os.getenv("IS_PASS") or getpass.getpass(f"Clave de {USUARIO}@{HOST}: ")


def importar_telnetlib():
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            import telnetlib
        return telnetlib
    except ImportError:
        v = sys.version_info
        print(f"ERROR: este Python ({v.major}.{v.minor}) ya no incluye telnetlib "
              "(eliminado en 3.13).\n"
              "Alternativas:\n"
              "  - ejecutarlo con Python <= 3.12 (p. ej. python3.12 telnet/...);\n"
              "  - instalar la copia de PyPI en un entorno virtual:\n"
              "        python3 -m venv ~/telnetenv && ~/telnetenv/bin/pip install telnetlib-313-and-up\n"
              "        ~/telnetenv/bin/python telnet/...\n"
              "  - telnet0_sockets_crudo.py no lo necesita (usa sockets).")
        sys.exit(1)
