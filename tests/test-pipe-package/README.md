# test-pipe-package

A VAgents package for test-pipe-package.

## Description

A VAgents package: test-pipe-package

## Installation

Install this package using the VAgents package manager:

```bash
vagents pm install https://github.com/yourusername/test-pipe-package.git
```

## Usage

### Command Line Interface

```bash
# Basic usage
vagents pm run test-pipe-package

# With verbose output
vagents pm run test-pipe-package --verbose

# With configuration file
vagents pm run test-pipe-package --config myconfig.json

# Combined options
vagents pm run test-pipe-package --verbose --config myconfig.json

# Using with pipes
cat data.txt | vagents pm run test-pipe-package --verbose
echo "process this" | vagents pm run test-pipe-package

# Using vibe runner (simpler syntax)
vibe run test-pipe-package --verbose
cat results.json | vibe run test-pipe-package --config analysis.yaml
```

### Programmatic Usage

```python
from vagents.manager.package import PackageManager

pm = PackageManager()

# Basic execution
result = pm.execute_package("test-pipe-package", verbose=True, config="myconfig.json")
print(result)

# With input content
content = "data to process"
result = pm.execute_package("test-pipe-package", input=content, verbose=True)
print(result)
```

## Pipe Support

This package supports reading from stdin when used with pipes:

```bash
# Process file content
cat myfile.txt | vibe run test-pipe-package

# Process command output
ls -la | vibe run test-pipe-package --verbose

# Chain with other commands
curl -s https://api.example.com/data | vibe run test-pipe-package --config api.yaml
```

When using pipes, the stdin content is automatically passed to your package's main function as the `input` parameter (also available as `stdin`).

## CLI Arguments

This package supports the following command line arguments:

- `--verbose, -v`: Enable verbose output (flag)
- `--config, -c`: Configuration file path (string)

## Configuration

See `package.yaml` for package configuration, including argument definitions.

## Development

To modify this package:

1. Clone the repository
2. Make your changes to the main function and argument definitions
3. Update the version in `package.yaml`
4. Commit and push changes
5. Users can update with `vagents pm update test-pipe-package`

### Adding New Arguments

To add new CLI arguments, update the `arguments` section in `package.yaml`:

```yaml
arguments:
  - name: "new_arg"
    type: "str"
    help: "Description of the new argument"
    short: "n"
    required: false
    default: null
```

Then update your main function to accept the new parameter.
