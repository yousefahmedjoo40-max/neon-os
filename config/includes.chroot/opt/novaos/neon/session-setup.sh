#!/bin/bash
# NeonOS: يعمل عند كل تسجيل دخول
sleep 2
CFG="$HOME/.config/neonos"; mkdir -p "$CFG"
WALL="/usr/share/backgrounds/novaos/neon-nebula.jpg"

set_wall() {
  local props
  props=$(xfconf-query -c xfce4-desktop -l 2>/dev/null | grep '/last-image$')
  [[ -z "$props" ]] && props=$(for m in 0 Virtual-1 eDP-1 HDMI-1 VGA-1 DP-1; do echo "/backdrop/screen0/monitor$m/workspace0/last-image"; done)
  for p in $props; do
    xfconf-query -c xfce4-desktop -p "$p" -s "$WALL" 2>/dev/null || xfconf-query -c xfce4-desktop -p "$p" -n -t string -s "$WALL"
    xfconf-query -c xfce4-desktop -p "${p/last-image/image-style}" -s 5 2>/dev/null || xfconf-query -c xfce4-desktop -p "${p/last-image/image-style}" -n -t int -s 5
  done
}
[[ -f "$CFG/first-session-done" ]] || { set_wall; touch "$CFG/first-session-done"; }

# الوضع الخفيف تلقائياً للأجهزة الضعيفة (أقل من ~1.8GB رام)
RAM_KB=$(awk '/MemTotal/{print $2}' /proc/meminfo)
if [[ "$RAM_KB" -lt 1800000 && ! -f "$CFG/lite-decided" ]]; then
  touch "$CFG/lite" "$CFG/lite-decided"
  xfconf-query -c xfwm4 -p /general/use_compositing -s false 2>/dev/null || xfconf-query -c xfwm4 -p /general/use_compositing -n -t bool -s false
fi

# إصلاح الإعدادات إذا رفع المطوّر نسخة جديدة منها عبر تحديث
/opt/novaos/neon/apply-defaults.sh
( sleep 45; /opt/novaos/neon/neon-update-check.sh ) >/dev/null 2>&1 &
