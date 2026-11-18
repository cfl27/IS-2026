#!/bin/bash
# Ejercicio 3 (sesión 4, apartado 2.2): resolución ITERATIVA "a mano" con dig.
#
# Qué hace: resuelve en.wikipedia.org bajando por el árbol del DNS con
# dig +norecurse, paso a paso, como lo haría un resolvedor recursivo por dentro:
#     raíz (.)  ->  servidores de org  ->  servidores de wikipedia.org  ->  respuesta
# En cada salto imprime a QUÉ IP pregunta, qué servidores le devuelven en
# AUTHORITY (la "referencia" o referral) y qué IP (glue) usa para el siguiente.
# Al final compara la IP con la de `host`. La versión automatizada con
# dnspython es dns_iterativo.py.
#
# Ejecución:   bash dns/dns_iterativo.sh [nombre]      (por defecto en.wikipedia.org)
#
# Concepto:
#   RECURSIVA  el cliente pide "dame la respuesta final" (flag rd = recursion
#              desired) y el servidor hace todo el trabajo. Es lo que hace dig
#              por defecto, y tu navegador con el DNS de tu proveedor.
#   ITERATIVA  (+norecurse: rd=0) el servidor solo dice lo que SABE: si no es
#              autoridad de la respuesta, devuelve una REFERENCIA: "pregunta a
#              estos" (registros NS en la sección AUTHORITY) y, a menudo, sus
#              IP en ADDITIONAL. Es el CLIENTE quien sigue preguntando.
#   GLUE       Los servidores de org son v0n0.pir-ns.org... que están DENTRO de
#              org: para saber su IP habría que preguntar a org, ¡que es lo que
#              queremos hacer! Para romper ese círculo, la zona padre incluye
#              sus A/AAAA en ADDITIONAL: son los "glue records" (pegamento).
#   aa         flag "authoritative answer": solo aparece en la respuesta final,
#              la que da un servidor con autoridad sobre la zona.

NOMBRE="${1:-en.wikipedia.org}"
DIG="dig +norecurse +time=3 +tries=2"

paso() { printf '\n----- Paso %s: %s\n' "$1" "$2"; }

# Primer NS de la sección AUTHORITY de una salida de dig ($1)
primer_ns() { awk '/AUTHORITY SECTION/{f=1;next} f&&/^$/{exit} f&&$4=="NS"{print $5;exit}' <<<"$1"; }
# Lista de NS de AUTHORITY (para mostrarla)
lista_ns()  { awk '/AUTHORITY SECTION/{f=1;next} f&&/^$/{exit} f&&$4=="NS"{printf "%s ",$5}' <<<"$1"; }
# IPv4 de $2 en la sección ADDITIONAL de $1 (el glue), si viene
glue()      { awk -v n="$2" '/ADDITIONAL SECTION/{f=1;next} f&&$1==n&&$4=="A"{print $5;exit}' <<<"$1"; }
# Cabecera (flags) para ver rd/ra/aa en cada salto
flags()     { grep -m1 '^;; flags' <<<"$1"; }

# --------------------------------------------------------------------- Paso 1
# ¿Cuáles son los servidores raíz? Se le pregunta a 8.8.8.8 por el NS de ".".
# OJO: Google no siempre contesta sin recursión (sus "frontends" no comparten
# caché): si viene vacío, se repite CON recursión. Para este paso da igual: solo
# queremos la lista de raíces (que todo resolvedor trae ya en su "root hints").
paso 1 "servidores raíz (pregunta a 8.8.8.8 por '.')"
# grep -v '^;': con +short, los avisos de error de dig empiezan por ";;"
RAIZ_NS=$($DIG @8.8.8.8 . NS +short 2>/dev/null | grep -v '^;' | head -1)
[ -z "$RAIZ_NS" ] && { echo "  (8.8.8.8 no contesta sin recursión: repito con recursión)"
                       RAIZ_NS=$(dig +time=3 +tries=2 @8.8.8.8 . NS +short | grep -v '^;' | sort | head -1); }
