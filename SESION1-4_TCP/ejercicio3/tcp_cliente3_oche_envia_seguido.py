import socket
import sys

if len(sys.argv) > 1:
    ip = sys.argv[1]
else:
    ip = "localhost"

if len(sys.argv) > 2:
    puerto = int(sys.argv[2])
else:
    puerto = 9999

cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

cliente.connect((ip, puerto))

mensajes = ["HOLA", "MUNDO", "PYTHON"]

# Primero enviamos los tres mensajes seguidos
for mensaje in mensajes:
    mensaje = mensaje + "\r\n"
    cliente.sendall(mensaje.encode("utf-8"))

# Después intentamos recibir tres respuestas
for i in range(3):
    respuesta = cliente.recv(80)
    respuesta = respuesta.decode("utf-8")
    print(repr(respuesta))

cliente.close()