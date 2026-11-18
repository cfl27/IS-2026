"""Ejercicio 5 (sesión 4, apartado 2.3.1): todas las IP de apple.com.

Qué hace: pide los registros A de un dominio (apple.com por defecto) y los
muestra todos, recorriendo la respuesta como si fuera una lista.

Ejecución:  ~/dnsenv/bin/python dns/dns_ips_apple.py [dominio]

Concepto: un nombre puede tener VARIOS registros A (un "RRset"). Es la forma
más simple de repartir carga y de tener redundancia: cada cliente prueba la
primera y el servidor DNS va rotando el orden (round-robin). Por eso
gethostbyname(), que devuelve una sola IP, se queda corto (ver
dns_gethostbyname.py). El número de IP que veas depende de desde dónde
preguntes: los grandes dominios responden según la ubicación (CDN).
"""
import sys

import dns.resolver

dominio = sys.argv[1] if len(sys.argv) > 1 else "apple.com"

respuesta = dns.resolver.resolve(dominio, "A")
print(f"{dominio}: {len(respuesta)} IP (TTL {respuesta.rrset.ttl} s)")
for registro in respuesta:          # cada elemento es un rdata de tipo A
    print("  ", registro.address)
