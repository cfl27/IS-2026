import socket
import sys


def recibe_mensaje(sock):
    
    buffer = []  # una lista es mucho más eficiente que concatenar bytes
    while True:
        byte = sock.recv(1)
        if not byte:               # conexión cerrada por el otro extremo
            return b""
        buffer.append(byte)
        # ¿Los dos últimos bytes son \r\n?
        if len(buffer) >= 2 and buffer[-2] == b"\r" and buffer[-1] == b"\n":
            return b"".join(buffer)


ip = sys.argv[1] if len(sys.argv) > 1 else "localhost"
puerto = int(sys.argv[2]) if len(sys.argv) > 2 else 9999

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((ip, puerto))

# Tres envíos seguidos, como en el experimento
for msg in ["UNO\r\n", "DOS\r\n", "TRES\r\n"]:
    print(f"Enviando: {repr(msg)}")
    s.sendall(msg.encode("utf-8"))

# Tres lecturas: ahora cada una devuelve una línea completa
for _ in range(3):
    respuesta = recibe_mensaje(s).decode("utf-8")
    print(f"Respuesta recibida: {repr(respuesta)}")

s.close()
