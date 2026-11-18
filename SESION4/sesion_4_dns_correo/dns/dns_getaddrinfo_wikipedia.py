"""Ejercicio 6 (sesión 4, apartado 2.4, opcional): HTTP a Wikipedia con getaddrinfo.

Qué hace: obtiene con getaddrinfo() los parámetros para conectar a
en.wikipedia.org por el servicio "http", crea el socket y conecta por IPv4,
envía una petición HTTP GET / y muestra la respuesta. Después lo intenta por
IPv6 y, si falla (la red de la Universidad, y muchas redes domésticas o WSL,
no tienen IPv6), lo explica en vez de lanzar un traceback.

Ejecución:  python3 dns/dns_getaddrinfo_wikipedia.py [nombre]

Concepto:
  - getaddrinfo(nombre, "http", familia, SOCK_STREAM) devuelve directamente
    los argumentos de socket() (familia, tipo, proto) y de connect()
    (sockaddr): el código no tiene ni una IP ni un número de puerto escritos.
  - La petición lleva la cabecera "Host": el mismo servidor (la misma IP)
    atiende miles de sitios (en., es., www.wikipedia.org...) y es esa
    cabecera la que dice cuál quieres (VIRTUAL HOSTING).
  - "Connection: close" pide al servidor que cierre al terminar, así basta
    con leer hasta que recv() devuelva b"" (fin de conexión).
  - La respuesta será un "301 Moved Permanently" con "Location: https://...":
    Wikipedia no sirve contenido por HTTP en claro, redirige a HTTPS (puerto
    443, TLS). Es lo esperado: el ejercicio va de conectar, no de la página.
"""
import socket
import sys

nombre = sys.argv[1] if len(sys.argv) > 1 else "en.wikipedia.org"
PETICION = (f"GET / HTTP/1.1\r\n"
            f"Host: {nombre}\r\n"
            f"User-Agent: practicas-IS-dns_getaddrinfo\r\n"
            f"Connection: close\r\n"
            f"\r\n").encode("ascii")     # línea en blanco = fin de cabeceras


def pedir_pagina(familia):
    """Conecta con la primera dirección de esa familia y hace GET /."""
    # Filtrando por familia y tipo, la lista se reduce a lo que interesa
    opciones = socket.getaddrinfo(nombre, "http", familia, socket.SOCK_STREAM)
    fam, tipo, proto, _canon, sockaddr = opciones[0]
    print(f"Conectando a {sockaddr} (familia {fam.name}, proto {proto})")
    with socket.socket(fam, tipo, proto) as s:
        s.settimeout(5)
        s.connect(sockaddr)
        s.sendall(PETICION)
        trozos = []
        while True:
            trozo = s.recv(4096)
            if not trozo:          # el servidor cerró: respuesta completa
                break
            trozos.append(trozo)
    return b"".join(trozos)


# --- IPv4: debe funcionar
respuesta = pedir_pagina(socket.AF_INET)
cabeceras, _, cuerpo = respuesta.partition(b"\r\n\r\n")
print(cabeceras.decode("latin-1"))
print(f"\n[cuerpo: {len(cuerpo)} bytes]")
if b" 301 " in cabeceras.split(b"\r\n")[0]:
    print("-> 301: Wikipedia redirige a HTTPS (mirar la cabecera Location)")

# --- IPv6: lo normal es que falle; el error se explica, no se vuelca
print("\n=== Intento por IPv6")
try:
    respuesta6 = pedir_pagina(socket.AF_INET6)
    print(respuesta6.split(b"\r\n")[0].decode("latin-1"), "-> ¡esta red sí tiene IPv6!")
except socket.gaierror as e:
    print(f"No hay dirección IPv6 utilizable para {nombre} ({e}).")
except OSError as e:
    # Típico: [Errno 101] Network is unreachable (no hay ruta IPv6) o timeout
    print(f"IPv6 falla: {e}\n  El DNS sí devuelve un AAAA (getaddrinfo funciona),"
          " pero esta máquina no tiene conectividad IPv6\n  (sin dirección global"
          " o sin ruta por defecto IPv6). Es lo esperado en la red de Uniovi y en WSL.")
