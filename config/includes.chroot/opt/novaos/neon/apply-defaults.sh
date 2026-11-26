#!/bin/bash
# NeonOS: إصلاح/تحديث إعدادات سطح المكتب بتحديث (حين يرفع المطوّر config-version)
# الاستخدام: apply-defaults.sh [--force]
DEF=/usr/share/novaos/defaults
[[ -f "$DEF/config-version" ]] || exit 0
CUR_FILE="$HOME/.config/neonos/config-version"
NEW=$(cat "$DEF/config-version")
CUR=$(cat "$CUR_FILE" 2>/dev/null || echo 0)
if [[ "$1" != "--force" && "$NEW" == "$CUR" ]]; then exit 0; fi

BK="$HOME/.config/neonos/backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BK"
pkill -x xfce4-panel 2>/dev/null
pkill -x xfconfd 2>/dev/null
sleep 0.5
while IFS= read -r rel; do
  [[ -z "$rel" || "$rel" == \#* ]] && continue
  for src in $DEF/config/$rel; do
    [[ -e "$src" ]] || continue
    r="${src#$DEF/config/}"
    [[ -e "$HOME/.config/$r" ]] && { mkdir -p "$BK/$(dirname "$r")"; cp -a "$HOME/.config/$r" "$BK/$r"; }
    mkdir -p "$HOME/.config/$(dirname "$r")"
    cp -a "$src" "$HOME/.config/$r"
  done
done < "$DEF/managed.list"
mkdir -p "$(dirname "$CUR_FILE")"
echo "$NEW" > "$CUR_FILE"
(xfce4-panel >/dev/null 2>&1 &)
notify-send -i /usr/share/novaos/neon-logo-48.png "NeonOS" "Desktop settings were refreshed by an update." 2>/dev/null
exit 0
