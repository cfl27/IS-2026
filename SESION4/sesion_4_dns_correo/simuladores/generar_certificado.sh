#!/bin/bash
# Simuladores: certificado TLS AUTOFIRMADO para localhost.
#
# Qué hace: crea en el directorio indicado cert.pem (certificado) y clave.pem
# (clave privada) con openssl, válidos 7 días, para CN=localhost y con
# subjectAltName DNS:localhost e IP:127.0.0.1.
#
# Ejecución:   bash simuladores/generar_certificado.sh /tmp/is_s4_sim
#
# Concepto:
#   - Un certificado une un NOMBRE con una clave pública y va FIRMADO por una
#     autoridad (CA) en la que el cliente confía (las de /etc/ssl/certs).
#     "Autofirmado" = firmado por su propia clave: nadie lo avala, así que un
#     cliente correcto lo RECHAZA (ssl.SSLCertVerificationError).
#   - El cliente comprueba el nombre en el subjectAltName (el CN ya no
#     cuenta en los clientes modernos): debe coincidir con server_hostname.
#   - El truco para probar sin tocar el código de los clientes:
#         export SSL_CERT_FILE=/tmp/is_s4_sim/cert.pem
#     ssl.create_default_context() carga las CA "por defecto" y OpenSSL toma
#     esa variable como el fichero de CA de confianza. Así el cliente
#     VERIFICA de verdad (nombre y firma) y solo confía en NUESTRO
#     certificado. Mejor que desactivar la verificación (CERT_NONE), que es
#     justo el error que no hay que cometer en un cliente real.
#   - -nodes ("no DES"): la clave privada sin contraseña, para que el
#     servidor arranque solo. Aceptable para una prueba local y temporal.
DIR="${1:?Uso: $0 <directorio>}"
mkdir -p "$DIR" || exit 1
openssl req -x509 -newkey rsa:2048 -sha256 -nodes -days 7 \
    -keyout "$DIR/clave.pem" -out "$DIR/cert.pem" \
    -subj "/CN=localhost" \
    -addext "subjectAltName=DNS:localhost,IP:127.0.0.1" 2>/dev/null || {
    echo "openssl ha fallado"; exit 1; }
chmod 600 "$DIR/clave.pem"
echo "Certificado: $DIR/cert.pem   Clave: $DIR/clave.pem"
