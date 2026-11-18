import time

import os
import sys

# comun.py está en la carpeta padre (la de la sesión)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from comun import HOST, USUARIO, importar_telnetlib, obtener_clave

# telnetlib solo existe hasta Python 3.12: si falta, mensaje claro y salida
telnetlib = importar_telnetlib()
SERVIDOR = "udp_servidor3_con_ok.py"

clave = obtener_clave()
tn = telnetlib.Telnet(HOST, 23, 10)

# 1-2. Login y espera del prompt
tn.read_until(b"login: ", 10)
tn.write(USUARIO.encode("ascii") + b"\n")
tn.read_until(b"Password: ", 10)
tn.write(clave.encode("ascii") + b"\n")
bienvenida = tn.read_until(b"$", 10)
# El prompt completo (p. ej. "alumno@maquina:~$") es la última línea leída.
# Se espera por él, y no por un simple "$", porque la salida de ps puede
# contener "$" en la línea de órdenes de otros procesos.
prompt = bienvenida.splitlines()[-1].strip()

# 3. Lista de procesos. Por Telnet no se negocia el tamaño de la terminal y
#    ps recorta cada línea a 80 columnas, cortando el nombre del script;
#    -ww quita ese límite de anchura.
tn.write(b"ps -ef -ww\n")
procesos = tn.read_until(prompt, 10).decode("ascii", errors="replace")

if SERVIDOR in procesos:
    # 4. Ya estaba corriendo: no se lanza otra copia (fallaría igualmente
    #    con "Address already in use", porque el puerto UDP ya está ocupado)
    print("El servidor ya está en ejecución")
    tn.write(b"exit\n")
    tn.close()
else:
    # 5. Lanzarlo en segundo plano:
    #    - "&" lo deja en segundo plano y devuelve el prompt.
    #    - nohup hace que ignore la señal SIGHUP, que el sistema envía a los
    #      procesos de una sesión cuando esta se cierra; sin nohup el servidor
    #      moriría al hacer "exit".
    #    - La salida va a un fichero para que el proceso no quede ligado a la
    #      terminal de esta sesión (que va a desaparecer).
    tn.write(f"nohup python3 {SERVIDOR} > servidor_udp.log 2>&1 &\n".encode("ascii"))
    # 6. Dar tiempo a que arranque, salir y recoger lo que quede
    time.sleep(1)
    tn.write(b"exit\n")
    print(tn.read_all().decode("ascii", errors="replace"))
    print("Servidor lanzado")
