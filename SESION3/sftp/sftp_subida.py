
# Concepto: put() copia el fichero local al servidor; después stat() pide
# sus atributos remotos (tamaño, permisos) para verificar la transferencia
# comparando tamaños. Es la comprobación mínima: no detecta un contenido
# distinto del mismo tamaño (para eso habría que comparar un hash).
# El docstring de arriba es también el mensaje de uso (sys.exit(__doc__)).
import os
import sys

import paramiko


# comun.py está en la carpeta padre (la de la sesión)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from comun import HOST, USUARIO, obtener_clave

# --- Argumentos: si no se da nombre remoto, se usa el del fichero local
if len(sys.argv) < 2:
    sys.exit(__doc__)
origen = sys.argv[1]
destino = sys.argv[2] if len(sys.argv) > 2 else os.path.basename(origen)

# --- Conexión SSH + canal SFTP
client = paramiko.SSHClient()
client.load_system_host_keys()
client.set_missing_host_key_policy(paramiko.WarningPolicy())
client.connect(HOST, username=USUARIO, password=obtener_clave())
sftp = client.open_sftp()

# --- Subida y verificación (ruta relativa = relativa al home remoto)
sftp.put(origen, destino)
info = sftp.stat(destino)
print(f"Subido {origen} -> {destino}: {info.st_size} bytes, permisos {oct(info.st_mode)}")
assert info.st_size == os.path.getsize(origen), "el tamaño no coincide"

sftp.close()
client.close()
