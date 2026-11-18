import random
import socket
import sys

puerto = int(sys.argv[1]) if len(sys.argv) > 1 else 9999

# SOCK_DGRAM = UDP. bind a "" escucha en todas las interfaces
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(("", puerto))
print("Servidor UDP escuchando en el puerto", puerto)

while True:
    datagrama, origen = s.recvfrom(1024)

    if random.randint(0, 1) == 0:
        # Pérdida simulada: no se muestra ni se confirma
        print("Simulando paquete perdido")
    else:
        print("Recibido desde", origen)
        print("Contenido:", datagrama.decode("utf8", errors="replace"))

        # Confirmación al cliente (a la dirección de la que vino el datagrama)
        s.sendto(b"OK", origen)
