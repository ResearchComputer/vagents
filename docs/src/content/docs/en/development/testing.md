---
title: "Installing Testing Version"
description: ""
sidebar:
  order: 1
---


```bash
uv venv --python 3.12 --seed
source .venv/bin/activate
uv pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ v-agents
```
