import socket
import random

host = "localhost"
puerto = 5000

servidor = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
servidor.bind((host, puerto))

print("Servidor UDP esperando mensajes...")

while True:
    datos, direccion = servidor.recvfrom(1024)

    if random.randint(0, 1) == 0:
        print("Simulando paquete perdido")
    else:
        print(datos.decode())
