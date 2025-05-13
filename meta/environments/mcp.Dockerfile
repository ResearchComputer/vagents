FROM python:3.13-slim

COPY . /vagents
WORKDIR /vagents

ENV NODE_VERSION=v23.6.0
ENV PYTHON_VERSION=3.13
ENV NVM_DIR=/usr/local/nvm
ENV NODE_PATH=$NVM_DIR/versions/node/$NODE_VERSION/bin
ENV PATH=$NODE_PATH:$PATH

RUN mkdir -p /workspace
RUN apt update && apt upgrade -y && apt install curl gcc build-essential pipx -y

RUN mkdir -p /usr/local/nvm && apt-get update && echo "y" | apt-get install curl
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
RUN /bin/bash -c "source $NVM_DIR/nvm.sh && nvm install $NODE_VERSION && nvm use --delete-prefix $NODE_VERSION"

# Install Python packages
RUN pip install --no-cache-dir -e ".[all]"
RUN pip install -U pipx && pipx ensurepath

WORKDIR /
