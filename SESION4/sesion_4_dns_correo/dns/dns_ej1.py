"""Ejercicio 4 (sesión 4, apartado 2.3.1): primera consulta con dnspython.

Qué hace: pregunta el registro A de en.wikipedia.org y lo muestra de tres
formas: (1) solo la IP, (2) el mensaje de respuesta completo en texto (lo
mismo que enseña dig) y (3) ese mismo mensaje en BINARIO, tal y como viaja
por la red dentro del datagrama UDP.

Ejecución:  ~/dnsenv/bin/python dns/dns_ej1.py [nombre]

Concepto: el protocolo DNS es BINARIO (RFC 1035): cabecera de 12 bytes (id,
flags, 4 contadores) y luego las secciones, con los nombres codificados como
"etiquetas" (longitud + texto: b'\\x02en\\x09wikipedia\\x03org\\x00') y
comprimidos con punteros (bytes 0xC0..). dnspython lo encapsula: nosotros
manejamos objetos y él construye y analiza los bytes.

Nota sobre el guion: usa dns.resolver.query(), que en dnspython 2.x está
OBSOLETO (lanza DeprecationWarning). Su sustituto es dns.resolver.resolve():
misma idea, pero por defecto NO añade los dominios de búsqueda de
/etc/resolv.conf (search_domains=False), que con query() producía consultas
inesperadas a "nombre.midominio.local".
"""
import sys

import dns.resolver

nombre = sys.argv[1] if len(sys.argv) > 1 else "en.wikipedia.org"

# resolve() usa el servidor de /etc/resolv.conf y pide RECURSIÓN (rd=1).
# Si el nombre es un CNAME, la respuesta trae la cadena de alias y resolve()
# entrega directamente los registros A del nombre canónico.
respuesta = dns.resolver.resolve(nombre)   # tipo "A" por defecto

# (1) El objeto Answer se comporta como una lista de registros (rdata)
print("IP:", respuesta[0].address)

# (2) .response es el dns.message.Message recibido: su str() es el formato de
#     dig (id, opcode, rcode, flags y secciones QUESTION/ANSWER/AUTHORITY...)
print("\n--- Respuesta del servidor en texto")
print(respuesta.response)

# (3) to_wire() lo vuelve a convertir a los bytes del protocolo
binario = respuesta.response.to_wire()
print(f"\n--- Mismo mensaje en binario ({len(binario)} bytes)")
print(binario)
# Los 2 primeros bytes son el id de la consulta (UDP no tiene conexiones:
# el id sirve para casar cada respuesta con su pregunta)
print("id (2 primeros bytes):", int.from_bytes(binario[:2], "big"),
      "=", respuesta.response.id)
