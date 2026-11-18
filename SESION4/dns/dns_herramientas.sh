#!/bin/bash
# Ejercicios 1 y 2 (sesión 4, apartado 2.1): host, dig y nslookup.
#
# Qué hace: resuelve www.uniovi.es, en.wikipedia.org y es.wikipedia.org con las
# tres herramientas y contra varios servidores de nombres, cada salida con un
# título, para poder compararlas (las respuestas a las preguntas del guion
# están en el README, apartado "Respuestas").
#
# Ejecución:   bash dns/dns_herramientas.sh            (todo)
#              bash dns/dns_herramientas.sh | less     (para leerlo con calma)
#
# Concepto:
#   - host     una línea por registro: lo más CONCISO (para personas).
#   - dig      muestra el mensaje DNS por SECCIONES (cabecera con id y flags,
#              QUESTION, ANSWER, AUTHORITY, ADDITIONAL): lo más cercano al
#              PROTOCOLO, por eso es la herramienta de diagnóstico.
#   - nslookup la histórica (obsoleta), formato intermedio.
#   - Ej. 2: "@servidor" (dig), segundo argumento (host / nslookup) = a QUIÉN se
#     pregunta. Sin él se usa el de /etc/resolv.conf (en WSL, 10.255.255.254:
#     un reenviador que Windows pone delante de su propio DNS).
#   - El punto final ("www.uniovi.es.") hace el nombre ABSOLUTO: así el
#     resolvedor no le añade los dominios de búsqueda de "search" en resolv.conf.

# +time/+tries: no esperar 15 s si un servidor no contesta (156.35.41.4 rechaza
# o ignora consultas recursivas desde fuera de la red de Uniovi)
DIG_OPC="+time=3 +tries=1"

titulo() { printf '\n==================== %s ====================\n' "$*"; }

# Servidores a comparar: el del sistema, el público de Google y el de Uniovi
SISTEMA=$(awk '/^nameserver/{print $2; exit}' /etc/resolv.conf)
SERVIDORES="$SISTEMA 8.8.8.8 156.35.41.4"

# ---------------------------------------------------------------- Ejercicio 1
for nombre in www.uniovi.es. en.wikipedia.org.; do
    titulo "host $nombre"
    host "$nombre"
    titulo "nslookup $nombre"
    nslookup "$nombre"
    titulo "dig $nombre   (mensaje completo, por secciones)"
    dig $DIG_OPC "$nombre"
done

# en y es de Wikipedia: alias (CNAME) distintos que llevan al MISMO nombre
# canónico (dyna.wikimedia.org) y, por tanto, a la misma IP.
titulo "en.wikipedia.org frente a es.wikipedia.org (solo respuesta)"
for nombre in en.wikipedia.org. es.wikipedia.org.; do
    echo "--- $nombre"; dig $DIG_OPC +noall +answer "$nombre"
done

# ---------------------------------------------------------------- Ejercicio 2
for srv in $SERVIDORES; do
    titulo "dig @$srv www.uniovi.es"
    # Con +noall +answer +comments se ve la cabecera (status, flags) y la
    # respuesta sin el resto: lo justo para comparar servidores
    if ! dig $DIG_OPC +noall +comments +answer @"$srv" www.uniovi.es.; then
        echo "(sin respuesta de $srv: normal si es 156.35.41.4 y estás fuera de Uniovi)"
    fi
    titulo "host www.uniovi.es $srv"
    host -W 3 www.uniovi.es. "$srv" || echo "(sin respuesta de $srv)"
done
