#!/bin/bash
# NeonOS: يشغّل تطبيق Flatpak، ولو غير مثبّت يثبّته تلقائياً أول مرة مع شريط تقدّم
APP="$1"; NAME="${2//-/ }"; shift 2
if ! flatpak info "$APP" >/dev/null 2>&1; then
  flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo 2>/dev/null
  flatpak install -y --noninteractive flathub "$APP" 2>&1 \
    | zenity --progress --pulsate --auto-close --no-cancel --title="NeonOS" \
        --text="Installing $NAME (first time only, needs internet)…" --width=440
  if ! flatpak info "$APP" >/dev/null 2>&1; then
    zenity --error --title="NeonOS" --text="Could not install $NAME.\nCheck your internet connection and try again."
    exit 1
  fi
fi
exec flatpak run "$APP" "$@"
