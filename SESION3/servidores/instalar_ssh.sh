#!/bin/bash
# Apartado 2.2.1: instala el servidor OpenSSH y un entorno virtual con paramiko.

set -e   # parar en el primer error

# apt-get install -y: instala sin preguntar. python3-venv permite crear
# entornos virtuales (Ubuntu no deja instalar paquetes con pip en el sistema)
sudo apt-get install -y openssh-server python3-venv
# enable --now: arrancar el servicio ya y también en cada arranque
sudo systemctl enable --now ssh
# Al instalarse se generan las claves de host (una por algoritmo)
ls -l /etc/ssh/ssh_host_*

# Entorno virtual ~/paramikoenv con paramiko (solo la primera vez)
if [ ! -d ~/paramikoenv ]; then
    python3 -m venv ~/paramikoenv
    ~/paramikoenv/bin/pip install --quiet --upgrade pip paramiko
fi
~/paramikoenv/bin/python -c "import paramiko; print('paramiko', paramiko.__version__)"
# ss -ltn: sockets TCP (-t) en escucha (-l), con puertos numéricos (-n)
ss -ltn | grep -q ':22 ' && echo "SSH escuchando en el puerto 22"
