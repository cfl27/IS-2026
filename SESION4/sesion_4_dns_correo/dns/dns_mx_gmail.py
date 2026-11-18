"""Ejercicio 10 (sesión 4, apartado 3.1.4): servidores de correo de gmail.com.

Qué hace: consulta los registros MX del dominio (gmail.com por defecto), los
ordena por prioridad y resuelve la IP de cada servidor. Formato del guion:
    5  gmail-smtp-in.l.google.com.      108.177.119.27
    10 alt1.gmail-smtp-in.l.google.com. 74.125.130.27

Ejecución:  ~/dnsenv/bin/python dns/dns_mx_gmail.py [dominio]

Concepto: así encuentra un MTA (servidor de correo) a quién entregar un
mensaje para usuario@gmail.com: mira el DNS, no "gmail.com" directamente.
Cada MX tiene dos campos:
  preference  número de prioridad: MENOR = más preferido. Con empate se
              elige al azar (reparto de carga). Si el primero no responde se
              prueba el siguiente; si no responde ninguno, se reintenta más
              tarde (las colas de un MTA guardan el mensaje unos 5 días).
  exchange    NOMBRE de la máquina (nunca una IP): hace falta otra consulta
              A para conocer su dirección.
(El guion usa dns.resolver.query, obsoleto en dnspython 2.x: ver dns_ej1.py.)
"""
import sys

import dns.resolver

dominio = sys.argv[1] if len(sys.argv) > 1 else "gmail.com"

mx = dns.resolver.resolve(dominio, "MX")
# Ordenar por prioridad (el servidor DNS no garantiza ningún orden)
registros = sorted(mx, key=lambda r: r.preference)

ancho = max(len(r.exchange.to_text()) for r in registros)
for r in registros:
    nombre = r.exchange.to_text()
    # Segunda consulta: el registro A del exchange
    ip = dns.resolver.resolve(r.exchange, "A")[0].address
    print(f"{r.preference:<2} {nombre:<{ancho}} {ip}")
