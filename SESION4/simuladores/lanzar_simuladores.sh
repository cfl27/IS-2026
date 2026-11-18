#!/bin/bash
# Simuladores: lanza los tres servidores falsos para probar el correo en local.
#
# Qué hace:
#   1. Genera un certificado autofirmado para localhost (generar_certificado.sh).
#   2. Lanza en segundo plano, compartiendo el mismo buzón:
#        127.0.0.1:2525  SMTP modo RELAY       (como relay.uniovi.es:25)
#        127.0.0.1:5587  SMTP STARTTLS + AUTH  (como smtp.gmail.com:587)
#        127.0.0.1:5995  POP3 con TLS implícito (como pop.gmail.com:995)
#      Puertos > 1024: no hace falta root (los < 1024 son "privilegiados").
#   3. Escribe en <dir>/entorno.sh las variables para los clientes y espera.
#      Ctrl+C (o kill) para los tres servidores.
#
# Ejecución:
#   Terminal 1:  bash simuladores/lanzar_simuladores.sh [/tmp/is_s4_sim]
#   Terminal 2:  source /tmp/is_s4_sim/entorno.sh
#                IS_SMTP_PORT=2525 python3 correo/smtp/email_envia_crudo.py
#                python3 correo/pop3/email_pop3_poplib2.py
#   Los diálogos, vistos desde el servidor: /tmp/is_s4_sim/*.log
#
# Credenciales: IS_SIM_USER / IS_SIM_PASS si existen; si no, alumno@example.com
# y una clave ALEATORIA nueva en cada arranque (nada fijo en el repositorio).
cd "$(dirname "$0")" || exit 1
DIR="${1:-/tmp/is_s4_sim}"
P_RELAY="${IS_SIM_PUERTO_RELAY:-2525}"
P_SUB="${IS_SIM_PUERTO_SUB:-5587}"
P_POP="${IS_SIM_PUERTO_POP:-5995}"
export IS_SIM_USER="${IS_SIM_USER:-alumno@example.com}"
export IS_SIM_PASS="${IS_SIM_PASS:-$(openssl rand -hex 8)}"
export PYTHONDONTWRITEBYTECODE=1

for p in "$P_RELAY" "$P_SUB" "$P_POP"; do
    ss -ltn | grep -q "127.0.0.1:$p " && { echo "El puerto $p ya está ocupado (¿simuladores ya lanzados?)"; exit 1; }
done

mkdir -p "$DIR/buzon" || exit 1
bash ./generar_certificado.sh "$DIR" >/dev/null || exit 1
CERT=(--cert "$DIR/cert.pem" --clave "$DIR/clave.pem")

# Al salir (Ctrl+C, kill o fin normal) se paran los tres hijos
trap 'kill $(jobs -p) 2>/dev/null; wait 2>/dev/null; echo "Simuladores parados."' EXIT
trap 'exit 0' INT TERM

python3 -u servidor_smtp_falso.py --puerto "$P_RELAY" --buzon "$DIR/buzon" >"$DIR/smtp_relay.log" 2>&1 &
python3 -u servidor_smtp_falso.py --puerto "$P_SUB" --buzon "$DIR/buzon" "${CERT[@]}" \
        --exigir-auth >"$DIR/smtp_submission.log" 2>&1 &
python3 -u servidor_pop3_falso.py --puerto "$P_POP" --buzon "$DIR/buzon" "${CERT[@]}" >"$DIR/pop3.log" 2>&1 &

# Esperar a que los tres escuchen (máx. 5 s)
for _ in $(seq 50); do
    n=$(ss -ltn | grep -cE "127.0.0.1:($P_RELAY|$P_SUB|$P_POP) ")
    [ "$n" = 3 ] && break; sleep 0.1
done
[ "$n" = 3 ] || { echo "No arrancaron los simuladores:"; cat "$DIR"/*.log; exit 1; }

# Variables para los clientes. umask 077: el fichero solo lo lee su dueño
(umask 077; cat >"$DIR/entorno.sh" <<EOF
# Generado por lanzar_simuladores.sh: credenciales TEMPORALES del simulador
export SSL_CERT_FILE="$DIR/cert.pem"   # confiar en el certificado autofirmado
export IS_SMTP_SERVER=localhost IS_SMTP_PORT=$P_SUB
export IS_POP_SERVER=localhost IS_POP_PORT=$P_POP
export IS_USER="$IS_SIM_USER" IS_PASS="$IS_SIM_PASS"
export IS_FROM="$IS_SIM_USER" IS_TO="$IS_SIM_USER"
EOF
)
echo "Simuladores en marcha (buzón: $DIR/buzon, logs: $DIR/*.log)."
echo "En otra terminal:  source $DIR/entorno.sh"
echo "  (para el relay sin AUTH de los ej. 7-9 añade IS_SMTP_PORT=$P_RELAY)"
echo "Ctrl+C para pararlos."
wait
