"""Ejercicio 3, versión automática (sesión 4, apartado 2.2): resolvedor ITERATIVO.

Qué hace: resuelve un nombre (por defecto en.wikipedia.org) sin pedir NUNCA
recursión a nadie: empieza en un servidor raíz y sigue las referencias
(referrals) zona a zona, imprimiendo en cada salto a quién pregunta, qué
referencia recibe y qué servidor elige. Si la respuesta es un CNAME, vuelve a
empezar desde la raíz con el nombre canónico. Al final compara con el
resolvedor del sistema (lo mismo que hace `host`).

Ejecución (necesita dnspython: ver README):
    ~/dnsenv/bin/python dns/dns_iterativo.py [nombre]

Concepto: es lo que hace POR DENTRO un servidor recursivo (el 8.8.8.8 o el de
tu proveedor) cuando no tiene la respuesta en caché:
  1. Pregunta a una raíz. La raíz no sabe la IP, pero sabe quién lleva "org":
     respuesta SIN sección ANSWER, con registros NS en AUTHORITY (la
     referencia) y sus IP en ADDITIONAL (los "glue records").
  2. Pregunta a uno de esos servidores, que remite a los de "wikipedia.org".
  3. Estos son AUTORIDAD (flag aa): contestan en ANSWER.
Si un NS de la referencia no trae glue (porque su nombre está en otra zona,
p. ej. a2.org.afilias-nst.info), hay que resolver ANTES su IP: el programa se
llama a sí mismo (resolución recursiva *dentro* del cliente iterativo).
"""
import socket
import sys

import dns.exception
import dns.flags
import dns.message
import dns.query
import dns.rdatatype

# Algunas raíces con su IP fija: todo resolvedor las trae de serie en su
# fichero "root hints" (hay 13 nombres, a..m.root-servers.net, cada uno
# replicado en cientos de sitios con anycast)
RAICES = [("a.root-servers.net", "198.41.0.4"), ("f.root-servers.net", "192.5.5.241"),
          ("k.root-servers.net", "193.0.14.129"), ("m.root-servers.net", "202.12.27.33")]
MAX_SALTOS = 10


def preguntar(nombre, ip):
    """Envía UNA consulta tipo A, sin recursión, a la IP dada (UDP, puerto 53)."""
    consulta = dns.message.make_query(nombre, dns.rdatatype.A)
    # make_query activa por defecto el bit RD ("recursion desired"): se quita
    # para que el servidor solo responda con lo que sabe (consulta iterativa)
    consulta.flags &= ~dns.flags.RD
    # EDNS (payload 1232) permite respuestas UDP de más de 512 bytes (las
    # referencias con muchos glue lo superan). Si aun así llega truncada (flag
    # TC), udp_with_fallback repite la consulta por TCP, como manda el RFC.
    consulta.use_edns(0, payload=1232)
    respuesta, _por_tcp = dns.query.udp_with_fallback(consulta, ip, timeout=3)
    return respuesta


def resolver_iterativo(nombre, sangria=""):
    """Devuelve la lista de IPv4 de `nombre` recorriendo el árbol desde la raíz."""
    # Servidores a los que se puede preguntar en este nivel: si uno no
    # responde se pasa al siguiente (para eso una zona tiene VARIOS NS)
    candidatos = list(RAICES)
    for salto in range(1, MAX_SALTOS + 1):
        r = None
        while candidatos and r is None:
            servidor, ip = candidatos.pop(0)
            print(f"{sangria}[{salto}] pregunto a {servidor} ({ip}) por {nombre}")
            try:
                r = preguntar(nombre, ip)
            except dns.exception.Timeout:
                print(f"{sangria}    no responde: pruebo con otro servidor de la zona")
        if r is None:
            raise dns.exception.Timeout()
        print(f"{sangria}    flags: {dns.flags.to_text(r.flags)}")

        # --- ¿Respuesta? (sección ANSWER no vacía)
        if r.answer:
            ips, cname = [], None
            for rrset in r.answer:
                print(f"{sangria}    ANSWER: {rrset.to_text()}")
                if rrset.rdtype == dns.rdatatype.A:
                    ips += [rd.address for rd in rrset]
                elif rrset.rdtype == dns.rdatatype.CNAME:
                    cname = rrset[0].target.to_text()
            if ips:
                return ips
            # Solo un alias: el nombre canónico puede estar en otra zona, así
            # que se empieza de nuevo desde la raíz
            print(f"{sangria}    es un alias (CNAME) de {cname}: vuelvo a la raíz")
            return resolver_iterativo(cname, sangria)

        # --- Referencia: NS de la zona hija en AUTHORITY
        ns_rrsets = [x for x in r.authority if x.rdtype == dns.rdatatype.NS]
        if not ns_rrsets:
            sys.exit(f"{sangria}    ni respuesta ni referencia (¿NXDOMAIN?): {r.rcode()}")
        zona = ns_rrsets[0].name.to_text()
        nombres_ns = [rd.target.to_text() for rd in ns_rrsets[0]]
        print(f"{sangria}    REFERENCIA: la zona '{zona}' la llevan {', '.join(nombres_ns)}")

        # Glue: A de esos NS en ADDITIONAL
        glue = {x.name.to_text(): x[0].address for x in r.additional
                if x.rdtype == dns.rdatatype.A}
        con_glue = [n for n in nombres_ns if n in glue]
        if con_glue:
            candidatos = [(n, glue[n]) for n in con_glue]
            print(f"{sangria}    elijo {con_glue[0]}: IP {glue[con_glue[0]]} sacada del glue (ADDITIONAL)")
        else:
            servidor = nombres_ns[0]
            print(f"{sangria}    {servidor} viene SIN glue: lo resuelvo primero")
            ip = resolver_iterativo(servidor, sangria + "      ")[0]
            candidatos = [(servidor, ip)]
            print(f"{sangria}    elijo {servidor}: IP {ip}")
    sys.exit("Demasiados saltos")


if __name__ == "__main__":
    nombre = sys.argv[1] if len(sys.argv) > 1 else "en.wikipedia.org"
    try:
        ips = resolver_iterativo(nombre)
    except dns.exception.Timeout:
        sys.exit("Un servidor no respondió (¿hay red? ¿bloqueado el puerto 53/UDP?)")
    print(f"\nResultado iterativo: {nombre} -> {', '.join(ips)}")
    # Comparación con el resolvedor del sistema (recursivo, el de host)
    sistema = socket.gethostbyname_ex(nombre)[2]
    print(f"Resolvedor del sistema: {nombre} -> {sistema}")
    if not set(ips) & set(sistema):
        # No es un error: los grandes sitios usan GeoDNS / CDN y el servidor
        # autoritativo responde según la IP de QUIÉN pregunta (aquí, esta
        # máquina; en el otro caso, el resolvedor recursivo del sistema)
        print("(IPs distintas pero correctas: el autoritativo responde según el origen"
              " de la consulta, GeoDNS)")
