---
title: "Package Manager"
description: "Learn how to use the VAgents Package Manager to install, manage, and execute packages from git repositories."
---

# VAgents Package Manager

The VAgents Package Manager (`vibe`) is a powerful tool that allows you to install, manage, and execute code packages directly from git repositories. It provides a simple way to share and distribute reusable AI agent components, tools, and workflows.

## Overview

The package manager enables you to:
- **Install packages** from any git repository with subdirectory support
- **Manage package versions** and dependencies with automatic validation
- **Execute packages** with dynamic CLI argument parsing and pipe support
- **Create and share** your own packages using built-in templates
- **Search and discover** available packages by name, description, and tags

## Installation

The package manager comes bundled with VAgents. Once you have VAgents installed, you can use the `vibe` command:

```bash
pip install v-agents
```

Verify installation:

```bash
vibe --help
```

## Basic Usage

### Installing Packages

Install a package from a git repository:

```bash
vibe install https://github.com/username/my-package.git
```

Install from a specific branch:

```bash
vibe install https://github.com/username/my-package.git --branch develop
```

Install from a subdirectory within the repository:

```bash
vibe install https://github.com/username/my-package.git/packages/subpackage
```

Force reinstall (overwrite existing package):

```bash
vibe install https://github.com/username/my-package.git --force
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

Get help for a package's CLI arguments:

```bash
vibe help-package my-package
```

### Updating Packages

Update a package to the latest version:

```bash
vibe update my-package
```

Update from a specific branch:

```bash
vibe update my-package --branch develop
```

### Uninstalling Packages

Remove a package:

```bash
vibe uninstall my-package
```

### Executing Packages

#### Dynamic CLI Argument Parsing

The package manager automatically parses CLI arguments based on each package's configuration:

```bash
# Basic execution
vibe run my-package

# With package-specific arguments
vibe run code-analyzer --history 5 --verbose
vibe run data-processor --config analysis.json --output results.csv
vibe run file-converter --input-format json --output-format yaml
```

#### Output Formats

Choose from multiple output formats:

```bash
vibe run my-package --format rich      # Rich formatted output (default)
vibe run my-package --format plain     # Plain text output
vibe run my-package --format json      # JSON output
vibe run my-package --format markdown  # Markdown output
```

#### Pipe and Stdin Support

Packages automatically support stdin input when used with pipes:

```bash
# Process file content
cat data.txt | vibe run text-analyzer --verbose

# Process command output
ls -la | vibe run file-processor

# Chain with other commands
curl -s https://api.example.com/data | vibe run api-analyzer --config api.yaml

# Process multiple files
find . -name "*.log" -exec cat {} \; | vibe run log-analyzer --format json
```

#### Legacy Argument Passing (Deprecated)

For backward compatibility, you can still use the legacy format:

```bash
# Pass positional arguments
vibe run-legacy my-package --args "arg1" "arg2" "arg3"

# Pass keyword arguments as JSON
vibe run-legacy my-package --kwargs '{"param1": "value1", "param2": 42}'
```

### Package Manager Status

Check the package manager status:

```bash
vibe status
```

This shows:
- Base directory location (~/.vagents/packages)
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
- `my-new-package.py` - Main module with example implementation
- `README.md` - Documentation with usage examples

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
arguments:
  - name: verbose
    type: bool
    help: Enable verbose output
    short: v
    required: false
  - name: config
    type: str
    help: Configuration file path
    short: c
    required: false
  - name: history
    type: int
    help: Number of historical records to process
    default: 10
    required: false
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
- `arguments`: CLI argument definitions with type validation

**Argument Types:**

- `str`: String values
- `int`: Integer values
- `float`: Float values
- `bool`: Boolean flags (use `--flag` syntax)
- `list`: Lists of values (use `--items value1 value2 value3`)

**Argument Properties:**

- `name`: Argument name (creates `--name` CLI option)
- `type`: Value type for validation
- `help`: Description shown in help text
- `short`: Single letter shortcut (creates `-x` option)
- `required`: Whether argument is mandatory
- `default`: Default value if not provided
- `choices`: List of allowed values

### Package Entry Points

The entry point must be a callable function or class that can accept arguments:

#### Function Entry Point

```python
def main(verbose=False, config=None, input=None, stdin=None, **kwargs):
    """
    Main entry point for the package

    Args:
        verbose (bool): Enable verbose output
        config (str): Configuration file path
        input (str): Input content from stdin/pipes
        stdin (str): Alias for input parameter
        **kwargs: Additional CLI arguments

    Returns:
        Any: Result that will be displayed to the user
    """
    # Handle stdin input (input and stdin are aliases)
    content = input or stdin

    result = {
        "message": "Hello from my package!",
        "verbose": verbose,
        "config": config,
        "has_input": content is not None,
        "args": kwargs
    }

    if verbose:
        print(f"Processing with config: {config}")
        if content:
            print(f"Input length: {len(content)} characters")

    # Process the input content if provided
    if content:
        result["processed_input"] = {
            "length": len(content),
            "lines": len(content.splitlines()),
            "words": len(content.split()),
            "analysis": analyze_content(content)
        }

    return result

