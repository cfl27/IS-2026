#!/bin/bash
# Sesión 1.4 (apartado Docker): el servidor "oche" en un contenedor.
#
# Qué hace: lanza en segundo plano un contenedor llamado "servidor_oche", en
# la red Docker "pruebas", que ejecuta uno de los servidores TCP de la sesión
# (por defecto el 5, readline) en su puerto 9999, publicado en el puerto
# 9090 del anfitrión. Es la orden del guion:
#     docker run -d --rm -p 9090:9999 --network pruebas --name servidor_oche ...
#
# Uso:  docker/tcp_docker_lanzar_servidor.sh [nº de ejercicio 3-7]   (desde cualquier carpeta)
#       Probar desde el anfitrión:  python3 clientes/tcp_cliente5_oche_readline.py localhost 9090
#       Probar desde otro contenedor, POR NOMBRE:  docker/tcp_docker_lanzar_cliente.sh
#       Pararlo:  docker stop servidor_oche
#
# Conceptos:
#   -p 9090:9999   "publicar" un puerto: lo que llegue al 9090 del ANFITRIÓN
#                  se reenvía al 9999 del CONTENEDOR. Sin -p el servidor solo
#                  es accesible desde la red Docker.
#   --name         dentro de una red creada por el usuario ("pruebas"), Docker
#                  tiene un DNS interno (127.0.0.11) que resuelve el nombre del
#                  contenedor a su IP: por eso el cliente usa "servidor_oche" y
#                  no una IP, que cambia en cada arranque.
#   -v ...:/app    se monta la carpeta servidores/ en vez de construir una imagen.
#
# OJO: si el 9090 está ocupado (Prometheus de la sesión 2.3 usa justo el 9090),
# el script avisa y usa el 9091. Se puede elegir otro con PUERTO_ANFITRION=NNNN.

DIR="$(cd "$(dirname "$0")" && pwd)"               # carpeta docker/
. "$DIR/../../../pruebas/lib_docker.sh"             # docker con o sin sudo, según funcione

N="${1:-5}"
SERVIDOR=$(cd "$DIR/../servidores" && ls tcp_servidor"$N"_*.py 2>/dev/null | head -1)
[ -n "$SERVIDOR" ] || { echo "No hay servidor del ejercicio $N (usa 3, 4, 5, 6 o 7)"; exit 1; }

PUERTO="${PUERTO_ANFITRION:-9090}"
if [ -z "$PUERTO_ANFITRION" ] && ss -ltn | grep -q ":$PUERTO "; then
    echo "AVISO: el puerto $PUERTO del anfitrión está ocupado (¿Prometheus?): uso el 9091"
    PUERTO=9091
fi

docker network inspect pruebas >/dev/null 2>&1 || docker network create pruebas >/dev/null
docker rm -f servidor_oche >/dev/null 2>&1        # por si quedó uno de antes

# python -u: salida sin buffer, para verla al momento con "docker logs"
docker run -d --rm -p "$PUERTO":9999 --network pruebas --name servidor_oche \
    -v "$DIR/../servidores":/app python:3.7 python -u "/app/$SERVIDOR" 9999 >/dev/null || exit 1
echo "servidor_oche ($SERVIDOR) en marcha: contenedor :9999, anfitrión :$PUERTO"
echo "  docker logs servidor_oche     docker stop servidor_oche"
