FROM mcr.microsoft.com/devcontainers/base:ubuntu24.04

COPY --from=jdxcode/mise /usr/local/bin/mise /usr/local/bin/

RUN DEV_USER=$(getent passwd 1000 | cut -d: -f1) && \
  chsh -s /usr/bin/zsh "$DEV_USER" && \
  echo 'eval "$(mise activate bash)"' >> /home/$DEV_USER/.bashrc && \
  echo 'eval "$(mise activate zsh)"' >> /home/$DEV_USER/.zshrc