def analyze_content(content):
    """Example processing function"""
    if "error" in content.lower():
        return "Input contains error messages"
    elif "success" in content.lower():
        return "Input contains success messages"
    else:
        return "Input analyzed successfully"
```

#### Class Entry Point

```python
class MyPackage:
    def __call__(self, *args, **kwargs):
        return self.execute(*args, **kwargs)

    def execute(self, verbose=False, config=None, **kwargs):
        # Implementation here
        return {"result": "success", "verbose": verbose}
```

### Publishing Packages

1. **Create your package** using the template
2. **Implement your functionality** in the main module
3. **Update configuration** in `package.yaml` with proper details
4. **Test locally** before publishing:
   ```bash
   # Test your implementation
   python my_package.py --verbose --config test.json
   echo "test data" | python my_package.py --verbose
   ```
5. **Initialize git repository**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/yourusername/my-package.git
   git push -u origin main
   ```
6. **Users can install** with:
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

### Programmatic Usage

You can also use the package manager directly in Python:

```python
from vagents.manager.package import PackageManager

# Initialize package manager
pm = PackageManager()

# Install a package
pm.install_package("https://github.com/user/package.git", branch="main", force=False)

# List installed packages
packages = pm.list_packages()
print(packages)

# Execute a package with arguments
result = pm.execute_package("package-name", verbose=True, config="myconfig.json")

# Execute with stdin input
content = "data to process"
result = pm.execute_package("package-name", input=content, verbose=True)

# Update a package
pm.update_package("package-name", branch="main")

# Uninstall a package
pm.uninstall_package("package-name")
```

### Configuration Files

**Supported Configuration Formats:**

The package manager supports multiple configuration file formats:
- `package.yaml` (preferred)
- `package.yml`
- `package.json`
- `vagents.yaml`
- `vagents.yml`

**Default Directories:**

- Base directory: `~/.vagents/packages`
- Registry file: `~/.vagents/packages/registry.json`
- Package storage: `~/.vagents/packages/packages/`

**Custom Configuration:**

```python
# Use custom base directory
pm = PackageManager(base_path="/custom/path")
```

### Security Considerations

1. **Trust your sources** - Only install packages from trusted repositories
2. **Review package code** - Check the source code before installation
3. **Use version pinning** - Pin to specific versions for production use
4. **Regular updates** - Keep packages updated for security patches
5. **Validate inputs** - Packages run with user privileges
6. **Monitor execution** - Watch for unexpected behavior or resource usage

### Error Handling

The package manager provides comprehensive error handling:

```python
try:
    result = pm.execute_package("package-name")
    if isinstance(result, dict) and "error" in result:
        print(f"Package execution failed: {result['error']}")
except ValueError as e:
    print(f"Package not found: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

### Package Development Best Practices

1. **Use descriptive names** for packages and arguments
2. **Provide comprehensive help** text for all CLI arguments
3. **Handle errors gracefully** with meaningful error messages
4. **Support stdin/pipe** input for data processing packages
5. **Return structured data** (dict/list) for better formatting
6. **Include examples** in your README
7. **Version your packages** semantically
8. **Test with different** input types and edge cases
9. **Document dependencies** clearly
10. **Use appropriate tags** for discoverability

### Integration with VAgents

The package manager integrates seamlessly with the VAgents framework:

```python
# Use in VAgents modules
from vagents.manager.package import PackageManager

class MyVAgentsModule:
    def __init__(self):
        self.package_manager = PackageManager()

    async def process_request(self, request):
        # Use external packages in your processing
        analysis_result = self.package_manager.execute_package(
            "data-analyzer",
            data=request.data,
            config="analysis.yaml"
        )
        return analysis_result
```
