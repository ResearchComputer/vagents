"""
Tests for vagents.utils.cli module.
"""
import pytest
import dataclasses
import inspect
from typing import Optional
from vagents.utils.cli import dataclass_to_cli


@dataclasses.dataclass
class SampleConfig:
    """Sample configuration dataclass for testing."""

    name: str = "default"
    count: int = 10
    enabled: bool = True
    description: Optional[str] = None


@dataclasses.dataclass
class ComplexConfig:
    """Complex configuration dataclass for testing."""

    database_url: str
    max_connections: int = 100
    timeout: float = 30.0
    features: Optional[list] = None


class TestDataclassToCli:
    """Test the dataclass_to_cli decorator."""

    def test_basic_function_decoration(self):
        """Test decorating a basic function with dataclass parameter."""

        def sample_function(config: SampleConfig):
            return f"Name: {config.name}, Count: {config.count}"

        wrapped_func = dataclass_to_cli(sample_function)

        # Should return a callable
        assert callable(wrapped_func)

    def test_function_with_dataclass_and_other_params(self):
        """Test decorating function with dataclass and other parameters."""

        def complex_function(
            extra_param: str, config: SampleConfig, another_param: int = 5
        ):
            return f"{extra_param}: {config.name} x {another_param}"

        wrapped_func = dataclass_to_cli(complex_function)

        assert callable(wrapped_func)

    def test_wrapped_function_call_with_defaults(self):
        """Test calling wrapped function with default values."""

        def simple_function(config: SampleConfig):
            return config.name

        wrapped_func = dataclass_to_cli(simple_function)

        # Call with default values
        result = wrapped_func()

        assert result == "default"

    def test_wrapped_function_call_with_kwargs(self):
        """Test calling wrapped function with keyword arguments."""

        def simple_function(config: SampleConfig):
            return f"{config.name}-{config.count}"

        wrapped_func = dataclass_to_cli(simple_function)

        # Call with overridden values
        result = wrapped_func(name="test", count=20)

        assert result == "test-20"

    def test_wrapped_function_with_extra_params(self):
        """Test wrapped function with extra parameters."""

        def function_with_extras(
            prefix: str, config: SampleConfig, suffix: str = "end"
        ):
            return f"{prefix}-{config.name}-{suffix}"

        wrapped_func = dataclass_to_cli(function_with_extras)

        # Call with extra parameters
        result = wrapped_func(prefix="start", name="middle", suffix="finish")

        assert result == "start-middle-finish"

    def test_dataclass_field_filtering(self):
        """Test that only dataclass fields are used for configuration."""

        def test_function(config: SampleConfig):
            return config.enabled

        wrapped_func = dataclass_to_cli(test_function)

        # Should work with dataclass fields
        result = wrapped_func(enabled=False)
        assert result is False

        # Non-dataclass fields should not affect the config
        result = wrapped_func(enabled=True, non_field="ignored")
        assert result is True

    def test_complex_dataclass(self):
        """Test with a more complex dataclass."""

        def database_function(config: ComplexConfig):
            return f"DB: {config.database_url}, Connections: {config.max_connections}"

        wrapped_func = dataclass_to_cli(database_function)

        result = wrapped_func(
            database_url="postgresql://localhost:5432/test", max_connections=50
        )

        assert "postgresql://localhost:5432/test" in result
        assert "50" in result

    def test_signature_inspection(self):
        """Test that the function signature is properly inspected."""

        def multi_param_function(x: int, config: SampleConfig, y: str = "default"):
            return f"{x}-{config.name}-{y}"

        wrapped_func = dataclass_to_cli(multi_param_function)

        # Test signature inspection worked correctly
        result = wrapped_func(x=42, name="test", y="custom")
        assert result == "42-test-custom"

    def test_no_dataclass_parameter(self):
        """Test behavior when function has no dataclass parameter."""

        def no_dataclass_function(x: int, y: str):
            return f"{x}-{y}"

        # Should handle gracefully or raise appropriate error
        try:
            wrapped_func = dataclass_to_cli(no_dataclass_function)
            # If it doesn't raise an error, test that it works
            result = wrapped_func(x=1, y="test")
            assert result == "1-test"
        except (IndexError, AttributeError):
            # This is acceptable behavior for edge case
            pass

    def test_multiple_dataclass_parameters(self):
        """Test function with multiple dataclass parameters."""

        @dataclasses.dataclass
        class SecondConfig:
            value: int = 100

        def multi_dataclass_function(config1: SampleConfig, config2: SecondConfig):
            return f"{config1.name}-{config2.value}"

        wrapped_func = dataclass_to_cli(multi_dataclass_function)

        # Should use the first dataclass found
        result = wrapped_func(name="test")
        assert "test" in result

    def test_wrapped_function_preserves_behavior(self):
        """Test that wrapped function preserves original function behavior."""

        def original_function(config: SampleConfig):
            if config.enabled:
                return config.count * 2
            else:
                return 0

        wrapped_func = dataclass_to_cli(original_function)

        # Test enabled=True
        result1 = wrapped_func(count=5, enabled=True)
        assert result1 == 10

        # Test enabled=False
        result2 = wrapped_func(count=5, enabled=False)
        assert result2 == 0

    def test_optional_fields(self):
        """Test handling of optional fields in dataclass."""

        def optional_function(config: SampleConfig):
            return config.description or "no description"

        wrapped_func = dataclass_to_cli(optional_function)

        # Test with None (default)
        result1 = wrapped_func()
        assert result1 == "no description"

        # Test with provided value
        result2 = wrapped_func(description="custom description")
        assert result2 == "custom description"

    def test_dataclass_fields_access(self):
        """Test that dataclass fields are properly accessed."""

        def field_access_function(config: ComplexConfig):
            fields = list(config.__dataclass_fields__.keys())
            return len(fields)

        wrapped_func = dataclass_to_cli(field_access_function)

        result = wrapped_func(database_url="test://db")

        # Should return number of fields in ComplexConfig
        expected_fields = len(ComplexConfig.__dataclass_fields__)
        assert result == expected_fields

    def test_parameter_ordering(self):
        """Test that parameter ordering is preserved."""

        def ordered_function(a: str, config: SampleConfig, b: int, c: str = "default"):
            return f"{a}-{config.name}-{b}-{c}"

        wrapped_func = dataclass_to_cli(ordered_function)

        result = wrapped_func(a="first", name="middle", b=2, c="last")

        assert result == "first-middle-2-last"

    def test_kwargs_separation(self):
        """Test that kwargs are properly separated between dataclass and other params."""

        def separation_function(prefix: str, config: SampleConfig):
            return f"{prefix}:{config.name}:{config.count}"

        wrapped_func = dataclass_to_cli(separation_function)

        result = wrapped_func(
            prefix="test",  # Non-dataclass param
            name="config",  # Dataclass param
            count=42,  # Dataclass param
        )

        assert result == "test:config:42"

    def test_edge_case_empty_kwargs(self):
        """Test edge case with empty kwargs."""

        def empty_kwargs_function(config: SampleConfig):
            return config.name

        wrapped_func = dataclass_to_cli(empty_kwargs_function)

        # Should work with no arguments (use defaults)
        result = wrapped_func()

        assert result == "default"

    def test_type_preservation(self):
        """Test that parameter types are preserved."""

        def type_function(config: SampleConfig):
            return type(config.count).__name__

        wrapped_func = dataclass_to_cli(type_function)

        result = wrapped_func(count=42)

        assert result == "int"
