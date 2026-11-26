#!/bin/bash
# NeonOS: تثبيت درايفر NVIDIA المناسب لكرتك تلقائياً (عبر nvidia-detect). يُستدعى بـ sudo من الإعدادات فقط.
set -e
export DEBIAN_FRONTEND=noninteractive
command -v nvidia-detect >/dev/null 2>&1 || apt-get install -y nvidia-detect
PKG=$(nvidia-detect 2>/dev/null | grep -oE 'nvidia-[a-z0-9-]*driver' | head -1 || true)
if [[ -z "$PKG" ]]; then
  echo "No NVIDIA GPU found, or it uses the open-source driver already."
  exit 2
fi
echo "Selected driver: $PKG"
echo "PROGRESS 5";  apt-get update
echo "PROGRESS 25"; apt-get install -y linux-headers-amd64 dkms firmware-misc-nonfree
echo "PROGRESS 45"; apt-get install -y "$PKG"
echo "PROGRESS 100"
echo "Driver $PKG installed. A restart activates it."
