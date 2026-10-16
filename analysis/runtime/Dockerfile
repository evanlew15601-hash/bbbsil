FROM scottyhardy/docker-wine@sha256:2133f429d75dd4f652580554279212105bf91d9eafd5ff8e7773dbe83a8b5b2f

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        xdotool \
        x11-apps \
        imagemagick \
        libegl1:i386 \
        libgl1:i386 \
        libgl1-mesa-dri:i386 \
        mesa-utils \
    && rm -rf /var/lib/apt/lists/*