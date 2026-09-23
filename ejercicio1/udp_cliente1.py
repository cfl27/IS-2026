import socket
import sys

if len(sys.argv) > 1:
    ip = sys.argv[1]

else:
    ip = "localhost"

if len(sys.argv) > 2:
    puerto = sys.argv[2]

else:
    puerto = 9999

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

while True:

    texto = input("Escribe un mensaje: ")

    s.sendto(texto.encode("utf-8"), (ip, puerto))

    if texto == "FIN":
        break

s.close()