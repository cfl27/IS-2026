#!/bin/bash
# Prueba automática de la sesión 4 (DNS y correo). Sin sudo y sin cuentas reales.
# Uso:  bash ./probar_sesion4.sh
#
# Qué comprueba:
#   [Sintaxis]   todos los .py compilan y todos los .sh pasan bash -n.
#   [Mensajes]   la biblioteca email: cabeceras, tildes (RFC 2047, QP, base64), adjunto.
#   [SMTP]       los 4 clientes contra los SIMULADORES (simuladores/), mirando lo
#                que llega al buzón: cabeceras, sobre, tildes, adjunto, TLS, AUTH.
#   [POP3]       los 4 clientes y la máquina de estados (STAT, LIST, TOP, DELE,
#                RSET, QUIT/UPDATE, bloqueo del buzón).
#   [Errores]    clave incorrecta, sin AUTH, certificado no fiable, puerto cerrado:
#                el script debe fallar CON UN MENSAJE CLARO (y sin traceback).
#   [DNS]        dig/host/dnspython contra 8.8.8.8 y los servidores raíz (necesita
#                Internet: sin red, o si un servidor no responde, se marca OMITIDO).
# Lo que necesita servidores reales (relay.uniovi.es, Gmail) no se prueba aquí:
# ver "Pasos manuales" en el README.
#
# Cómo funciona:
#   - "check <descripción> <orden>": OK si la orden termina con código 0; si no,
#     FALLO y se muestran las primeras líneas de su salida.
#   - Los simuladores se lanzan en puertos de prueba (12525/15587/15995) para no
#     chocar con unos lanzados a mano, con una clave aleatoria, y todo va a un
#     directorio temporal que trap ... EXIT borra (y para los simuladores)
#     aunque la prueba se interrumpa.
cd "$(dirname "$0")" || exit 1
DIR="$PWD"
export PYTHONDONTWRITEBYTECODE=1          # no dejar __pycache__ en el repositorio
PY_DNS=~/dnsenv/bin/python                # Python con dnspython
T=$(mktemp -d /tmp/is_s4_pruebas.XXXXXX)
SIM="$T/sim"; BUZON="$SIM/buzon"
ok=0; fallo=0; omitido=0

