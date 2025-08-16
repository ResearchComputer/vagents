import os
import sys
import json
import shutil
import tempfile
import importlib
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from urllib.parse import urlparse
import inspect
import datetime
import re
from pydantic import BaseModel, Field as PydanticField, field_validator

try:
    import yaml
except ImportError:
    yaml = None

import logging
import asyncio
import threading

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("LOGLEVEL", "WARN").upper())

# Core agent/protocol imports
try:
    from vagents.core import AgentModule, AgentInput, AgentOutput  # type: ignore
except Exception:
    AgentModule = None  # type: ignore
    AgentInput = None  # type: ignore
    AgentOutput = None  # type: ignore


@dataclass
class PackageArgument:
    """Definition of a package command line argument"""

    name: str
    type: str = "str"  # str, int, float, bool, list
    help: str = ""
    default: Any = None
    required: bool = False
    choices: List[str] = None
    short: str = None  # Short form like -h

    def __post_init__(self):
        if self.choices is None:
            self.choices = []


@dataclass
class PackageConfig:
    """Configuration for a package

    For agent packages, the entry point SHOULD be either:
    - A class deriving from `vagents.core.AgentModule` implementing `async forward(input: AgentInput) -> AgentOutput|dict|Any`
    - A function accepting `(input: AgentInput)` and returning `AgentOutput|dict|Any` (sync or async)
    """

    name: str
    version: str
    description: str
    author: str
    repository_url: str
    entry_point: str  # Module.function or Module.Class
    dependencies: List[str] = None
    python_version: str = ">=3.8"
    tags: List[str] = None
    arguments: List[PackageArgument] = None  # CLI arguments this package accepts

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.tags is None:
            self.tags = []
        if self.arguments is None:
            self.arguments = []


