"""Experimento getaddrinfo (sesión 4, apartado 2.4, opcional).

Qué hace: imprime socket.getaddrinfo("en.wikipedia.org", "www") tal cual
(como pide el guion) y después desgrana cada elemento de la lista.

Ejecución:  python3 dns/dns_getaddrinfo_experimento.py [nombre] [servicio]

Concepto: getaddrinfo() es la API POSIX MODERNA, independiente del protocolo:
tú das NOMBRE de máquina y NOMBRE de servicio ("www", "http", "ssh"... se
traducen a puerto con /etc/services) y te devuelve una LISTA con todas las
formas posibles de conectar. Cada elemento es una tupla de 5:
  familia    AF_INET (IPv4) o AF_INET6 (IPv6)          \\
  tipo       SOCK_STREAM (TCP), SOCK_DGRAM (UDP)...      > los 3 argumentos
  proto      6 = IPPROTO_TCP, 17 = IPPROTO_UDP         /  de socket()
  canonname  nombre canónico: vacío salvo que se pida con AI_CANONNAME
  sockaddr   lo que se pasa a connect(): (IP, puerto) en IPv4 y
             (IP, puerto, flowinfo, scope_id) en IPv6
Sin filtros salen combinaciones de familia x tipo (TCP, UDP, RAW): por eso
la lista es larga. El código "bueno" las prueba en orden hasta que una
conecta (lo que hace socket.create_connection()).
"""
import socket
import sys

nombre = sys.argv[1] if len(sys.argv) > 1 else "en.wikipedia.org"
servicio = sys.argv[2] if len(sys.argv) > 2 else "www"

lista = socket.getaddrinfo(nombre, servicio)
print("Tal cual:", lista)
print(f"\n{len(lista)} elementos (formas distintas de conectar):")
for i, (familia, tipo, proto, canonname, sockaddr) in enumerate(lista):
    print(f"[{i}] familia={familia.name:<9} tipo={tipo.name:<11} "
          f"proto={proto:<2} canonname={canonname!r:<4} sockaddr={sockaddr}")

# Con AI_CANONNAME el primer elemento trae el nombre canónico (el CNAME final)
canon = socket.getaddrinfo(nombre, servicio, type=socket.SOCK_STREAM,
                           flags=socket.AI_CANONNAME)[0][3]
print(f"\nCon AI_CANONNAME: canonname = {canon!r}")
print("proto 6 es IPPROTO_TCP:", socket.IPPROTO_TCP == 6)
