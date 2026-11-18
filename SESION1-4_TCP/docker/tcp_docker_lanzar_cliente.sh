#!/bin/bash
# Sesión 1.4 (apartado Docker): el cliente "oche" en otro contenedor, llamando
# al servidor POR SU NOMBRE.
#
# Qué hace: ejecuta (en primer plano, y se borra al acabar) el cliente TCP del
# ejercicio indicado (por defecto el 5) en la red "pruebas", conectando a
# "servidor_oche:9999". Antes hay que lanzar docker/tcp_docker_lanzar_servidor.sh
# con el MISMO número de ejercicio (cada pareja habla su propio protocolo).
#
# Uso:  docker/tcp_docker_lanzar_cliente.sh [nº de ejercicio 3-7]
#
# Concepto: el cliente usa el puerto 9999 (el del CONTENEDOR), no el 9090: el
# -p del servidor solo afecta a quien entra desde el anfitrión. Entre
# contenedores de la misma red se habla directamente, por nombre y puerto
# interno, gracias al DNS de Docker.

DIR="$(cd "$(dirname "$0")" && pwd)"
. "$DIR/../../../pruebas/lib_docker.sh"             # docker con o sin sudo, según funcione

N="${1:-5}"
# El primero en orden alfabético: en el 3 es tcp_cliente3_oche.py (y no el
# experimento tcp_cliente3_oche_envia_seguido.py)
CLIENTE=$(cd "$DIR/../clientes" && ls tcp_cliente"$N"_*.py 2>/dev/null | sort | head -1)
[ -n "$CLIENTE" ] || { echo "No hay cliente del ejercicio $N (usa 3, 4, 5, 6 o 7)"; exit 1; }

docker run --rm --network pruebas -v "$DIR/../clientes":/app \
    python:3.7 python "/app/$CLIENTE" servidor_oche 9999