class PackageMetadata(BaseModel):
    """Pydantic model for package metadata validation"""

    def __init__(self, **data):
        if hasattr(super(), "__init__"):
            super().__init__(**data)
        else:
            # Fallback for when pydantic is not available
            for key, value in data.items():
                setattr(self, key, value)

        # Manual validation when pydantic is not available
        if not hasattr(self, "name") or not self.name:
            raise ValueError("name is required")
        if not hasattr(self, "version") or not self.version:
            raise ValueError("version is required")
        if not hasattr(self, "description") or not self.description:
            raise ValueError("description is required")
        if not hasattr(self, "author") or not self.author:
            raise ValueError("author is required")
        if not hasattr(self, "repository_url") or not self.repository_url:
            raise ValueError("repository_url is required")
        if not hasattr(self, "entry_point") or not self.entry_point:
            raise ValueError("entry_point is required")

        # Set defaults
        if not hasattr(self, "dependencies"):
            self.dependencies = []
        if not hasattr(self, "python_version"):
            self.python_version = ">=3.8"
        if not hasattr(self, "tags"):
            self.tags = []
        if not hasattr(self, "arguments"):
            self.arguments = []

        # Validate repository URL
        parsed = urlparse(self.repository_url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("repository_url must be a valid URL")

        # Validate entry point
        if "." not in self.entry_point:
            raise ValueError(
                "entry_point must be in format 'module.function' or 'module.Class'"
            )

    name: str = PydanticField(..., description="Package name")
    version: str = PydanticField(..., description="Package version")
    description: str = PydanticField(..., description="Package description")
    author: str = PydanticField(..., description="Package author")
    repository_url: str = PydanticField(..., description="Git repository URL")
    entry_point: str = PydanticField(
        ..., description="Entry point (module.function or module.Class)"
    )
    dependencies: List[str] = PydanticField(
        default=[], description="List of dependencies"
    )
    python_version: str = PydanticField(
        default=">=3.8", description="Python version requirement"
    )
    tags: List[str] = PydanticField(default=[], description="Package tags")
    arguments: List[Dict] = PydanticField(
        default=[], description="CLI arguments definition"
    )

    @field_validator("repository_url")
    @classmethod
    def validate_repository_url(cls, v):
        """Validate that repository_url is a valid git URL"""
        parsed = urlparse(v)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("repository_url must be a valid URL")
        return v

    @field_validator("entry_point")
    @classmethod
    def validate_entry_point(cls, v):
        """Validate entry point format"""
        if "." not in v:
            raise ValueError(
                "entry_point must be in format 'module.function' or 'module.Class'"
            )
        return v


class PackageArgumentParser:
    """Parser for package-specific command line arguments"""

    def __init__(self, config: PackageConfig):
        self.config = config
        self.arguments = self._parse_arguments_from_config()

    def _parse_arguments_from_config(self) -> List[PackageArgument]:
        """Convert configuration arguments to PackageArgument objects"""
        arguments = []

        for arg_def in self.config.arguments:
            if isinstance(arg_def, dict):
                # Convert dict to PackageArgument
                arg = PackageArgument(
                    name=arg_def.get("name", ""),
                    type=arg_def.get("type", "str"),
                    help=arg_def.get("help", ""),
                    default=arg_def.get("default"),
                    required=arg_def.get("required", False),
                    choices=arg_def.get("choices", []),
                    short=arg_def.get("short"),
                )
                arguments.append(arg)
            elif isinstance(arg_def, PackageArgument):
                arguments.append(arg_def)

        return arguments

    def parse_args(self, args: List[str]) -> Dict[str, Any]:
        """Parse command line arguments based on package argument definitions

        Args:
            args: List of command line arguments (e.g., ['--history', '2'])

        Returns:
            Dict of parsed arguments
        """
        import argparse

        parser = argparse.ArgumentParser(
            prog=f"vagents run {self.config.name}",
            description=self.config.description,
            add_help=False,  # We'll handle help ourselves
        )

        # Add package-specific arguments
        for arg in self.arguments:
            kwargs = {
                "help": arg.help,
                "default": arg.default,
                "required": arg.required,
            }

            # Handle different argument types
            if arg.type == "bool":
                kwargs["action"] = "store_true"
            elif arg.type == "int":
                kwargs["type"] = int
            elif arg.type == "float":
                kwargs["type"] = float
            elif arg.type == "list":
                kwargs["nargs"] = "*"
            elif arg.type == "str":
                kwargs["type"] = str

            if arg.choices:
                kwargs["choices"] = arg.choices

            # Add argument with both long and short forms
            arg_names = [f"--{arg.name}"]
            if arg.short:
                arg_names.append(f"-{arg.short}")

            parser.add_argument(*arg_names, **kwargs)

        # Parse the arguments
        try:
            parsed_args = parser.parse_args(args)
            return vars(parsed_args)
        except SystemExit:
            # argparse calls sys.exit on error, we want to handle this gracefully
            raise ValueError(f"Invalid arguments for package {self.config.name}")


class PackageExecutionContext:
    """Context for executing package functions with sandboxing and environment management"""

    def __init__(self, package_path: Path, config: PackageConfig):
        self.package_path = package_path
        self.config = config
        self.loaded_module = None
        self.original_sys_path = sys.path.copy()

    def __enter__(self):
        """Enter execution context"""
        # Add package path to sys.path for imports
        if str(self.package_path) not in sys.path:
            sys.path.insert(0, str(self.package_path))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit execution context and cleanup"""
        # Restore original sys.path
        sys.path = self.original_sys_path

        # Cleanup imported modules if needed
        if self.loaded_module and hasattr(self.loaded_module, "__name__"):
            module_name = self.loaded_module.__name__
            if module_name in sys.modules:
                del sys.modules[module_name]

    def load_and_execute(self, *args, **kwargs):
        """Load the module and execute the entry point.

        Enhanced behavior:
        - If the entry point is an AgentModule subclass, it will be instantiated
          and its async `forward` will be executed with a standard `AgentInput`.
        - If the entry point is a function that accepts an `AgentInput`, it will
          be invoked accordingly (awaited if coroutine) and the result coerced to
          `AgentOutput` when possible.
        - Otherwise, original behavior is preserved (callable with *args/**kwargs).
        """
        try:
            module_name, function_name = self.config.entry_point.rsplit(".", 1)

            # Import the module
            spec = importlib.util.spec_from_file_location(
                module_name, self.package_path / f"{module_name}.py"
            )
            if spec is None:
                raise ImportError(
                    f"Cannot find module {module_name} in {self.package_path}"
                )

            module = importlib.util.module_from_spec(spec)
            self.loaded_module = module
            spec.loader.exec_module(module)

            # Get the function or class
            if not hasattr(module, function_name):
                raise AttributeError(
                    f"Module {module_name} does not have attribute {function_name}"
                )

            target = getattr(module, function_name)

            # Prepare AgentInput if protocols are available
            agent_input = None
            if AgentInput is not None:
                try:
                    # Detect if caller intended stdin-like content
                    payload = {**kwargs}
                    # Normalize CLI-provided stdin to string content if present
                    for k in ("input", "stdin", "content"):
                        if k in payload and not isinstance(payload[k], (str, bytes)):
                            try:
                                payload[k] = str(payload[k])
                            except Exception:
                                payload[k] = ""
                    agent_input = AgentInput(payload=payload)
                except Exception:
                    agent_input = None

            def _coerce_output(value: Any) -> Any:
                """Coerce raw result to AgentOutput if protocol is available."""
                if AgentOutput is None:
                    return value
                if isinstance(value, AgentOutput):
                    return value
                # Wrap common structures into AgentOutput
                input_id = getattr(agent_input, "id", None) if agent_input else None
                if isinstance(value, dict):
                    return AgentOutput(input_id=input_id, result=value)
                # Fallback: wrap scalar/object under "value"
                return AgentOutput(input_id=input_id, result={"value": value})

            async def _maybe_await(coro_or_value: Any) -> Any:
                if inspect.isawaitable(coro_or_value):
                    return await coro_or_value
                return coro_or_value

            def _run_coro_blocking(coro) -> Any:
                """Run an async coroutine to completion, even if a loop is running in this thread.

                Falls back to running in a dedicated thread when needed to avoid 'event loop is running' errors.
                """
                try:
                    return asyncio.run(coro)
                except RuntimeError as e:
                    if "event loop" not in str(e).lower():
                        raise
                    result_box: Dict[str, Any] = {}
                    error_box: Dict[str, BaseException] = {}

                    def _runner():
                        try:
                            result_box["result"] = asyncio.run(coro)
                        except BaseException as exc:  # noqa: BLE001
                            error_box["error"] = exc

                    t = threading.Thread(target=_runner, daemon=True)
                    t.start()
                    t.join()
                    if error_box:
                        raise error_box["error"]
                    return result_box.get("result")

            # Execute the function or instantiate and call the class
            if inspect.isclass(target):
                instance = target()
                # If the instance is an AgentModule, run its async forward with AgentInput
                if AgentModule is not None and isinstance(instance, AgentModule):
                    if agent_input is None:
                        raise TypeError(
                            "Agent protocol not available to construct AgentInput"
                        )
                    result = _run_coro_blocking(instance.forward(agent_input))
                    return _coerce_output(result)

                # Legacy: call class instance if callable
                if hasattr(instance, "__call__"):
                    return instance(*args, **kwargs)
                raise TypeError(f"Class {function_name} is not callable")

            if inspect.isfunction(target):
                # Determine if function explicitly supports AgentInput
                supports_param_name = None
                if agent_input is not None:
                    try:
                        sig = inspect.signature(target)
                        for p in sig.parameters.values():
                            # Only accept explicit agent_input parameter name
                            if p.name == "agent_input":
                                supports_param_name = p.name
                                break
                            # Check type annotation name matches AgentInput
                            ann = p.annotation
                            if ann is not inspect._empty:
                                if AgentInput is not None and ann is AgentInput:
                                    supports_param_name = p.name
                                    break
                                if isinstance(ann, str) and (
                                    ann.endswith("AgentInput") or "AgentInput" in ann
                                ):
                                    supports_param_name = p.name
                                    break
                    except Exception:
                        supports_param_name = None

                if supports_param_name:
                    # Call with AgentInput via keyword
                    call_kwargs = dict(kwargs)
                    call_kwargs[supports_param_name] = agent_input
                    out = target(*args, **call_kwargs)
                    if inspect.isawaitable(out):
                        out = _run_coro_blocking(out)
                    return _coerce_output(out)

                # Legacy behavior: call with *args/**kwargs and return raw result
                # Legacy function signature. If it accepts 'input' or 'stdin', pass stdin text when available
                try:
                    sig = inspect.signature(target)
                    params = sig.parameters
                except Exception:
                    params = {}
                call_kwargs = dict(kwargs)
                if agent_input is not None:
                    stdin_text = None
                    # Try to surface a string for stdin-like parameter
                    for k in ("input", "stdin", "content"):
                        v = call_kwargs.get(k)
                        if isinstance(v, (str, bytes)):
                            stdin_text = v.decode() if isinstance(v, bytes) else v
                            break
                    if stdin_text is None:
                        # As a last resort try to use AgentInput.payload.get("input") etc.
                        for k in ("input", "stdin", "content"):
                            v = (agent_input.payload or {}).get(k)
                            if isinstance(v, (str, bytes)):
                                stdin_text = v.decode() if isinstance(v, bytes) else v
                                break
                    if stdin_text is not None:
                        if "input" in params and "input" not in call_kwargs:
                            call_kwargs["input"] = stdin_text
                        elif "stdin" in params and "stdin" not in call_kwargs:
                            call_kwargs["stdin"] = stdin_text
                        elif "content" in params and "content" not in call_kwargs:
                            call_kwargs["content"] = stdin_text

                out = target(*args, **call_kwargs)
                if inspect.isawaitable(out):
                    out = _run_coro_blocking(out)
                return out

            raise TypeError(f"{function_name} is neither a function nor a class")

        except Exception as e:

            logger.error(f"Error executing package {self.config.name}: {e}")
            raise


class GitRepository:
    """Git repository operations"""

    @staticmethod
    def parse_repo_url_with_subdir(
        repo_url_with_subdir: str,
    ) -> Tuple[str, Optional[str]]:
        """Parse repository URL that may contain a subdirectory path

        Args:
            repo_url_with_subdir: URL like 'git@github.com:user/repo.git/subdir' or
                                 'https://github.com/user/repo.git/subdir'

        Returns:
            Tuple[str, Optional[str]]: (clean_repo_url, subdirectory_path)
        """
        # Handle SSH URLs (git@github.com:user/repo.git/subdir)
        ssh_pattern = r"^(git@[^:]+:[^/]+/[^/]+\.git)(/.*)?$"
        ssh_match = re.match(ssh_pattern, repo_url_with_subdir)
        if ssh_match:
            repo_url = ssh_match.group(1)
            subdir = ssh_match.group(2)
            if subdir:
                subdir = subdir.lstrip("/")
            return repo_url, subdir if subdir else None

        # Handle HTTPS URLs (https://github.com/user/repo.git/subdir)
        https_pattern = r"^(https://[^/]+/[^/]+/[^/]+\.git)(/.*)?$"
        https_match = re.match(https_pattern, repo_url_with_subdir)
        if https_match:
            repo_url = https_match.group(1)
            subdir = https_match.group(2)
            if subdir:
                subdir = subdir.lstrip("/")
            return repo_url, subdir if subdir else None

        # Handle URLs without .git extension
        # SSH: git@github.com:user/repo/subdir
        ssh_no_git_pattern = r"^(git@[^:]+:[^/]+/[^/]+)(/.*)?$"
        ssh_no_git_match = re.match(ssh_no_git_pattern, repo_url_with_subdir)
        if ssh_no_git_match and not ssh_no_git_match.group(1).endswith(".git"):
            base = ssh_no_git_match.group(1)
            subdir_part = ssh_no_git_match.group(2)

            # Split the path part to separate repo from subdir
            if subdir_part:
                parts = subdir_part.strip("/").split("/")
                if parts:
                    # First part might be part of repo name, rest is subdir
                    repo_url = base + ".git"
                    subdir = "/".join(parts) if parts else None
                    return repo_url, subdir
            else:
                return base + ".git", None

        # HTTPS: https://github.com/user/repo/subdir
        https_no_git_pattern = r"^(https://[^/]+/[^/]+/[^/]+)(/.*)?$"
        https_no_git_match = re.match(https_no_git_pattern, repo_url_with_subdir)
        if https_no_git_match and not https_no_git_match.group(1).endswith(".git"):
            base = https_no_git_match.group(1)
            subdir_part = https_no_git_match.group(2)

            if subdir_part:
                parts = subdir_part.strip("/").split("/")
                if parts:
                    repo_url = base + ".git"
                    subdir = "/".join(parts) if parts else None
                    return repo_url, subdir
            else:
                return base + ".git", None

        # If no pattern matches, assume it's a plain repo URL
        return repo_url_with_subdir, None

    @staticmethod
    def clone(repo_url: str, target_path: Path, branch: str = "main") -> bool:
        """Clone a git repository"""
        try:
            cmd = [
                "git",
                "clone",
                "--branch",
                branch,
                "--depth",
                "1",
                repo_url,
                str(target_path),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info(f"Successfully cloned {repo_url} to {target_path}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to clone repository {repo_url}: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Error cloning repository {repo_url}: {e}")
            return False

    @staticmethod
    def extract_subdirectory(repo_path: Path, subdir: str, target_path: Path) -> bool:
        """Extract a subdirectory from a cloned repository

        Args:
            repo_path: Path to the cloned repository
            subdir: Subdirectory path within the repository
            target_path: Target path to copy the subdirectory to

        Returns:
            bool: True if extraction successful, False otherwise
        """
        try:
            subdir_path = repo_path / subdir
            if not subdir_path.exists():
                logger.error(
                    f"Subdirectory {subdir} not found in repository {repo_path}"
                )
                return False

            if not subdir_path.is_dir():
                logger.error(
                    f"Path {subdir} is not a directory in repository {repo_path}"
                )
                return False

            # Copy the subdirectory content to target path
            shutil.copytree(subdir_path, target_path)
            logger.info(
                f"Successfully extracted subdirectory {subdir} to {target_path}"
            )
            return True

        except Exception as e:
            logger.error(f"Error extracting subdirectory {subdir}: {e}")
            return False

    @staticmethod
    def pull(repo_path: Path, branch: str = "main") -> bool:
        """Pull latest changes from git repository"""
        try:
            original_cwd = os.getcwd()
            os.chdir(repo_path)

            # Fetch and pull latest changes
            subprocess.run(
                ["git", "fetch", "origin", branch],
                capture_output=True,
                text=True,
                check=True,
            )
            subprocess.run(
                ["git", "reset", "--hard", f"origin/{branch}"],
                capture_output=True,
                text=True,
                check=True,
            )

            logger.info(f"Successfully pulled latest changes for {repo_path}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to pull repository {repo_path}: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Error pulling repository {repo_path}: {e}")
            return False
        finally:
            os.chdir(original_cwd)

    @staticmethod
    def get_commit_hash(repo_path: Path) -> Optional[str]:
        """Get current commit hash"""
        try:
            # If this is not a git repository, silently return None (common for local installs)
            git_dir = repo_path / ".git"
            if not git_dir.exists():
                return None

            original_cwd = os.getcwd()
            os.chdir(repo_path)

            result = subprocess.run(
                ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            # Keep error logging for real git repos, but downgrade severity to warning
            logger.warning(
                f"Failed to get commit hash for {repo_path}: {e.stderr or e}"
            )
            return None
        except Exception as e:
            logger.warning(f"Error getting commit hash for {repo_path}: {e}")
            return None
        finally:
            try:
                os.chdir(original_cwd)
            except Exception:
                pass


class PackageRegistry:
    """Registry for managing installed packages"""

    def __init__(self, registry_path: Path):
        self.registry_path = registry_path
        self.registry_file = registry_path / "registry.json"
        self.packages_dir = registry_path / "packages"

        # Create directories if they don't exist
        self.registry_path.mkdir(parents=True, exist_ok=True)
        self.packages_dir.mkdir(parents=True, exist_ok=True)

        # Initialize registry file
        if not self.registry_file.exists():
            self._save_registry({})

    def _load_registry(self) -> Dict[str, Dict]:
        """Load the package registry"""
        try:
            with open(self.registry_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading registry: {e}")
            return {}

    def _save_registry(self, registry: Dict[str, Dict]):
        """Save the package registry"""
        try:
            with open(self.registry_file, "w") as f:
                json.dump(registry, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving registry: {e}")

    def register_package(
        self, config: PackageConfig, package_path: Path, commit_hash: str = None
    ):
        """Register a package in the registry"""
        registry = self._load_registry()

        # Convert PackageConfig to dict, handling PackageArgument objects
        config_dict = asdict(config)
        # Convert PackageArgument objects to dicts if they exist
        if "arguments" in config_dict:
            config_dict["arguments"] = [
                asdict(arg) if hasattr(arg, "__dict__") else arg
                for arg in config_dict["arguments"]
            ]

        package_info = {
            **config_dict,
            "installed_path": str(package_path),
            "install_time": str(datetime.datetime.now()),
            "commit_hash": commit_hash,
            "status": "installed",
        }

        registry[config.name] = package_info
        self._save_registry(registry)
        logger.info(f"Registered package {config.name} in registry")

    def unregister_package(self, package_name: str):
        """Remove a package from the registry"""
        registry = self._load_registry()
        if package_name in registry:
            del registry[package_name]
            self._save_registry(registry)
            logger.info(f"Unregistered package {package_name}")

    def get_package_info(self, package_name: str) -> Optional[Dict]:
        """Get information about a registered package"""
        registry = self._load_registry()
        return registry.get(package_name)

    def list_packages(self) -> Dict[str, Dict]:
        """List all registered packages"""
        return self._load_registry()

    def is_package_installed(self, package_name: str) -> bool:
        """Check if a package is installed"""
        return package_name in self._load_registry()


class PackageManager:
    """Main package manager for handling remote git repositories"""

    def __init__(self, base_path: Optional[Path] = None):
        """Initialize package manager

        Args:
            base_path: Base directory for storing packages. Defaults to ~/.vagents/packages
        """
        if base_path is None:
            base_path = Path.home() / ".vagents" / "packages"

        self.base_path = Path(base_path)
        self.registry = PackageRegistry(self.base_path)

        logger.info(f"Initialized PackageManager with base path: {self.base_path}")

    def _validate_package_structure(
        self, package_path: Path
    ) -> Optional[PackageConfig]:
        """Validate package structure and load configuration"""
        config_files = [
            "package.yaml",
            "package.yml",
            "package.json",
            "vagents.yaml",
            "vagents.yml",
        ]

        config_file = None
        for cf in config_files:
            if (package_path / cf).exists():
                config_file = package_path / cf
                break

        if config_file is None:
            logger.error(f"No package configuration found in {package_path}")
            return None

        try:
            if config_file.suffix in [".yaml", ".yml"]:
                if yaml is None:
                    logger.error(
                        "PyYAML is required for YAML configuration files but not installed"
                    )
                    return None
                with open(config_file, "r") as f:
                    config_data = yaml.safe_load(f)
            else:  # JSON
                with open(config_file, "r") as f:
                    config_data = json.load(f)

            # Validate using Pydantic
            metadata = PackageMetadata(**config_data)

            # Convert to PackageConfig
            config = PackageConfig(
                name=metadata.name,
                version=metadata.version,
                description=metadata.description,
                author=metadata.author,
                repository_url=metadata.repository_url,
                entry_point=metadata.entry_point,
                dependencies=metadata.dependencies,
                python_version=metadata.python_version,
                tags=metadata.tags,
                arguments=[
                    PackageArgument(**arg_def) if isinstance(arg_def, dict) else arg_def
                    for arg_def in getattr(metadata, "arguments", [])
                ],
            )

            # Validate entry point file exists
            module_name = config.entry_point.split(".")[0]
            entry_file = package_path / f"{module_name}.py"
            if not entry_file.exists():
                logger.error(f"Entry point file {entry_file} not found")
                return None

            logger.info(f"Validated package configuration for {config.name}")
            return config

        except Exception as e:
            logger.error(f"Error validating package configuration: {e}")
            return None

    def install_package(
        self, repo_url_with_subdir: str, branch: str = "main", force: bool = False
    ) -> bool:
        """Install a package from a git repository, optionally from a subdirectory

        Args:
            repo_url_with_subdir: Git repository URL, optionally with subdirectory path
                                Examples:
                                - git@github.com:user/repo.git
                                - git@github.com:user/repo.git/packages/code-review
                                - https://github.com/user/repo.git/packages/code-review
            branch: Git branch to use (default: main)
            force: Force reinstall if package already exists

        Returns:
            bool: True if installation successful, False otherwise
        """
        logger.info(f"Installing package from {repo_url_with_subdir}")

        # Parse the URL to extract repository URL and subdirectory
        repo_url, subdir = GitRepository.parse_repo_url_with_subdir(
            repo_url_with_subdir
        )
        logger.info(f"Parsed URL - Repository: {repo_url}, Subdirectory: {subdir}")

        # Create temporary directory for cloning
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            repo_path = temp_path / "repo"

            # Clone the repository
            if not GitRepository.clone(repo_url, repo_path, branch):
                return False

            # If a subdirectory is specified, extract it
            package_source_path = repo_path
            if subdir:
                package_source_path = temp_path / "package"
                if not GitRepository.extract_subdirectory(
                    repo_path, subdir, package_source_path
                ):
                    return False

            # Validate package structure
            config = self._validate_package_structure(package_source_path)
            if config is None:
                return False

            # Check if package already exists
            if self.registry.is_package_installed(config.name) and not force:
                logger.warning(
                    f"Package {config.name} already installed. Please remove it first to reinstall."
                )
                return False

            # Create package installation directory
            package_install_path = self.registry.packages_dir / config.name
            if package_install_path.exists():
                shutil.rmtree(package_install_path)

            # Copy package files
            shutil.copytree(package_source_path, package_install_path)

            # Install dependencies (requirements.txt preferred, else config list)
            if not self._install_dependencies_for_package(package_install_path, config):
                # Clean up on failure to keep state consistent
                try:
                    shutil.rmtree(package_install_path, ignore_errors=True)
                finally:
                    return False

            # Get commit hash from the original repo
            commit_hash = GitRepository.get_commit_hash(repo_path)

            # Update config to store the original URL with subdirectory
            config.repository_url = repo_url_with_subdir

            # Register package
            self.registry.register_package(config, package_install_path, commit_hash)

            logger.info(
                f"Successfully installed package {config.name} v{config.version}"
            )
            return True

    def install_local_package(self, local_dir: str, force: bool = False) -> bool:
        """Install a package from a local directory.

        Args:
            local_dir: Path to the local directory containing the package files
            force: Force reinstall if package already exists

        Returns:
            bool: True if installation successful, False otherwise
        """
        try:
            source_path = Path(local_dir).expanduser().resolve()
            if not source_path.exists() or not source_path.is_dir():
                logger.error(
                    f"Local path does not exist or is not a directory: {source_path}"
                )
                return False

            # Validate package structure from local directory
            config = self._validate_package_structure(source_path)
            if config is None:
                return False

            # Check if package already exists
            if self.registry.is_package_installed(config.name) and not force:
                logger.warning(
                    f"Package {config.name} already installed. Please remove it first to reinstall."
                )
                return False

            # Create/replace installation directory
            package_install_path = self.registry.packages_dir / config.name
            if package_install_path.exists():
                shutil.rmtree(package_install_path)

            shutil.copytree(source_path, package_install_path)

            # Install dependencies (requirements.txt preferred, else config list)
            if not self._install_dependencies_for_package(package_install_path, config):
                # Clean up on failure
                try:
                    shutil.rmtree(package_install_path, ignore_errors=True)
                finally:
                    return False

            # Try to capture commit hash if inside a git repo; otherwise None
            commit_hash = GitRepository.get_commit_hash(source_path)

            # Record a file:// URL for provenance
            try:
                config.repository_url = f"file://{str(source_path)}"
            except Exception:
                # Fallback: keep whatever was in the config
                pass

            # Register package
            self.registry.register_package(config, package_install_path, commit_hash)

            logger.info(
                f"Successfully installed local package {config.name} v{config.version} from {source_path}"
            )
            return True

        except Exception as e:
            logger.error(f"Error installing local package from {local_dir}: {e}")
            return False

    def uninstall_package(self, package_name: str) -> bool:
        """Uninstall a package

        Args:
            package_name: Name of the package to uninstall

        Returns:
            bool: True if uninstallation successful, False otherwise
        """
        logger.info(f"Uninstalling package {package_name}")

        package_info = self.registry.get_package_info(package_name)
        if package_info is None:
            logger.error(f"Package {package_name} not found")
            return False

        # Remove package directory
        package_path = Path(package_info["installed_path"])
        if package_path.exists():
            shutil.rmtree(package_path)

        # Unregister package
        self.registry.unregister_package(package_name)

        logger.info(f"Successfully uninstalled package {package_name}")
        return True

    def update_package(self, package_name: str, branch: str = "main") -> bool:
        """Update a package to the latest version

        Args:
            package_name: Name of the package to update
            branch: Git branch to use (default: main)

        Returns:
            bool: True if update successful, False otherwise
        """
        logger.info(f"Updating package {package_name}")

        package_info = self.registry.get_package_info(package_name)
        if package_info is None:
            logger.error(f"Package {package_name} not found")
            return False

        repo_url_with_subdir = package_info["repository_url"]

        # Reinstall the package (this will handle subdirectories automatically)
        return self.install_package(repo_url_with_subdir, branch, force=True)

    def execute_package(self, package_name: str, *args, **kwargs) -> Any:
        """Execute a package function

        Args:
            package_name: Name of the package to execute
            *args: Arguments to pass to the package function
            **kwargs: Keyword arguments to pass to the package function

        Returns:
            Any: Result of the package function execution
        """
        logger.info(f"Executing package {package_name}")

        package_info = self.registry.get_package_info(package_name)
        if package_info is None:
            raise ValueError(f"Package {package_name} not found")

        package_path = Path(package_info["installed_path"])
        if not package_path.exists():
            raise ValueError(f"Package path {package_path} does not exist")

        # Create package config from registry info
        config = PackageConfig(
            name=package_info["name"],
            version=package_info["version"],
            description=package_info["description"],
            author=package_info["author"],
            repository_url=package_info["repository_url"],
            entry_point=package_info["entry_point"],
            dependencies=package_info.get("dependencies", []),
            python_version=package_info.get("python_version", ">=3.8"),
            tags=package_info.get("tags", []),
            arguments=[
                PackageArgument(**arg_def) if isinstance(arg_def, dict) else arg_def
                for arg_def in package_info.get("arguments", [])
            ],
        )

        # Execute in context
        with PackageExecutionContext(package_path, config) as ctx:
            return ctx.load_and_execute(*args, **kwargs)

    def execute_package_with_cli_args(
        self, package_name: str, cli_args: List[str]
    ) -> Any:
        """Execute a package with CLI arguments parsed according to package definition

        Args:
            package_name: Name of the package to execute
            cli_args: List of CLI arguments (e.g., ['--history', '2', '--verbose'])

        Returns:
            Any: Result of the package function execution
        """
        logger.info(f"Executing package {package_name} with CLI args: {cli_args}")

        package_info = self.registry.get_package_info(package_name)
        if package_info is None:
            raise ValueError(f"Package {package_name} not found")

        package_path = Path(package_info["installed_path"])
        if not package_path.exists():
            raise ValueError(f"Package path {package_path} does not exist")

        # Create package config from registry info
        config = PackageConfig(
            name=package_info["name"],
            version=package_info["version"],
            description=package_info["description"],
            author=package_info["author"],
            repository_url=package_info["repository_url"],
            entry_point=package_info["entry_point"],
            dependencies=package_info.get("dependencies", []),
            python_version=package_info.get("python_version", ">=3.8"),
            tags=package_info.get("tags", []),
            arguments=[
                PackageArgument(**arg_def) if isinstance(arg_def, dict) else arg_def
                for arg_def in package_info.get("arguments", [])
            ],
        )

        # Parse CLI arguments based on package configuration
        arg_parser = PackageArgumentParser(config)
        parsed_kwargs = arg_parser.parse_args(cli_args)

        # Execute in context with parsed arguments
        with PackageExecutionContext(package_path, config) as ctx:
            return ctx.load_and_execute(**parsed_kwargs)

    def list_packages(self) -> Dict[str, Dict]:
        """List all installed packages"""
        return self.registry.list_packages()

    def get_package_info(self, package_name: str) -> Optional[Dict]:
        """Get detailed information about a package"""
        return self.registry.get_package_info(package_name)

    def search_packages(
        self, query: str = None, tags: List[str] = None
    ) -> Dict[str, Dict]:
        """Search packages by name, description, or tags

        Args:
            query: Search query for name or description
            tags: List of tags to filter by

        Returns:
            Dict[str, Dict]: Filtered packages
        """
        packages = self.list_packages()
        filtered = {}

        for name, info in packages.items():
            match = True

            # Filter by query
            if query:
                query_lower = query.lower()
                if (
                    query_lower not in name.lower()
                    and query_lower not in info.get("description", "").lower()
                ):
                    match = False

            # Filter by tags
            if tags and match:
                package_tags = set(info.get("tags", []))
                if not set(tags).intersection(package_tags):
                    match = False

            if match:
                filtered[name] = info

        return filtered

    # ---------------------------
    # Dependency installation
    # ---------------------------
    def _install_dependencies_for_package(
        self, package_install_path: Path, config: "PackageConfig"
    ) -> bool:
        """Install package dependencies using pip.

        Preference order:
        1) requirements.txt in the package root
        2) dependencies list from package config

        Behavior control via env vars:
        - VAGENTS_PM_SKIP_DEPS=1 to skip installation
        - VAGENTS_PM_PIP_EXTRA_ARGS to pass extra pip args (e.g. "--extra-index-url ...")
        """
        try:
            if os.environ.get("VAGENTS_PM_SKIP_DEPS", "0") in ("1", "true", "True"):
                logger.info(
                    "Skipping dependency installation due to VAGENTS_PM_SKIP_DEPS"
                )
                return True

            req_file = package_install_path / "requirements.txt"
            deps: List[str] = list(config.dependencies or [])

            if not req_file.exists() and not deps:
                logger.info(
                    f"No dependencies declared for package {config.name}; skipping install"
                )
                return True

            pip_cmd = [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
            ]
            extra = os.environ.get("VAGENTS_PM_PIP_EXTRA_ARGS")
            if extra:
                # naive split; users can quote as needed in env var
                pip_cmd.extend(extra.split())

            if req_file.exists():
                logger.info(f"Installing dependencies from {req_file}...")
                cmd = pip_cmd + ["-r", str(req_file)]
            else:
                logger.info(f"Installing dependencies for {config.name}: {deps}")
                cmd = pip_cmd + deps

            result = subprocess.run(
                cmd,
                cwd=str(package_install_path),
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                logger.error(
                    "Failed to install dependencies for %s: %s\n%s",
                    config.name,
                    result.stderr.strip(),
                    result.stdout.strip(),
                )
                return False

            logger.info(f"Dependencies installed for {config.name}")
            return True
        except Exception as e:
            logger.error(f"Error installing dependencies for {config.name}: {e}")
            return False


# Example usage and built-in packages
def create_code_review_package_example():
    """Example of how to create a code review package"""

    example_config = {
        "name": "code-review",
        "version": "1.0.0",
        "description": "Automated code review tool that analyzes git changes and provides feedback",
        "author": "VAgents Community",
        "repository_url": "https://github.com/vagents-ai/code-review-package.git",
        "entry_point": "code_review.analyze_changes",
        "dependencies": ["gitpython", "ast"],
        "python_version": ">=3.8",
        "tags": ["git", "code-review", "analysis"],
    }

    example_code = '''
import git
import os
from typing import Dict, List

def analyze_changes(*args, **kwargs) -> Dict:
    """
    Analyze git changes and provide code review feedback
    """
    repo_path = kwargs.get("repo_path", ".")

    try:
        repo = git.Repo(repo_path)

        # Get uncommitted changes
        changed_files = [item.a_path for item in repo.index.diff(None)]
        untracked_files = repo.untracked_files

        # Get recent commits
        commits = list(repo.iter_commits(max_count=5))
        recent_changes = [{"hash": commit.hexsha[:8], "message": commit.message.strip()}
                         for commit in commits]

        # Basic analysis
        review_feedback = {
            "changed_files": changed_files,
            "untracked_files": untracked_files,
            "recent_commits": recent_changes,
            "suggestions": [
                "Consider adding tests for new functionality",
                "Ensure all files have appropriate docstrings",
                "Check for consistent code formatting"
            ]
        }

        return review_feedback

    except Exception as e:
        return {"error": f"Failed to analyze repository: {str(e)}"}
'''

    return example_config, example_code


if __name__ == "__main__":
    # Example usage

    # Initialize package manager
    pm = PackageManager()

    # Example: Install a package from a git repository (entire repo)
    # pm.install_package("https://github.com/example/code-review-package.git")

    # Example: Install a package from a subdirectory in a git repository
    # pm.install_package("git@github.com:vagents-ai/packages.git/code-review")
    # pm.install_package("https://github.com/vagents-ai/packages.git/data-analysis")
    # pm.install_package("git@github.com:user/monorepo.git/packages/tools/linter")

    # List packages
    packages = pm.list_packages()
    print("Installed packages:", packages)

    # Execute a package (example)
    # result = pm.execute_package("code-review", repo_path=".")
    # print("Code review result:", result)
