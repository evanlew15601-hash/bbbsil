# Local Runtime Tools

This local image adds X11 inspection/automation tools and 32-bit Mesa/EGL
libraries to the pinned Wine 11 base image. It contains no game files. Build it
from the repository root:

```sh
docker build -t bbbsil-wine-ui -f analysis/runtime/Dockerfile analysis/runtime
```

Run the original CD installer with its input mounted read-only, no network, and
all Wine state temporary:

```sh
docker run --rm --network none \
  --mount type=bind,source="$PWD",target=/input,readonly \
  --workdir /input \
  --tmpfs /tmp:rw,exec,nosuid,size=3g \
  --entrypoint /bin/bash bbbsil-wine-ui -lc \
  'xvfb-run -a wine Setup.exe'
```

The installer is interactive. `inspect_setup.sh` captures the launcher screen;
pass `--install` to click `Instalar`, `--advance` to step through the initial
instruction page, `--accept` to accept the license and stop at the destination
page, or `--complete` to install to the default path and wait for Setup to exit.
The complete action prints discovered game files. Do not report an install based
only on its process exit code; verify `Bbb.exe`, `BBB.dat`, `BBBMusic.dat`, and
`BBBSound.dat` in the persistent Wine prefix before launching the game. The
original input directory remains read-only.