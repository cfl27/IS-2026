
import socket
import sys

ip = sys.argv[1] if len(sys.argv) > 1 else "localhost"
puerto = int(sys.argv[2]) if len(sys.argv) > 2 else 9999

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((ip, puerto))

# Modo texto ("r"): readline() devuelve str ya decodificado. newline="\r\n"
# indica que el fin de línea es "\r\n" y se conserva en el resultado.
f = s.makefile(mode="r", encoding="utf8", newline="\r\n")

for msg in ["UNO\r\n", "DOS\r\n", "TRES\r\n"]:
    print(f"Enviando: {repr(msg)}")
    s.sendall(msg.encode("utf8"))

for _ in range(3):
    respuesta = f.readline()
    print(f"Respuesta recibida: {repr(respuesta)}")

f.close()
s.close()
