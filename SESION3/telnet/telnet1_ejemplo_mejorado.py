import getpass
import telnetlib

HOST = "localhost"

user = input("Usuario: ")
password = getpass.getpass("Contraseña: ")

tn = telnetlib.Telnet(HOST)

tn.read_until(b"login: ")
tn.write(user.encode("utf8") + b"\n")

tn.read_until(b"Password: ")
tn.write(password.encode("utf8") + b"\n")

# Esperamos hasta el prompt inicial y descartamos todo lo anterior
tn.read_until(b"$")

# Ejecutamos el comando
tn.write(b"ls /home\n")

# Leemos hasta que vuelva a aparecer el prompt
respuesta = tn.read_until(b"$")

print(respuesta.decode("utf8"))

tn.write(b"exit\n")
tn.read_all()