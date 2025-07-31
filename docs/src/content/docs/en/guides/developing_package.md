---
title: "Developing a Package"
description: "Learn how to develop and distribute VAgents packages."
---

# Developing a VAgents Package

This guide will walk you through creating, testing, and distributing your own VAgents packages.

## Getting Started

Use the package template generator to create a new package:

```bash
vibe create-template my-awesome-package
```

This creates a basic package structure that you can customize for your needs.

## Package Structure

A typical VAgents package contains:

```
my-awesome-package/
├── package.yaml          # Package configuration
├── my_awesome_package.py  # Main module
├── README.md             # Documentation
└── requirements.txt      # Optional dependencies
```

## Development Workflow

1. **Create the package template**
2. **Implement your functionality**
3. **Test locally**
4. **Publish to git repository**
5. **Install and test via package manager**

For detailed information, see the [Package Manager guide](/guides/package_manager).
