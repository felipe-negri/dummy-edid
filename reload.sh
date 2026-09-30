#!/usr/bin/env bash
# Faz a GPU e o KWin relerem o EDID depois de gravar a EEPROM (precisa de sudo).
#  1. `detect` no sysfs: o kernel relê o EDID do conector
#  2. uevent de change na drm: o KWin atualiza a lista de modos (sem isso ele fica com a antiga)
set -eu
CONN=${CONN:-card1-HDMI-A-1}
cd "$(dirname "$0")"
echo detect | sudo tee /sys/class/drm/$CONN/status
sudo udevadm trigger --action=change --subsystem-match=drm
sleep 2
if cmp -s /sys/class/drm/$CONN/edid edid/void-dummy.bin; then
  echo "kernel com o EDID novo"
else
  echo "ATENÇÃO: o kernel ainda tem outro EDID; rode de novo ou replugue o dummy" >&2
fi
kscreen-doctor -o 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g' | grep -m1 Modes
