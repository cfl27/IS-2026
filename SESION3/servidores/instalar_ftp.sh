#!/bin/bash
# Anexo 3.2.1 (opcional): servidor FTP Pure-FTPd (sin cifrar; solo para pruebas).

set -e   # parar en el primer error
# pure-ftpd = servidor; ftp = cliente de línea de órdenes para probar a mano
sudo apt-get install -y pure-ftpd ftp
# enable --now: arrancar ya y en cada arranque (si falla, al menos reiniciarlo)
sudo systemctl enable --now pure-ftpd 2>/dev/null || sudo systemctl restart pure-ftpd
sleep 1
ss -ltn | grep -q ':21 ' && echo "FTP escuchando en el puerto 21" || echo "AVISO: nada escucha en el puerto 21"
