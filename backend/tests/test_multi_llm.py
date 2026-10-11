"""Tests for multi-LLM provider support (Phase 3)."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.services.llm_service import (
    get_llm_service, OpenAIService, AnthropicService, CohereService
)


class TestLLMProviderFactory:
    """Test LLM provider factory function."""

    def test_get_openai_service(self):
        """Test getting OpenAI service."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            service = get_llm_service("openai", api_key="test-key")
            assert isinstance(service, OpenAIService)

    def test_get_anthropic_service(self):
        """Test getting Anthropic service."""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            service = get_llm_service("anthropic", api_key="test-key")
            assert isinstance(service, AnthropicService)

    def test_get_cohere_service(self):
        """Test getting Cohere service."""
        with patch.dict("os.environ", {"COHERE_API_KEY": "test-key"}):
            service = get_llm_service("cohere", api_key="test-key")
            assert isinstance(service, CohereService)

    def test_get_unknown_provider(self):
        """Test that unknown provider raises error."""
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            get_llm_service("unknown-provider")

    def test_provider_name_case_insensitive(self):
        """Test that provider names are case-insensitive."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            service = get_llm_service("OpenAI", api_key="test-key")
            assert isinstance(service, OpenAIService)


class TestOpenAIService:
    """Test OpenAI service."""

    def test_missing_api_key_raises_error(self):
        """Test that missing API key raises ValueError."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="OpenAI API key is required"):
                OpenAIService()

    def test_uses_env_var_api_key(self):
        """Test that service uses OPENAI_API_KEY from environment."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            service = OpenAIService()
            assert service.api_key == "test-key"

    def test_accepts_api_key_parameter(self):
        """Test that service accepts api_key parameter."""
        service = OpenAIService(api_key="param-key")
        assert service.api_key == "param-key"

    def test_default_model(self):
        """Test default model selection."""
        service = OpenAIService(api_key="test-key")
        assert service.model == "gpt-3.5-turbo"

    def test_custom_model(self):
        """Test custom model selection."""
        service = OpenAIService(api_key="test-key", model="gpt-4")
        assert service.model == "gpt-4"


class TestAnthropicService:
    """Test Anthropic service."""

    def test_missing_api_key_raises_error(self):
        """Test that missing API key raises ValueError."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="Anthropic API key is required"):
                AnthropicService()

    def test_uses_env_var_api_key(self):
        """Test that service uses ANTHROPIC_API_KEY from environment."""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            service = AnthropicService()
            assert service.api_key == "test-key"

    def test_accepts_api_key_parameter(self):
        """Test that service accepts api_key parameter."""
        service = AnthropicService(api_key="param-key")
        assert service.api_key == "param-key"

    def test_default_model(self):
        """Test default model selection."""
        service = AnthropicService(api_key="test-key")
        assert service.model == "claude-3-haiku-20240307"

    def test_custom_model(self):
        """Test custom model selection."""
        service = AnthropicService(api_key="test-key", model="claude-3-opus-20240229")
        assert service.model == "claude-3-opus-20240229"


class TestCohereService:
    """Test Cohere service."""

    def test_missing_api_key_raises_error(self):
        """Test that missing API key raises ValueError."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="Cohere API key is required"):
                CohereService()

    def test_uses_env_var_api_key(self):
        """Test that service uses COHERE_API_KEY from environment."""
        with patch.dict("os.environ", {"COHERE_API_KEY": "test-key"}):
            service = CohereService()
            assert service.api_key == "test-key"

    def test_accepts_api_key_parameter(self):
        """Test that service accepts api_key parameter."""
        service = CohereService(api_key="param-key")
        assert service.api_key == "param-key"

    def test_default_model(self):
        """Test default model selection."""
        service = CohereService(api_key="test-key")
        assert service.model == "command-light"

    def test_custom_model(self):
        """Test custom model selection."""
        service = CohereService(api_key="test-key", model="command")
        assert service.model == "command"


class TestLLMServiceAbstractMethods:
    """Test that all services implement required abstract methods."""

    def test_openai_has_generate_response(self):
        """Test that OpenAI service has generate_response method."""
        service = OpenAIService(api_key="test-key")
        assert hasattr(service, "generate_response")
        assert callable(service.generate_response)

    def test_openai_has_stream_response(self):
        """Test that OpenAI service has stream_response method."""
        service = OpenAIService(api_key="test-key")
        assert hasattr(service, "stream_response")
        assert callable(service.stream_response)

    def test_anthropic_has_generate_response(self):
        """Test that Anthropic service has generate_response method."""
        service = AnthropicService(api_key="test-key")
        assert hasattr(service, "generate_response")
        assert callable(service.generate_response)

    def test_anthropic_has_stream_response(self):
        """Test that Anthropic service has stream_response method."""
        service = AnthropicService(api_key="test-key")
        assert hasattr(service, "stream_response")
        assert callable(service.stream_response)

    def test_cohere_has_generate_response(self):
        """Test that Cohere service has generate_response method."""
        service = CohereService(api_key="test-key")
        assert hasattr(service, "generate_response")
        assert callable(service.generate_response)

    def test_cohere_has_stream_response(self):
        """Test that Cohere service has stream_response method."""
        service = CohereService(api_key="test-key")
        assert hasattr(service, "stream_response")
        assert callable(service.stream_response)


class TestSystemPrompt:
    """Test that system prompts are consistent across services."""

    def test_openai_system_prompt(self):
        """Test OpenAI system prompt."""
        service = OpenAIService(api_key="test-key")
        assert "security-conscious" in service.SYSTEM_PROMPT
        assert "untrusted data" in service.SYSTEM_PROMPT
        assert "cite" in service.SYSTEM_PROMPT.lower()

    def test_anthropic_system_prompt(self):
        """Test Anthropic system prompt."""
        service = AnthropicService(api_key="test-key")
        assert "security-conscious" in service.SYSTEM_PROMPT
        assert "untrusted data" in service.SYSTEM_PROMPT
        assert "cite" in service.SYSTEM_PROMPT.lower()

    def test_cohere_system_prompt(self):
        """Test Cohere system prompt."""
        service = CohereService(api_key="test-key")
        assert "security-conscious" in service.SYSTEM_PROMPT
        assert "untrusted data" in service.SYSTEM_PROMPT
        assert "cite" in service.SYSTEM_PROMPT.lower()

    def test_system_prompts_match(self):
        """Test that all services use the same system prompt."""
        openai_service = OpenAIService(api_key="test-key")
        anthropic_service = AnthropicService(api_key="test-key")
        cohere_service = CohereService(api_key="test-key")

        assert openai_service.SYSTEM_PROMPT == anthropic_service.SYSTEM_PROMPT
        assert anthropic_service.SYSTEM_PROMPT == cohere_service.SYSTEM_PROMPT


class TestProviderModelSelection:
    """Test model selection and defaults for each provider."""

    def test_openai_supports_multiple_models(self):
        """Test that OpenAI service accepts various models."""
        models = ["gpt-4", "gpt-3.5-turbo", "gpt-3.5-turbo-16k"]
        for model in models:
            service = OpenAIService(api_key="test-key", model=model)
            assert service.model == model

    def test_anthropic_supports_multiple_models(self):
        """Test that Anthropic service accepts various models."""
        models = [
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307"
        ]
        for model in models:
            service = AnthropicService(api_key="test-key", model=model)
            assert service.model == model

    def test_cohere_supports_multiple_models(self):
        """Test that Cohere service accepts various models."""
        models = ["command", "command-light", "command-nightly"]
        for model in models:
            service = CohereService(api_key="test-key", model=model)
            assert service.model == model
