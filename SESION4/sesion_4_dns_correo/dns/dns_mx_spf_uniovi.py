"""Experimentos MX y SPF (sesión 4, apartado 3.1.4): el correo de uniovi.es en el DNS.

Qué hace:
  1. Muestra los MX de uniovi.es (lo que da `dig uniovi.es MX`).
  2. Busca entre sus registros TXT el de SPF (`dig uniovi.es TXT`), lo
     interpreta mecanismo a mecanismo y lista IPs AUTORIZADAS a enviar correo
     "de" uniovi.es: al menos una de Uniovi (a:relay.uniovi.es, ip4:...) y
     una de Microsoft (siguiendo el include:spf.protection.outlook.com).
  3. Mira si el dominio publica DMARC (_dmarc.uniovi.es).

Ejecución:  ~/dnsenv/bin/python dns/dns_mx_spf_uniovi.py [dominio]

Concepto:
  SMTP no autentica al remitente: cualquiera puede decir "MAIL FROM:
  <alguien@uniovi.es>". Tres mecanismos, todos publicados en el DNS, lo
  mitigan:
  - SPF (Sender Policy Framework, RFC 7208): registro TXT "v=spf1 ..." del
    dominio del REMITENTE DEL SOBRE (el MAIL FROM, no la cabecera From:). El
    MTA que RECIBE comprueba si la IP del MTA que le habla está en la lista:
        mx            las IP de los MX del dominio
        a:host        la IP de ese host        (a:relay.uniovi.es)
        ip4:red/n     una red IPv4 en CIDR      (ip4:156.35.11.151)
        include:dom   "lo que autorice el SPF de dom" (Microsoft 365)
        -all          todo lo demás: FALLO (rechazar). ~all = "softfail".
  - DKIM (RFC 6376): el MTA de origen FIRMA cabeceras y cuerpo con su clave
    privada y añade la cabecera DKIM-Signature (d=dominio, s=selector). La
    clave pública está en un TXT de <selector>._domainkey.<dominio>. A
    diferencia de SPF sí protege el contenido y la cabecera From:, y
    sobrevive a reenvíos.
  - DMARC (RFC 7489): TXT en _dmarc.<dominio> que dice qué hacer si SPF/DKIM
    fallan o no "alinean" con el From: visible (p=none/quarantine/reject) y
    a dónde mandar informes.
"""
import ipaddress
import sys

import dns.resolver

dominio = sys.argv[1] if len(sys.argv) > 1 else "uniovi.es"


def txt(nombre):
    """Lista de cadenas TXT de un nombre (cada registro puede venir troceado
    en varias cadenas de 255 bytes: se juntan)."""
    try:
        return [b"".join(r.strings).decode() for r in dns.resolver.resolve(nombre, "TXT")]
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
        return []


def spf_de(nombre):
    """El registro SPF (el TXT que empieza por v=spf1) o None."""
    return next((t for t in txt(nombre) if t.startswith("v=spf1")), None)


def ips_a(host):
    return [r.address for r in dns.resolver.resolve(host, "A")]


def primera_ip_de_include(nombre, profundidad=0):
    """Sigue los include: hasta encontrar un ip4: (Microsoft anida varios)."""
    spf = spf_de(nombre) or ""
    print(f"      {'  ' * profundidad}{nombre}: {spf}")
    for mec in spf.split()[1:]:
        if mec.startswith("ip4:"):
            return mec[4:]
    for mec in spf.split()[1:]:
        if mec.startswith("include:") and profundidad < 4:
            ip = primera_ip_de_include(mec[8:], profundidad + 1)
            if ip:
                return ip
    return None


# ---------------------------------------------------------------- 1. MX
print(f"=== MX de {dominio} (menor preference = más prioritario)")
for r in sorted(dns.resolver.resolve(dominio, "MX"), key=lambda r: r.preference):
    print(f"  {r.preference:<3} {r.exchange}  {ips_a(r.exchange)}")

# ---------------------------------------------------------------- 2. SPF
print(f"\n=== Registros TXT de {dominio}")
for t in txt(dominio):
    print("  ", t[:100] + ("..." if len(t) > 100 else ""))
spf = spf_de(dominio)
if not spf:
    sys.exit(f"{dominio} no publica SPF")

print(f"\n=== Interpretación del SPF\n  {spf}")
autorizadas = []          # (ip o red, de dónde sale)
for mec in spf.split()[1:]:          # el primero es "v=spf1"
    if mec == "mx":
        print("  mx                      -> pueden enviar los propios MX")
        for r in dns.resolver.resolve(dominio, "MX"):
            autorizadas += [(ip, f"MX {r.exchange}") for ip in ips_a(r.exchange)]
    elif mec.startswith("a:"):
        host = mec[2:]
        print(f"  {mec:<23} -> puede enviar la máquina {host}")
        autorizadas += [(ip, f"a:{host}") for ip in ips_a(host)]
    elif mec.startswith("ip4:"):
        red = ipaddress.ip_network(mec[4:], strict=False)
        print(f"  {mec:<23} -> la red {red} ({red.num_addresses} dirección/es)")
        autorizadas.append((str(red), "ip4"))
    elif mec.startswith("include:"):
        print(f"  {mec:<23} -> lo que autorice el SPF de {mec[8:]} (lo sigo):")
        ip = primera_ip_de_include(mec[8:])
        if ip:
            autorizadas.append((ip, f"{mec} (Microsoft 365)"))
    elif mec.endswith("all"):
        significado = {"-": "FALLO: rechazar", "~": "softfail: marcar como sospechoso",
                       "?": "neutral", "+": "aceptar todo (¡inútil!)"}
        print(f"  {mec:<23} -> cualquier otra IP: {significado.get(mec[0], 'aceptar')}")

print("\n=== Algunas IPs/redes autorizadas a enviar correo de", dominio)
for ip, origen in autorizadas:
    print(f"  {ip:<22} ({origen})")

# ---------------------------------------------------------------- 3. DMARC
print(f"\n=== DMARC (_dmarc.{dominio})")
print("  ", next((t for t in txt(f"_dmarc.{dominio}") if t.startswith("v=DMARC1")),
               "no publicado"))
print("DKIM: la clave pública está en <selector>._domainkey."
      f"{dominio}; el selector solo se conoce leyendo\n"
      "la cabecera DKIM-Signature (s=...) de un correo recibido de ese dominio.")
