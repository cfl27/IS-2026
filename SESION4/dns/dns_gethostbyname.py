"""Experimento gethostbyname / gethostbyname_ex (sesión 4, apartado 2.3.2).

Qué hace: resuelve apple.com y www.uniovi.es (o los nombres que se pasen)
con la API POSIX clásica y explica cada elemento de la tupla que devuelve
gethostbyname_ex().

Ejecución:  python3 dns/dns_gethostbyname.py [nombre ...]     (sin dnspython)

Concepto: socket.gethostbyname() y gethostbyname_ex() NO hablan DNS
directamente: llaman a la biblioteca C del sistema (el "resolver" de libc),
que mira primero /etc/hosts y luego pregunta al servidor de /etc/resolv.conf
(el orden lo fija /etc/nsswitch.conf). Es lo que usa socket.connect() cuando
le das un nombre. Limitaciones: solo IPv4 y solo registros A (ni MX ni TXT):
para lo demás hace falta dnspython; para IPv6, getaddrinfo().

La tupla (hostname, aliaslist, ipaddrlist):
  [0] hostname   el nombre CANÓNICO (el final de la cadena de CNAME)
  [1] aliaslist  los alias que se han seguido para llegar a él (los CNAME,
                 incluido el nombre que preguntaste si no era el canónico)
  [2] ipaddrlist TODAS las IPv4 del nombre canónico
"""
import socket
import sys

nombres = sys.argv[1:] or ["apple.com", "www.uniovi.es"]

for nombre in nombres:
    print(f"=== {nombre}")
    print("gethostbyname   :", socket.gethostbyname(nombre), "  <- solo UNA IP")
    canonico, alias, ips = socket.gethostbyname_ex(nombre)
    print("gethostbyname_ex:", (canonico, alias, ips))
    print("  [0] nombre canónico:", canonico)
    print("  [1] alias (CNAME)  :", alias or "ninguno: el nombre ya era el canónico")
    print("  [2] lista de IPv4  :", ips)
    print()
