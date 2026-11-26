#!/bin/bash
# NeonOS: تشغيل برامج ويندوز (.exe/.msi/.bat) تلقائياً — يثبّت طبقة التوافق (Bottles/Wine) أول مرة بدون أسئلة
FILE="$1"
if [[ -z "$FILE" || ! -f "$FILE" ]]; then
  zenity --error --title="NeonOS" --text="Choose a Windows program (.exe) to run."
  exit 1
fi
exec /opt/novaos/neon/neon-flatpak-run.sh com.usebottles.bottles Windows-compatibility-layer -e "$FILE"
