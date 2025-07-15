"""
Tests for vagents.core.module module.
"""
import pytest
from vagents.core.module import VModule, VModuleConfig


class TestVModuleConfig:
    """Test the VModuleConfig class."""

    def test_config_default_values(self):
        """Test default configuration values."""
        config = VModuleConfig()

        assert config.enable_async is False

    def test_config_custom_values(self):
        """Test custom configuration values."""
        config = VModuleConfig(enable_async=True)

        assert config.enable_async is True

    def test_config_is_dataclass(self):
        """Test that VModuleConfig is a proper dataclass."""
        config = VModuleConfig()

        # Should have dataclass fields
        assert hasattr(config, "__dataclass_fields__")
        assert "enable_async" in config.__dataclass_fields__


class TestVModule:
    """Test the VModule class."""

    def test_module_creation(self):
        """Test VModule creation."""
        config = VModuleConfig()

        # Should create without error (abstract class won't be instantiated directly)
        # We'll test with a concrete implementation
        class TestModule(VModule):
            async def forward(self, *args, **kwargs):
                return "test_result"

        module = TestModule(config)
        assert module.config == config

    def test_module_config_assignment(self):
        """Test that config is properly assigned."""
        config = VModuleConfig(enable_async=True)

        class TestModule(VModule):
            async def forward(self, *args, **kwargs):
                return "test_result"

        module = TestModule(config)
        assert module.config.enable_async is True

    def test_module_post_init_called(self):
        """Test that _post_init is called during initialization."""
        config = VModuleConfig()
        post_init_called = False

        class TestModule(VModule):
            def _post_init(self):
                nonlocal post_init_called
                post_init_called = True
                super()._post_init()

            async def forward(self, *args, **kwargs):
                return "test_result"

        module = TestModule(config)
        assert post_init_called is True

    def test_module_abstract_forward(self):
        """Test that forward method is abstract."""
        config = VModuleConfig()

        # Cannot instantiate VModule directly due to abstract method
        with pytest.raises(TypeError):
            VModule(config)

    @pytest.mark.asyncio
    async def test_module_forward_implementation(self):
        """Test forward method implementation."""
        config = VModuleConfig()

        class TestModule(VModule):
            async def forward(self, input_value, multiplier=2):
                return input_value * multiplier

        module = TestModule(config)
        result = await module.forward(5)

        assert result == 10

    @pytest.mark.asyncio
    async def test_module_forward_with_kwargs(self):
        """Test forward method with keyword arguments."""
        config = VModuleConfig()

        class TestModule(VModule):
            async def forward(self, *args, **kwargs):
                return {"args": args, "kwargs": kwargs}

        module = TestModule(config)
        result = await module.forward(1, 2, key="value")

        assert result["args"] == (1, 2)
        assert result["kwargs"] == {"key": "value"}

    @pytest.mark.asyncio
    async def test_module_call_method(self):
        """Test that __call__ method delegates to forward."""
        config = VModuleConfig()

        class TestModule(VModule):
            async def forward(self, value):
                return value * 2

        module = TestModule(config)
        result = await module(10)

        assert result == 20

    @pytest.mark.asyncio
    async def test_module_call_with_args_kwargs(self):
        """Test __call__ method with args and kwargs."""
        config = VModuleConfig()

        class TestModule(VModule):
            async def forward(self, *args, **kwargs):
                return sum(args) + sum(kwargs.values())

        module = TestModule(config)
        result = await module(1, 2, 3, extra=4, bonus=5)

        assert result == 15  # 1+2+3+4+5

    def test_module_async_config_handling(self):
        """Test that async configuration is handled in _post_init."""
        config = VModuleConfig(enable_async=True)

        class TestModule(VModule):
            def __init__(self, config):
                self.post_init_async_enabled = None
                super().__init__(config)

            def _post_init(self):
                self.post_init_async_enabled = self.config.enable_async
                super()._post_init()

            async def forward(self, *args, **kwargs):
                return "test_result"

        module = TestModule(config)
        assert module.post_init_async_enabled is True

    def test_module_inheritance(self):
        """Test that VModule can be properly inherited."""
        config = VModuleConfig()

        class BaseModule(VModule):
            async def forward(self, *args, **kwargs):
                return "base_result"

        class DerivedModule(BaseModule):
            async def forward(self, *args, **kwargs):
                base_result = await super().forward(*args, **kwargs)
                return f"derived_{base_result}"

        module = DerivedModule(config)
        assert isinstance(module, VModule)
        assert isinstance(module, BaseModule)

    @pytest.mark.asyncio
    async def test_module_inheritance_forward(self):
        """Test that inherited forward method works correctly."""
        config = VModuleConfig()

        class BaseModule(VModule):
            async def forward(self, value):
                return value * 2

        class DerivedModule(BaseModule):
            async def forward(self, value):
                base_result = await super().forward(value)
                return base_result + 1

        module = DerivedModule(config)
        result = await module.forward(5)

        assert result == 11  # (5 * 2) + 1


class TestVModuleIntegration:
    """Integration tests for VModule."""

    @pytest.mark.asyncio
    async def test_module_with_complex_logic(self):
        """Test module with complex processing logic."""
        config = VModuleConfig(enable_async=True)

        class ProcessingModule(VModule):
            async def forward(self, data, transform_func=None):
                if transform_func:
                    return [transform_func(item) for item in data]
                return data

        module = ProcessingModule(config)

        # Test with transform function
        result = await module.forward([1, 2, 3, 4], lambda x: x * x)
        assert result == [1, 4, 9, 16]

        # Test without transform function
        result = await module.forward([1, 2, 3, 4])
        assert result == [1, 2, 3, 4]

    @pytest.mark.asyncio
    async def test_module_async_operations(self):
        """Test module with async operations."""
        import asyncio

        config = VModuleConfig(enable_async=True)

        class AsyncModule(VModule):
            async def forward(self, delay, result):
                await asyncio.sleep(delay)
                return result

        module = AsyncModule(config)

        # Test async execution
        result = await module.forward(0.01, "async_result")
        assert result == "async_result"

    @pytest.mark.asyncio
    async def test_module_error_handling(self):
        """Test module error handling."""
        config = VModuleConfig()

        class ErrorModule(VModule):
            async def forward(self, should_error=False):
                if should_error:
                    raise ValueError("Test error")
                return "success"

        module = ErrorModule(config)

        # Test successful execution
        result = await module.forward(False)
        assert result == "success"

        # Test error handling
        with pytest.raises(ValueError, match="Test error"):
            await module.forward(True)

    def test_module_config_modification(self):
        """Test that module config can be modified after creation."""
        config = VModuleConfig(enable_async=False)

        class TestModule(VModule):
            async def forward(self, *args, **kwargs):
                return self.config.enable_async

        module = TestModule(config)
        assert module.config.enable_async is False

        # Modify config
        module.config.enable_async = True
        assert module.config.enable_async is True
