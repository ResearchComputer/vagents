---
title: "Package Manager"
description: "Learn how to use the VAgents Package Manager to install, manage, and execute packages from git repositories."
---

# VAgents Package Manager

The VAgents Package Manager (`vibe`) is a powerful tool that allows you to install, manage, and execute code packages directly from git repositories. It provides a simple way to share and distribute reusable AI agent components, tools, and workflows.

## Overview

The package manager enables you to:
- Install packages from any git repository
- Manage package versions and dependencies
- Execute packages with custom arguments
- Create and share your own packages
- Search and discover available packages

## Installation

The package manager comes bundled with VAgents. Once you have VAgents installed, you can use the `vibe` command:

```bash
pip install v-agents
```

## Basic Usage

### Installing Packages

Install a package from a git repository:

```bash
vibe install https://github.com/username/my-package.git
```

Install from a subdirectory within the repository:

```bash
vibe install https://github.com/username/my-package.git/subdir
```

### Listing Installed Packages

View all installed packages:

```bash
vibe list
```

Get output in JSON format:

```bash
vibe list --format json
```

### Package Information

Get detailed information about a specific package:

```bash
vibe info my-package
```

### Updating Packages

Update a package to the latest version:

```bash
vibe update my-package
```

### Uninstalling Packages

Remove a package:

```bash
vibe uninstall my-package
```

### Executing Packages

Run a package:

```bash
vibe run my-package
```

Pass arguments to the package:

```bash
vibe run my-package --args "arg1" "arg2" "arg3"
```

Pass keyword arguments as JSON:

```bash
vibe run my-package --kwargs '{"param1": "value1", "param2": 42}'
```

Choose output format:

```bash
vibe run my-package --format rich    # Rich formatted output (default)
vibe run my-package --format plain   # Plain text output
vibe run my-package --format json    # JSON output
vibe run my-package --format markdown # Markdown output
```


### Package Manager Status

Check the package manager status:

```bash
vibe status
```

This shows:
- Base directory location
- Number of installed packages
- Package summary with versions
- Total disk usage

## Creating Packages

### Package Template

Create a new package template:

```bash
vibe create-template my-new-package
```

Create in a specific directory:

```bash
vibe create-template my-new-package --output-dir ./packages
```

This creates a package structure with:
- `package.yaml` - Package configuration
- `my-new-package.py` - Main module
- `README.md` - Documentation

### Package Configuration

Each package requires a `package.yaml` configuration file:

```yaml
name: my-package
version: 1.0.0
description: A sample VAgents package
author: Your Name
repository_url: https://github.com/yourusername/my-package.git
entry_point: my_package.main
dependencies: []
python_version: ">=3.8"
tags:
  - vagents
  - example
```

**Configuration Fields:**

- `name`: Package identifier (required)
- `version`: Semantic version string (required)
- `description`: Brief package description (required)
- `author`: Package author name (required)
- `repository_url`: Git repository URL (required)
- `entry_point`: Module.function or Module.Class to execute (required)
- `dependencies`: List of Python package dependencies
- `python_version`: Minimum Python version requirement
- `tags`: List of tags for categorization and search

### Package Entry Points

The entry point must be a callable function or class that can accept arguments:

```python
def main(*args, **kwargs):
    """
    Main entry point for the package

    Args:
        *args: Positional arguments from command line
        **kwargs: Keyword arguments from command line

    Returns:
        Any: Result that will be displayed to the user
    """
    return {
        "message": "Hello from my package!",
        "args": args,
        "kwargs": kwargs
    }
```

Or a class with a callable interface:

```python
class MyPackage:
    def __call__(self, *args, **kwargs):
        return self.execute(*args, **kwargs)

    def execute(self, *args, **kwargs):
        # Implementation here
        return {"result": "success"}
```

### Publishing Packages

1. Create your package using the template
2. Implement your functionality in the main module
3. Update the configuration in `package.yaml`
4. Initialize a git repository:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   ```
5. Push to a remote repository (GitHub, GitLab, etc.)
6. Users can install with:
   ```bash
   vibe install https://github.com/yourusername/my-package.git
   ```

## Advanced Usage

### Debug Mode

Enable debug logging by setting the environment variable:

```bash
export LOGLEVEL=DEBUG
vibe install https://github.com/username/package.git
```

### Security Considerations

1. **Trust your sources** - Only install packages from trusted repositories
2. **Review package code** - Check the source code before installation
3. **Use version pinning** - Pin to specific versions for production use
4. **Regular updates** - Keep packages updated for security patches