check() { # descripción, comando...
    local d="$1"; shift
    if "$@" >"$T/out.txt" 2>&1; then echo "  OK       $d"; ok=$((ok+1))
    else echo "  FALLO    $d"; sed 's/^/           | /' "$T/out.txt" | head -8; fallo=$((fallo+1)); fi
}
omitir() { echo "  OMITIDO  $1"; omitido=$((omitido+1)); }
# Último mensaje del buzón (los nombres empiezan por la hora en ms: ordenan)
ultimo() { ls "$BUZON"/*.eml 2>/dev/null | sort | tail -1; }
num_buzon() { ls "$BUZON"/*.eml 2>/dev/null | wc -l; }
decodificar() { python3 correo/mensajes/email_decodificar.py "$(ultimo)"; }

LANZADOR=""
limpiar() {
    [ -n "$LANZADOR" ] && kill "$LANZADOR" 2>/dev/null && wait "$LANZADOR" 2>/dev/null
    rm -rf "$T"
}
trap limpiar EXIT

# ------------------------------------------------------------------ Requisitos
command -v openssl >/dev/null || { echo "Falta openssl"; exit 1; }
if [ ! -x "$PY_DNS" ] || ! "$PY_DNS" -c "import dns.resolver" 2>/dev/null; then
    echo "(creando ~/dnsenv con dnspython...)"
    python3 -m venv ~/dnsenv >/dev/null 2>&1 && ~/dnsenv/bin/pip install -q dnspython >/dev/null 2>&1
fi
HAY_DNSPYTHON=0; "$PY_DNS" -c "import dns.resolver" 2>/dev/null && HAY_DNSPYTHON=1

echo "[Sintaxis]"
# compile() en memoria: comprueba la sintaxis SIN escribir .pyc (py_compile sí los escribe)
check "todos los .py compilan" python3 -c '
import sys
for f in sys.argv[1:]:
    compile(open(f, encoding="utf-8").read(), f, "exec")' $(find . -name '*.py')
check "todos los .sh pasan bash -n" bash -c 'for f in $(find . -name "*.sh"); do bash -n "$f" || exit 1; done'

echo "[Mensajes RFC 5322 (biblioteca email)]"
M=correo/mensajes/email_crear_mensaje_prueba.py
check "código del guion: añade MIME-Version y Content-Type" bash -c "python3 $M | grep -q '^MIME-Version: 1.0' && python3 $M | grep -q '^Content-Type: text/plain'"
check "el mensaje NO lleva el punto final"   bash -c "! python3 $M | grep -qx '\.'"
check "tildes en cabeceras -> RFC 2047 (=?utf-8?...?=)" bash -c "python3 $M --tildes | grep -q '^To: =?utf-8?q?D=C3=A9sti'"
check "tildes en el cuerpo: 8bit, quoted-printable y base64" bash -c "python3 $M --tildes > $T/t.txt; grep -q 'canci=C3=B3n' $T/t.txt && grep -q 'Transfer-Encoding: base64' $T/t.txt && grep -q 'Transfer-Encoding: 8bit' $T/t.txt"
check "el asunto codificado se decodifica bien" bash -c "python3 $M --tildes | grep -q 'Decodificado: Prueba con tildes: ¿qué tal, Ñandú?'"
check "adjunto (ej. 9): multipart/mixed + image/gif en base64" bash -c "IS_SIN_RED=1 python3 $M --adjunto --guardar $T/adj.eml | grep -q 'image/gif   codificada en base64  nombre=atc.gif' && grep -q 'multipart/mixed; boundary=' $T/adj.eml"
check "email_decodificar.py reconoce el adjunto" bash -c "python3 correo/mensajes/email_decodificar.py $T/adj.eml | grep -q 'ADJUNTO filename=atc.gif'"

# ------------------------------------------------------------------ Simuladores
export IS_SIM_USER="alumno@example.com" IS_SIM_PASS="$(openssl rand -hex 8)"
export IS_SIM_PUERTO_RELAY=12525 IS_SIM_PUERTO_SUB=15587 IS_SIM_PUERTO_POP=15995
bash simuladores/lanzar_simuladores.sh "$SIM" >"$T/lanzador.log" 2>&1 &
LANZADOR=$!
for _ in $(seq 50); do [ -f "$SIM/entorno.sh" ] && break; sleep 0.1; done
if [ ! -f "$SIM/entorno.sh" ]; then
    echo "No arrancan los simuladores:"; cat "$T/lanzador.log"; exit 1
fi
# shellcheck disable=SC1091
source "$SIM/entorno.sh"            # SSL_CERT_FILE, IS_SMTP_*, IS_POP_*, IS_USER/PASS...
RELAY="IS_SMTP_PORT=$IS_SIM_PUERTO_RELAY"
export IS_SIN_RED=1                 # el adjunto no se descarga: GIF generado

echo "[SMTP contra los simuladores]"
check "ej. 7 crudo (HELO/MAIL/RCPT/DATA/QUIT) contra el relay" bash -c "env $RELAY timeout 20 python3 correo/smtp/email_envia_crudo.py | grep -q 'Mensaje enviado'"
check "  el buzón guarda el sobre (Return-Path) y la traza Received" bash -c "grep -q '^Return-Path: <alumno@example.com>' \"\$(ls $BUZON/*.eml | sort | tail -1)\" && grep -q '^Received: from ' \"\$(ls $BUZON/*.eml | sort | tail -1)\""
check "  y el Subject de la plantilla" bash -c "grep -q '^Subject: Prueba SMTP en crudo' \"\$(ls $BUZON/*.eml | sort | tail -1)\""
check "ej. 7 con dos destinatarios (dos RCPT TO)" bash -c "env $RELAY IS_TO='uno@example.com,dos@example.com' timeout 20 python3 correo/smtp/email_envia_crudo.py | grep -c 'RCPT TO' | grep -qx 2 && grep -q '^Delivered-To: uno@example.com, dos@example.com' \"\$(ls $BUZON/*.eml | sort | tail -1)\""
check "ej. 8 mensaje RFC 5322 (Date, Message-ID, MIME)" bash -c "env $RELAY timeout 20 python3 correo/smtp/email_envia_crudo_rfc5322.py >/dev/null && f=\$(ls $BUZON/*.eml | sort | tail -1) && grep -q '^Message-ID: <' \$f && grep -q '^Date: ' \$f && grep -q '^MIME-Version: 1.0' \$f"
check "ej. 8 con tildes: asunto en RFC 2047, decodificado correcto" bash -c "env $RELAY timeout 20 python3 correo/smtp/email_envia_crudo_rfc5322.py --tildes >/dev/null && grep -q '^Subject: .*=?utf-8?' \"\$(ls $BUZON/*.eml | sort | tail -1)\" && python3 correo/mensajes/email_decodificar.py \"\$(ls $BUZON/*.eml | sort | tail -1)\" | grep -q -- '-> Prueba con tildes: ¿qué tal, Ñandú?'"
check "ej. 9 adjunto llega como multipart/mixed con atc.gif" bash -c "env $RELAY timeout 20 python3 correo/smtp/email_envia_crudo_rfc5322.py --adjunto >/dev/null && python3 correo/mensajes/email_decodificar.py \"\$(ls $BUZON/*.eml | sort | tail -1)\" | grep -q 'image/gif  \[cte base64\]  ADJUNTO filename=atc.gif'"
check "ej. 11 STARTTLS + AUTH LOGIN (334/334/235)" bash -c "timeout 20 python3 correo/smtp/email_envia_crudo_ssl.py > $T/e11.txt && grep -q 'canal cifrado: TLS' $T/e11.txt && grep -q '^S: 235' $T/e11.txt && [ \$(grep -c '^S: 334' $T/e11.txt) = 2 ]"
check "  el 334 decodificado pide 'Username:'" grep -q 'trae en base64: Username:' "$T/e11.txt"
check "  la contraseña no aparece en pantalla" bash -c "! grep -q \"\$IS_PASS\" $T/e11.txt"
check "  el servidor lo registra como ESMTPSA (TLS + autenticado)" bash -c "grep -q 'with ESMTPSA' \"\$(ls $BUZON/*.eml | sort | tail -1)\""
check "ej. 12 smtplib: starttls + login + sendmail" bash -c "timeout 20 python3 correo/smtp/email_smtplib.py > $T/e12.txt 2>&1 && grep -q 'STARTTLS' $T/e12.txt && grep -q 'Mensaje enviado con smtplib' $T/e12.txt && grep -q '^Subject: Prueba con smtplib' \"\$(ls $BUZON/*.eml | sort | tail -1)\""

echo "[POP3 contra el simulador (TLS implícito)]"
N=$(num_buzon)
check "ej. 13 crudo: STAT da $N mensajes y extrae Subject/From" bash -c "timeout 20 python3 correo/pop3/email_pop3_recibe_crudo.py > $T/e13.txt && grep -q '^S: +OK $N ' $T/e13.txt && grep -q 'Subject: Prueba SMTP en crudo' $T/e13.txt && grep -q 'From:    alumno@example.com' $T/e13.txt"
check "ej. 14 crudo: Subject de los $N mensajes" bash -c "[ \$(timeout 20 python3 correo/pop3/email_pop3_recibe_crudo2.py | grep -c '  Subject:') = $N ]"
check "ej. 15 poplib: retr() devuelve una tupla de 3" bash -c "timeout 20 python3 correo/pop3/email_pop3_poplib.py > $T/e15.txt 2>&1 && grep -q 'retr(1) devuelve una tupla de 3 elementos' $T/e15.txt && grep -q \"\\*cmd\\* 'STAT'\" $T/e15.txt"
check "  la clave no sale en el debug de poplib" bash -c "! grep -q \"\$IS_PASS\" $T/e15.txt"
check "ej. 16 resumen (función del guion): tildes y multipart" bash -c "timeout 20 python3 correo/pop3/email_pop3_poplib2.py > $T/e16.txt && grep -q 'Subject: Prueba con tildes: ¿qué tal, Ñandú?' $T/e16.txt && grep -q -- '---Multipart. Parte 1' $T/e16.txt && [ \$(grep -c '^Subject:' $T/e16.txt) = $N ]"
check "ej. 16 --mejorada: lista el adjunto atc.gif" bash -c "timeout 20 python3 correo/pop3/email_pop3_poplib2.py --mejorada | grep -q -- '---Adjuntos: atc.gif'"
# Máquina de estados: DELE solo marca; RSET desmarca; el borrado es en UPDATE (QUIT)
cat >"$T/estados.py" <<'EOF'
import os, poplib, ssl, sys
def abrir():
    p = poplib.POP3_SSL("localhost", int(os.environ["IS_POP_PORT"]), context=ssl.create_default_context())
    p.user(os.environ["IS_USER"]); p.pass_(os.environ["IS_PASS"]); return p
p = abrir(); n = p.stat()[0]
assert len(p.list()[1]) == n, "LIST no da una línea por mensaje"
cab = p.top(1, 0)[1]
assert cab[-1] == b"" and any(l.startswith(b"Subject:") for l in cab), "TOP 1 0 no da solo cabeceras"
p.dele(1); assert p.stat()[0] == n - 1, "DELE no descuenta en STAT"
try: p.retr(1); sys.exit("RETR de un mensaje marcado debería dar -ERR")
except poplib.error_proto: pass
p.rset(); assert p.stat()[0] == n, "RSET no desmarca"
try: abrir(); sys.exit("dos sesiones a la vez: el buzón debería estar bloqueado")
except poplib.error_proto as e: assert b"IN-USE" in e.args[0]
p.dele(1); p.close()               # cortar SIN QUIT: no se debe borrar nada
import time
for _ in range(20):                # esperar a que el servidor note el corte
    try: p = abrir(); break
    except poplib.error_proto: time.sleep(0.2)
assert p.stat()[0] == n, "sin QUIT se ha borrado algo"
p.dele(1); p.quit()                # con QUIT -> UPDATE: ahora sí
p = abrir(); assert p.stat()[0] == n - 1, "QUIT no ha borrado el marcado"; p.quit()
print("estados OK")
EOF
check "POP3: LIST, TOP, DELE/RSET, bloqueo, UPDATE solo con QUIT" python3 "$T/estados.py"

echo "[Errores con mensaje claro]"
check "ej. 11 con clave mala -> 535 y pista de contraseña de aplicación" bash -c "! IS_PASS=mala timeout 20 python3 correo/smtp/email_envia_crudo_ssl.py > $T/x.txt 2>&1 && grep -q '535' $T/x.txt && grep -q 'contraseña de APLICACIÓN' $T/x.txt && ! grep -q Traceback $T/x.txt"
check "ej. 12 con clave mala -> SMTPAuthenticationError explicado" bash -c "! IS_PASS=mala timeout 20 python3 correo/smtp/email_smtplib.py > $T/x.txt 2>&1 && grep -q 'ERROR 535' $T/x.txt && ! grep -q Traceback $T/x.txt"
check "ej. 13 con clave mala -> -ERR explicado" bash -c "! IS_PASS=mala timeout 20 python3 correo/pop3/email_pop3_recibe_crudo.py > $T/x.txt 2>&1 && grep -q 'incorrectos' $T/x.txt"
check "ej. 15 con clave mala -> error_proto explicado" bash -c "! IS_PASS=mala timeout 20 python3 correo/pop3/email_pop3_poplib.py > $T/x.txt 2>&1 && grep -q 'ERROR POP3: -ERR \[AUTH\]' $T/x.txt && ! grep -q Traceback $T/x.txt"
check "MAIL FROM sin AUTH en el puerto de envío -> 530" bash -c "! timeout 20 python3 correo/smtp/email_envia_crudo.py > $T/x.txt && grep -q 'respondió 530' $T/x.txt"
check "sin SSL_CERT_FILE el certificado autofirmado se RECHAZA" bash -c "! env -u SSL_CERT_FILE timeout 20 python3 correo/pop3/email_pop3_poplib2.py > $T/x.txt 2>&1 && grep -q 'CERTIFICATE_VERIFY_FAILED' $T/x.txt && grep -q SSL_CERT_FILE $T/x.txt"
check "puerto cerrado -> 'Nadie escucha'" bash -c "! IS_SMTP_PORT=1 timeout 20 python3 correo/smtp/email_envia_crudo.py > $T/x.txt 2>&1 && grep -q 'Nadie escucha' $T/x.txt"

echo "[Parada de los simuladores]"
kill "$LANZADOR"; wait "$LANZADOR" 2>/dev/null; LANZADOR=""
sleep 0.5
check "no queda ningún puerto de los simuladores abierto" bash -c "! ss -ltn | grep -qE ':(12525|15587|15995) '"
check "no queda ningún proceso de los simuladores" bash -c "! pgrep -f 'servidor_(smtp|pop3)_falso.py --puerto 1(2525|5587|5995)'"

echo "[DNS (necesita Internet)]"
HAY_RED=0
[ -n "$(dig +time=2 +tries=2 +short @8.8.8.8 www.uniovi.es 2>/dev/null)" ] && HAY_RED=1
if [ "$HAY_RED" = 0 ]; then
    for t in herramientas iterativo.sh iterativo.py ej1 apple mx_gmail gethostbyname getaddrinfo wikipedia spf; do
        omitir "dns $t (sin acceso a 8.8.8.8)"; done
else
    check "dig @8.8.8.8: ANSWER con CNAME y A de www.uniovi.es" bash -c "dig +time=3 @8.8.8.8 www.uniovi.es | grep -A3 'ANSWER SECTION' | grep -q 'IN.*A'"
    if [ -n "$(dig +time=3 +tries=1 +short @156.35.41.4 www.uniovi.es 2>/dev/null)" ]; then
        check "dig @156.35.41.4 (DNS de Uniovi) responde" true
    else
        omitir "dig @156.35.41.4 no responde (normal desde fuera de la red de Uniovi)"
    fi
    check "host es la salida más concisa (1 línea por registro)" bash -c "host www.uniovi.es | grep -q 'is an alias for'"
    check "raíz con +norecurse: referencia a org (AUTHORITY, sin aa)" bash -c "dig +norecurse +time=3 @198.41.0.4 en.wikipedia.org > $T/r.txt && grep -A1 'AUTHORITY SECTION' $T/r.txt | grep -q '^org\.' && ! grep -q 'flags: qr aa' $T/r.txt"
    check "ej. 1-2 dns_herramientas.sh (host, dig, nslookup, 3 servidores)" bash -c "timeout 120 bash dns/dns_herramientas.sh > $T/h.txt 2>&1; grep -q '== nslookup www.uniovi.es' $T/h.txt && grep -q 'dig @8.8.8.8 www.uniovi.es' $T/h.txt && grep -q 'es.wikipedia.org.*CNAME' $T/h.txt"
    # La IP final puede no coincidir con la de host: Wikimedia usa GeoDNS y
    # contesta según quién pregunta. Se exige llegar a una IPv4 con autoridad
    check "ej. 3 dns_iterativo.sh: raíz -> org -> wikipedia.org -> IP" bash -c "timeout 90 bash dns/dns_iterativo.sh > $T/i.txt; grep -q \"REFERENCIA: la zona 'org.'\" $T/i.txt && grep -q \"REFERENCIA: la zona 'wikipedia.org.'\" $T/i.txt && grep -qE 'Resultado iterativo: en.wikipedia.org -> [0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$' $T/i.txt"
    if [ "$HAY_DNSPYTHON" = 1 ]; then
        check "ej. 3 dns_iterativo.py: referencias, glue, CNAME e IP final" bash -c "timeout 90 $PY_DNS dns/dns_iterativo.py > $T/i.txt; grep -q 'sacada del glue' $T/i.txt && grep -q 'es un alias (CNAME) de dyna.wikimedia.org' $T/i.txt && grep -qE 'Resultado iterativo: en.wikipedia.org -> [0-9.]+$' $T/i.txt"
        check "ej. 4 dns_ej1.py: IP, mensaje en texto y to_wire()" bash -c "$PY_DNS dns/dns_ej1.py > $T/d.txt && grep -qE '^IP: [0-9.]+$' $T/d.txt && grep -q '^;ANSWER' $T/d.txt && grep -qE '^id \(2 primeros bytes\): ([0-9]+) = \1$' $T/d.txt"
        check "ej. 4 resolve() no da DeprecationWarning (query() sí)" bash -c "! $PY_DNS -W error::DeprecationWarning dns/dns_ej1.py 2>&1 | grep -q Deprecat"
        check "ej. 5 dns_ips_apple.py lista IPs" bash -c "$PY_DNS dns/dns_ips_apple.py | grep -qE '^ +[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$'"
        check "ej. 10 dns_mx_gmail.py: MX ordenados por preference + IP" bash -c "$PY_DNS dns/dns_mx_gmail.py > $T/mx.txt && head -1 $T/mx.txt | grep -qE '^5 +gmail-smtp-in.l.google.com\. +[0-9.]+$' && cut -d' ' -f1 $T/mx.txt | sort -n -c"
        check "SPF de uniovi.es: a:relay, include de Microsoft e IPs" bash -c "$PY_DNS dns/dns_mx_spf_uniovi.py > $T/spf.txt && grep -q '(a:relay.uniovi.es)' $T/spf.txt && grep -q 'include:spf.protection.outlook.com (Microsoft 365)' $T/spf.txt && grep -q 'FALLO: rechazar' $T/spf.txt"
    else
        for t in iterativo.py ej1 apple mx_gmail spf; do omitir "dns $t (no se pudo instalar dnspython en ~/dnsenv)"; done
    fi
    check "gethostbyname_ex: canónico, alias e IPs" bash -c "python3 dns/dns_gethostbyname.py > $T/g.txt && grep -q \"\\[1\\] alias (CNAME)  : \\['www.uniovi.es'\\]\" $T/g.txt"
    check "getaddrinfo: tuplas (familia, tipo, proto, canonname, sockaddr)" bash -c "python3 dns/dns_getaddrinfo_experimento.py | grep -q 'proto 6 es IPPROTO_TCP: True'"
    check "ej. 6 HTTP por IPv4 (301 a https) e IPv6 sin traceback" bash -c "timeout 30 python3 dns/dns_getaddrinfo_wikipedia.py > $T/w.txt 2>&1; grep -q 'HTTP/1.1 301' $T/w.txt && grep -q 'Intento por IPv6' $T/w.txt && ! grep -q Traceback $T/w.txt"
fi

echo; echo "Resultado: $ok correctas, $fallo con fallo, $omitido omitidas"
[ "$fallo" = 0 ]
