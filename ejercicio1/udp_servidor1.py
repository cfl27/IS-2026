# udp_servidor1.py
import socket
import sys

if len(sys.argv) > 1:
    puerto = int(sys.argv[1])

else: 
    puerto = 9999

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(("", puerto))

print(f"Servidor UDP escuchando en el puerto", puerto)

while True:
    datagrama, origen = s.recvfrom(1024)
    mensaje = datagrama.decode("utf-8")

    print(mensaje);