# dig devuelve NOMBRES de servidor; hace falta otra consulta para su IP
[ -n "$RAIZ_NS" ] && IP=$(dig +time=3 +tries=2 +short @8.8.8.8 "$RAIZ_NS" A | grep -v '^;' | head -1)
if [ -z "$IP" ]; then
    # Último recurso: la IP de a.root-servers.net, la del fichero "root hints"
    # que todo resolvedor trae de serie (no cambia en años)
    RAIZ_NS=a.root-servers.net.; IP=198.41.0.4
    echo "  (8.8.8.8 no responde: uso la raíz de los root hints)"
fi
echo "  raíz elegida: $RAIZ_NS = $IP"

# ------------------------------------------------------------- Pasos 2, 3, 4
# Se pregunta siempre el nombre COMPLETO (así lo hace un resolvedor real); el
# guion pide "org" y luego "wikipedia.org" y la referencia que se recibe es
# exactamente la misma. Se baja un nivel en cada salto hasta que la respuesta
# traiga ANSWER (o se pase de 6 saltos, por seguridad).
n=2
while [ $n -le 7 ]; do
    paso $n "dig +norecurse @$IP $NOMBRE"
    SALIDA=$($DIG @"$IP" "$NOMBRE")
    flags "$SALIDA" | sed 's/^/  /'
    # ¿Ya hay respuesta? (sección ANSWER presente)
    if grep -q 'ANSWER SECTION' <<<"$SALIDA"; then
        echo "  RESPUESTA (con autoridad: flag aa):"
        awk '/ANSWER SECTION/{f=1;next} f&&/^$/{exit} f{print "    "$0}' <<<"$SALIDA"
        # en.wikipedia.org es un CNAME: el nombre canónico se resuelve igual
        # (aquí al mismo servidor, que también es autoridad de wikimedia.org)
        CNAME=$(awk '/ANSWER SECTION/{f=1;next} f&&$4=="CNAME"{print $5;exit}' <<<"$SALIDA")
        FINAL=$(awk '/ANSWER SECTION/{f=1;next} f&&/^$/{exit} f&&$4=="A"{print $5;exit}' <<<"$SALIDA")
        if [ -z "$FINAL" ] && [ -n "$CNAME" ]; then
            echo "  Es un alias: pregunto al mismo servidor por $CNAME"
            FINAL=$($DIG +short @"$IP" "$CNAME" A | grep -E '^[0-9.]+$' | head -1)
        fi
        break
    fi
    ZONA=$(awk '/AUTHORITY SECTION/{f=1;next} f&&$4=="NS"{print $1;exit}' <<<"$SALIDA")
    NS=$(primer_ns "$SALIDA")
    [ -z "$NS" ] && { echo "  Ni respuesta ni referencia: algo va mal"; echo "$SALIDA"; exit 1; }
    echo "  REFERENCIA: la zona '$ZONA' la sirven: $(lista_ns "$SALIDA")"
    SIG=$(glue "$SALIDA" "$NS")
    if [ -n "$SIG" ]; then
        echo "  elijo $NS; su IP viene en ADDITIONAL (glue): $SIG"
    else
        # Sin glue: el NS está fuera de la zona (p. ej. org -> afilias-nst.info)
        SIG=$(dig +time=3 +short @8.8.8.8 "$NS" A | head -1)
        echo "  elijo $NS; SIN glue: resuelvo su IP aparte -> $SIG"
    fi
    IP=$SIG; n=$((n+1))
done

echo
echo "===== Resultado iterativo: $NOMBRE -> ${FINAL:-?}"
echo "===== Comparación con host (recursivo, servidor del sistema):"
host "$NOMBRE" | sed 's/^/  /'
if [ -n "$FINAL" ] && ! host "$NOMBRE" | grep -q "address $FINAL\$"; then
    echo "  (IP distinta pero correcta: Wikimedia usa GeoDNS, responde según desde"
    echo "   dónde se pregunte; nosotros preguntamos desde esta máquina y host a"
    echo "   través del resolvedor del sistema, que sale a Internet por otro sitio)"
fi
