#!/bin/bash
# Ejercicio 3: huellas (fingerprints) SHA256 de las claves del servidor SSH local.
#
# Concepto: la primera vez que un cliente SSH conecta a un servidor muestra
# la huella de su clave de host y pregunta si se fía. La huella es un resumen
# (hash SHA256) de la clave pública: corta y fácil de comparar. Para no
# aceptar a ciegas, se compara con la que da el propio servidor (este
# script). Si coinciden, la clave es la auténtica y no hay nadie en medio.
#
# El servidor tiene una clave por algoritmo (ed25519, ecdsa, rsa); el cliente
# muestra la del algoritmo que se negocie (normalmente ed25519).
#
# Uso:  ssh/ssh_fingerprint.sh
for tipo in ed25519 ecdsa rsa; do
    f=/etc/ssh/ssh_host_${tipo}_key.pub
    # ssh-keygen -l: muestra la huella (-l = "list fingerprint") de la clave -f
    [ -r "$f" ] && ssh-keygen -l -f "$f"
done
