# VAgents Package Manager

A comprehensive package management system for VAgents that allows users to pull, install, and execute code packages from remote git repositories.

## Overview

The VAgents Package Manager enables users to:

- **Install packages** from remote git repositories
- **Execute functions** from installed packages in a sandboxed environment
- **Manage package versions** and dependencies
- **Create and share** reusable code packages
- **Search and discover** packages by name and tags

## Architecture

### Core Components

1. **PackageManager**: Main interface for package operations
2. **PackageRegistry**: Tracks installed packages and metadata
3. **GitRepository**: Handles git operations (clone, pull, etc.)
4. **PackageExecutionContext**: Provides sandboxed execution environment
5. **PackageConfig/PackageMetadata**: Package configuration and validation

### Package Structure

Each package must contain:

```
package-directory/
├── package.yaml (or package.json)  # Package metadata
├── main_module.py                  # Entry point module
├── README.md                       # Documentation
└── ...                            # Additional files
```

### Configuration Format

**package.yaml**:
```yaml
name: package-name
version: 1.0.0
description: Package description
author: Author Name
repository_url: https://github.com/user/repo.git
entry_point: module.function
dependencies:
  - dependency1
  - dependency2
python_version: ">=3.8"
tags:
  - tag1
  - tag2
```

## Installation

The package manager is included with VAgents. No additional installation is required.

```python
from vagents.manager.package import PackageManager
```

## Usage

### Basic Operations

```python
from vagents.manager.package import PackageManager

# Initialize package manager
pm = PackageManager()

# Install a package from git repository
pm.install_package("https://github.com/user/awesome-package.git")

# List installed packages
packages = pm.list_packages()
print(packages)

# Execute a package
result = pm.execute_package("package-name", arg1="value1", arg2="value2")

# Update a package
pm.update_package("package-name")

# Uninstall a package
pm.uninstall_package("package-name")
```

### CLI Interface

```bash
# Install a package
python -m vagents.manager.cli install https://github.com/user/package.git

# List packages
python -m vagents.manager.cli list

# Execute a package
python -m vagents.manager.cli execute package-name --kwargs '{"param": "value"}'

# Create a new package template
python -m vagents.manager.cli create-template my-package

# Get package information
python -m vagents.manager.cli info package-name

# Search packages
python -m vagents.manager.cli search --query "analysis" --tags data
```

### Advanced Usage

```python
# Install with specific branch
pm.install_package("https://github.com/user/package.git", branch="develop")

# Force reinstall
pm.install_package("https://github.com/user/package.git", force=True)

# Search packages
analysis_packages = pm.search_packages(query="analysis", tags=["data"])

# Get detailed package info
info = pm.get_package_info("package-name")
```

## Creating Packages

### 1. Use the Template Generator

```python
from vagents.manager.cli import create_package_template

# Create a new package template
create_package_template("my-awesome-package", output_dir="./packages")
```

### 2. Implement Your Function

Edit the generated module file:

```python
def main(*args, **kwargs):
    """
    Main entry point for your package

    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Any: Your function's result
    """
    # Your implementation here
    return {"message": "Hello from my package!"}
```

### 3. Configure Package Metadata

Edit `package.yaml`:

```yaml
name: my-awesome-package
version: 1.0.0
description: An awesome package that does amazing things
author: Your Name
repository_url: https://github.com/yourusername/my-awesome-package.git
entry_point: my_awesome_package.main
dependencies:
  - requests
  - numpy
python_version: ">=3.8"
tags:
  - awesome
  - utility
```

### 4. Test Locally

```python
pm = PackageManager()
# Install from local path for testing
# pm.install_package("/path/to/your/package")
result = pm.execute_package("my-awesome-package")
```

### 5. Publish to Git

```bash
git init
git add .
git commit -m "Initial package version"
git remote add origin https://github.com/yourusername/my-awesome-package.git
git push -u origin main
```

### 6. Share with Others

Others can now install your package:

```python
pm.install_package("https://github.com/yourusername/my-awesome-package.git")
```

## Example Packages

### Code Review Package

Analyzes git repositories and provides code review feedback:

```python
pm.install_package("https://github.com/vagents-ai/code-review-package.git")
result = pm.execute_package("code-review", repo_path=".")
```

**Features:**
- Git change analysis
- Code quality checks
- Suggestion generation
- Commit history review

### Data Analyzer Package

Provides comprehensive data analysis for CSV files:

```python
pm.install_package("https://github.com/vagents-ai/data-analyzer-package.git")
result = pm.execute_package("data-analyzer", file_path="data.csv")
```

**Features:**
- Statistical summaries
- Data quality assessment
- Correlation analysis
- Visualization generation
- Recommendation engine

## Security Considerations

### Sandboxed Execution

- Packages run in isolated execution contexts
- `sys.path` is managed to prevent interference
- Modules are cleaned up after execution

### Best Practices

1. **Only install packages from trusted sources**
2. **Review package code before installation**
3. **Use virtual environments for testing**
4. **Validate input parameters to packages**
5. **Monitor package execution and resource usage**

### Current Limitations

- No automatic dependency installation
- Limited runtime sandboxing
- No digital signature verification
- No automatic security scanning

## Configuration

### Default Directories

- Base directory: `~/.vagents/packages`
- Registry file: `~/.vagents/packages/registry.json`
- Package storage: `~/.vagents/packages/packages/`

### Custom Configuration

```python
# Use custom base directory
pm = PackageManager(base_path="/custom/path")
```

## Error Handling

The package manager provides comprehensive error handling:

```python
try:
    result = pm.execute_package("package-name")
    if "error" in result:
        print(f"Package execution failed: {result['error']}")
except ValueError as e:
    print(f"Package not found: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Integration with VAgents

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
            data=request.data
        )
        return analysis_result
```

## Future Enhancements

- [ ] Dependency resolution and automatic installation
- [ ] Package versioning and compatibility checks
- [ ] Enhanced security with code signing
- [ ] Package marketplace and discovery
- [ ] Performance monitoring and caching
- [ ] Docker-based execution sandboxing
- [ ] Package testing and validation framework

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Implement your changes
4. Add tests and documentation
5. Submit a pull request

## License

This package manager is part of the VAgents project and follows the same license terms.

## Support

For issues and questions:

- Create an issue in the VAgents repository
- Check the documentation and examples
- Review existing packages for implementation patterns

---

*The VAgents Package Manager enables a collaborative ecosystem where developers can easily share and reuse AI agent functionality.*
