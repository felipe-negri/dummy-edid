#!/usr/bin/env python3
"""Grava um EDID (128 ou 256 bytes) na EEPROM do dummy HDMI (endereço I2C 0x50) e confere.

Antes de gravar, salva o conteúdo atual em edid/backup-<data>.bin.
Uso: python3 write_eeprom.py <arquivo.bin> [/dev/i2c-N]
     python3 write_eeprom.py --read <saida.bin> [/dev/i2c-N]
O barramento do conector sai em `ddcutil detect` (linha "I2C bus").
"""
import fcntl
import os
import sys
import time

I2C_SLAVE = 0x0703
PAGE = 8          # 24C02: página de 8 bytes


def open_bus(dev):
    fd = os.open(dev, os.O_RDWR)
    fcntl.ioctl(fd, I2C_SLAVE, 0x50)
    return fd


def read(fd, n=256):
    os.write(fd, bytes([0]))
    return os.read(fd, n)


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    if args[0] == "--read":
        fd = open_bus(args[2] if len(args) > 2 else "/dev/i2c-3")
        open(args[1], "wb").write(read(fd))
        print(f"{args[1]}: 256 bytes lidos")
        return
    data = open(args[0], "rb").read()
    assert len(data) in (128, 256), f"tamanho inválido: {len(data)}"
    fd = open_bus(args[1] if len(args) > 1 else "/dev/i2c-3")
    backup = time.strftime("edid/backup-%Y%m%d-%H%M%S.bin")
    os.makedirs("edid", exist_ok=True)
    open(backup, "wb").write(read(fd))
    print(f"backup do conteúdo atual: {backup}")
    for off in range(0, len(data), PAGE):
        os.write(fd, bytes([off]) + data[off:off + PAGE])
        time.sleep(0.02)  # tempo de escrita da EEPROM
    if read(fd, len(data)) != data:
        sys.exit("DIVERGE! a EEPROM não ficou igual ao arquivo (write-protect?)")
    print("OK: gravado e conferido. Rode ./reload.sh pra placa reler o EDID.")


if __name__ == "__main__":
    main()
