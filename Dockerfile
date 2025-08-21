FROM python:3.12-slim-trixie

LABEL org.opencontainers.image.authors="Xiaoyu Guo <biggates2010@gmail.com>"

RUN apt-get update; \
    apt-get install -y git; \
    rm -rf /var/lib/apt/lists/*

COPY --from=astral/uv:python3.12-trixie-slim /usr/local/bin/uv /usr/bin/uv

RUN uv tool install --from git+https://github.com/EaphoneTech/clone-all-repo.git clone-all-repo

ENV PATH="/root/.local/bin:$PATH"

CMD [ "clone-all-repo" ]
