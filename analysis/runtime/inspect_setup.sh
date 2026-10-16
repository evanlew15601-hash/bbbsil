#!/usr/bin/env bash
set -euo pipefail

mkdir -p /runtime/wine-home /runtime/wine-prefix /runtime/screenshots
export HOME=/runtime/wine-home
export WINEPREFIX=/runtime/wine-prefix
export WINEDEBUG=+process,+seh
export DISPLAY=:99

Xvfb "$DISPLAY" -ac -screen 0 1280x1024x24 -nolisten tcp >/tmp/xvfb.log 2>&1 &
xvfb_pid=$!
setup_pid=
cleanup() {
	if [[ -n "$setup_pid" ]]; then
		kill "$setup_pid" 2>/dev/null || true
		wait "$setup_pid" 2>/dev/null || true
	fi
	kill "$xvfb_pid" 2>/dev/null || true
	wait "$xvfb_pid" 2>/dev/null || true
}
trap cleanup EXIT

if [[ ! -f "$WINEPREFIX/system.reg" ]]; then
	printf 'Initializing persistent Wine prefix...\n'
	timeout --signal=TERM --kill-after=5s 120s wineboot --init
fi

wine /input/Setup.exe >/tmp/setup.log 2>&1 &
setup_pid=$!

wait_for_launcher() {
	for _ in $(seq 1 200); do
		import -window root /tmp/launcher.png 2>/dev/null || continue
		colors="$(identify -format '%k' /tmp/launcher.png 2>/dev/null || printf '0')"
		if [[ "$colors" =~ ^[0-9]+$ ]] && (( colors > 100 )); then
			return 0
		fi
	done
	return 1
}

wait_for_screen_change() {
	local previous_hash="$1"
	for _ in $(seq 1 200); do
		import -window root /tmp/launcher.png 2>/dev/null || continue
		local current_hash
		current_hash="$(sha256sum /tmp/launcher.png | cut -d ' ' -f 1)"
		if [[ "$current_hash" != "$previous_hash" ]]; then
			return 0
		fi
	done
	return 1
}

wait_for_launcher || {
	printf 'Timed out waiting for the installer launcher to render.\n' >&2
	return 1 2>/dev/null || exit 1
}

if [[ "${1:-}" == "--install" || "${1:-}" == "--advance" || "${1:-}" == "--accept" || "${1:-}" == "--path" || "${1:-}" == "--complete" ]]; then
	initial_hash="$(sha256sum /tmp/launcher.png | cut -d ' ' -f 1)"
	xdotool mousemove --sync 640 643 click 1
	wait_for_screen_change "$initial_hash" || true
fi

if [[ "${1:-}" == "--advance" || "${1:-}" == "--accept" || "${1:-}" == "--path" || "${1:-}" == "--complete" ]]; then
	initial_hash="$(sha256sum /tmp/launcher.png | cut -d ' ' -f 1)"
	xdotool mousemove --sync 719 669 click 1
	wait_for_screen_change "$initial_hash" || true
fi

if [[ "${1:-}" == "--accept" || "${1:-}" == "--path" || "${1:-}" == "--complete" ]]; then
	initial_hash="$(sha256sum /tmp/launcher.png | cut -d ' ' -f 1)"
	xdotool mousemove --sync 719 669 click 1
	wait_for_screen_change "$initial_hash" || true
fi

if [[ "${1:-}" == "--path" || "${1:-}" == "--complete" ]]; then
	initial_hash="$(sha256sum /tmp/launcher.png | cut -d ' ' -f 1)"
	printf 'Selecting explicit Wine destination C:\\BBB\n'
	xdotool mousemove --sync 700 396 click 1
	xdotool key Home shift+End
	xdotool type --clearmodifiers 'C:\BBB'
	wait_for_screen_change "$initial_hash" || true
	import -window root /runtime/screenshots/setup-path.png
	printf 'Path-entry screenshot: /runtime/screenshots/setup-path.png\n'
	if [[ "${1:-}" == "--path" ]]; then
		return 0 2>/dev/null || exit 0
	fi
	initial_hash="$(sha256sum /tmp/launcher.png | cut -d ' ' -f 1)"
	xdotool mousemove --sync 719 669 click 1
	wait_for_screen_change "$initial_hash" || true
	if wait "$setup_pid"; then
		printf 'SETUP_EXIT=0\n'
	else
		setup_exit=$?
		printf 'SETUP_EXIT=%s\n' "$setup_exit"
	fi
	printf 'Installed game files:\n'
	find "$WINEPREFIX/drive_c" -type f \( \
		-iname 'Bbb.exe' -o -iname 'BBB.dat' -o -iname 'BBBMusic.dat' -o \
		-iname 'BBBSound.dat' \
	\) -print
fi

xdotool search --onlyvisible --name '.*' >/tmp/setup-window-ids 2>/dev/null || true

printf 'Visible window titles:\n'
while read -r window; do
	[[ -n "$window" ]] || continue
	printf '%s: ' "$window"
	xdotool getwindowname "$window" 2>/dev/null || true
	printf '  pid='
	(xdotool getwindowpid "$window" 2>/dev/null || true)
	printf '  geometry='
	(xdotool getwindowgeometry --shell "$window" 2>/dev/null | tr '\n' ' ' || true)
	printf '\n'
done </tmp/setup-window-ids

printf '\nWindow tree:\n'
if command -v xwininfo >/dev/null 2>&1; then
	xwininfo -root -tree 2>&1 | head -80 || true
fi

printf '\nWine process state:\n'
ps -efww | grep -E '[w]ine|[S]etup.exe|[w]ineserver' || true

import -window root /runtime/screenshots/setup.png 2>/tmp/setup-screenshot.log || {
	cat /tmp/setup-screenshot.log >&2
	return 1 2>/dev/null || exit 1
}

printf '\nScreenshot: /runtime/screenshots/setup.png\n'
printf '\nWine setup log:\n'
tail -60 /tmp/setup.log