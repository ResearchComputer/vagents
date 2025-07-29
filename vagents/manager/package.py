"""
Package Manager for VAgents

This module provides functionality to pull and manage code packages from remote git repositories.
Packages are modular functions that can be dynamically loaded and executed, such as code review tools,
data analysis functions, or any other reusable functionality.
"""

import os
import sys
import json
import shutil
import tempfile
import importlib
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, asdict
from urllib.parse import urlparse
import uuid
import inspect
import datetime

try:
    import yaml
except ImportError:
    yaml = None

try:
    from loguru import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)

try:
    from pydantic import BaseModel, Field as PydanticField, validator
except ImportError:
    # Fallback if pydantic is not available
    class BaseModel:
        pass

    def PydanticField(*args, **kwargs):
        return None

    def validator(*args, **kwargs):
        return lambda x: x


@dataclass
class PackageConfig:
    """Configuration for a package"""

    name: str
    version: str
    description: str
    author: str
    repository_url: str
    entry_point: str  # Module.function or Module.Class
    dependencies: List[str] = None
    python_version: str = ">=3.8"
    tags: List[str] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.tags is None:
            self.tags = []


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

    @validator("repository_url")
    def validate_repository_url(cls, v):
        """Validate that repository_url is a valid git URL"""
        parsed = urlparse(v)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("repository_url must be a valid URL")
        return v

    @validator("entry_point")
    def validate_entry_point(cls, v):
        """Validate entry point format"""
        if "." not in v:
            raise ValueError(
                "entry_point must be in format 'module.function' or 'module.Class'"
            )
        return v


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
        """Load the module and execute the entry point function"""
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

            # Execute the function or instantiate and call the class
            if inspect.isclass(target):
                instance = target()
                if hasattr(instance, "__call__"):
                    return instance(*args, **kwargs)
                else:
                    raise TypeError(f"Class {function_name} is not callable")
            elif inspect.isfunction(target):
                return target(*args, **kwargs)
            else:
                raise TypeError(f"{function_name} is neither a function nor a class")

        except Exception as e:
            logger.error(f"Error executing package {self.config.name}: {e}")
            raise


class GitRepository:
    """Git repository operations"""

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
            original_cwd = os.getcwd()
            os.chdir(repo_path)

            result = subprocess.run(
                ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
            )
            return result.stdout.strip()
        except Exception as e:
            logger.error(f"Error getting commit hash for {repo_path}: {e}")
            return None
        finally:
            os.chdir(original_cwd)


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

        package_info = {
            **asdict(config),
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
        self, repo_url: str, branch: str = "main", force: bool = False
    ) -> bool:
        """Install a package from a git repository

        Args:
            repo_url: Git repository URL
            branch: Git branch to use (default: main)
            force: Force reinstall if package already exists

        Returns:
            bool: True if installation successful, False otherwise
        """
        logger.info(f"Installing package from {repo_url}")

        # Create temporary directory for cloning
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            repo_path = temp_path / "repo"

            # Clone the repository
            if not GitRepository.clone(repo_url, repo_path, branch):
                return False

            # Validate package structure
            config = self._validate_package_structure(repo_path)
            if config is None:
                return False

            # Check if package already exists
            if self.registry.is_package_installed(config.name) and not force:
                logger.warning(
                    f"Package {config.name} already installed. Use force=True to reinstall."
                )
                return False

            # Create package installation directory
            package_install_path = self.registry.packages_dir / config.name
            if package_install_path.exists():
                shutil.rmtree(package_install_path)

            # Copy package files
            shutil.copytree(repo_path, package_install_path)

            # Get commit hash
            commit_hash = GitRepository.get_commit_hash(repo_path)

            # Register package
            self.registry.register_package(config, package_install_path, commit_hash)

            logger.info(
                f"Successfully installed package {config.name} v{config.version}"
            )
            return True

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

        repo_url = package_info["repository_url"]

        # Reinstall the package
        return self.install_package(repo_url, branch, force=True)

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
        )

        # Execute in context
        with PackageExecutionContext(package_path, config) as ctx:
            return ctx.load_and_execute(*args, **kwargs)

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

    # Example: Install a package from a git repository
    # pm.install_package("https://github.com/example/code-review-package.git")

    # List packages
    packages = pm.list_packages()
    print("Installed packages:", packages)

    # Execute a package (example)
    # result = pm.execute_package("code-review", repo_path=".")
    # print("Code review result:", result)
