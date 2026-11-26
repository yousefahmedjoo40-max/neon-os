#!/bin/bash
# فحص التحديثات بالخلفية وإظهار إشعار فقط (لا تحميل ولا إعادة تشغيل بدون موافقتك)
OUT=$(python3 /opt/novaos/updater/updater.py check 2>/dev/null)
VER=$(echo "$OUT" | sed -n 's/^RESULT available //p' | tail -1)
if [[ -n "$VER" ]]; then
  notify-send -i /usr/share/novaos/neon-logo-48.png "NeonOS update available" \
    "Version $VER is ready. Open Neon Center → Updates. It installs in the background — no restart needed."
fi
