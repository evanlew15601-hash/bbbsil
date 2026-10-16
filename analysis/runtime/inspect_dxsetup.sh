#!/usr/bin/env bash
set -euo pipefail

mkdir -p /runtime/wine-home /runtime/wine-prefix /runtime/screenshots
export HOME=/runtime/wine-home
export WINEPREFIX=/runtime/wine-prefix
export WINEDEBUG=-all
export DISPLAY=:99

Xvfb "$DISPLAY" -ac -screen 0 1280x1024x24 -nolisten tcp >/tmp/xvfb-dx.log 2>&1 &
xvfb_pid=$!
dxsetup_pid=
cleanup() {
	if [[ -n "$dxsetup_pid" ]]; then
		kill "$dxsetup_pid" 2>/dev/null || true
		wait "$dxsetup_pid" 2>/dev/null || true
	fi
	kill "$xvfb_pid" 2>/dev/null || true
	wait "$xvfb_pid" 2>/dev/null || true
}
trap cleanup EXIT

wine /input/dxsetup.exe >/tmp/dxsetup.log 2>&1 &
dxsetup_pid=$!
timeout --signal=TERM 20s xdotool search --sync --onlyvisible --name '.+' \
	>/tmp/dxsetup-window-ids 2>/dev/null || true

printf 'Visible DirectX setup windows:\n'
while read -r window; do
	[[ -n "$window" ]] || continue
	printf '%s: ' "$window"
	xdotool getwindowname "$window" 2>/dev/null || true
done </tmp/dxsetup-window-ids

DISPLAY="$DISPLAY" import -window root /runtime/screenshots/directx-setup.png
printf '\nScreenshot: /runtime/screenshots/directx-setup.png\n'
tail -30 /tmp/dxsetup.log