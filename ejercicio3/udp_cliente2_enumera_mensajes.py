import socket

host = "localhost"
puerto = 5000

cliente = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

contador = 1

while True:
    mensaje = input("Escribe un mensaje: ")

    datagrama = str(contador) + ": " + mensaje

    cliente.sendto(datagrama.encode(), (host, puerto))

    contador += 1
