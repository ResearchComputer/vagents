---
title: "Example: Deep Research"
description: A guide in my new Starlight docs site.
---

## Prerequisites

Make sure you have `docker` installed and running. The following example also relies on an external LLM service. Please set the following environment variables:

```bash
export RC_API_BASE="https://api.swissai.cscs.ch/v1" # Replace with your API base URL
export RC_API_KEY="sk-rc-[...]" # Replace with your API key
```

## Deploying the Service

- Run the crawl4ai service:

```bash
docker run -d \
  -p 11235:11235 \
  --name crawl4ai \
  --shm-size=1g \
  unclecode/crawl4ai:latest
```

- Clone the vAgents repository:

```bash
git clone git@github.com:eth-easl/vagent.git && cd vagent && git checkout refactor/managers
cd vagent && pip install -e ".[all]"
```

- Run the vAgents service:

```bash
export PYTHONPATH=.
vagent serve
```

## Calling the service

- Open a new terminal and run the following command:

```bash
export PYTHONPATH=.
python examples/apps/apps_client.py
```
