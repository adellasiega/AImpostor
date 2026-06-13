"""Test OllamaManager with mocked ollama.chat"""

from unittest.mock import MagicMock, patch

from framework.ollama_manager import OllamaManager
from framework.utils.data_types import WordOutputFormat


class TestOllamaManagerInit:

    def test_creates_with_defaults(self):
        manager = OllamaManager(model_name="llama3.1")

        assert manager.model_name == "llama3.1"
        assert manager.think is False
        assert manager.options == {}

    def test_creates_with_custom_options(self):
        manager = OllamaManager(model_name="llama3.1", think=True, options={"temperature": 0.7})

        assert manager.model_name == "llama3.1"
        assert manager.think is True
        assert manager.options == {"temperature": 0.7}


class TestOllamaManagerAsk:

    @patch("framework.ollama_manager.chat")
    def test_ask_with_simple_prompt(self, mock_chat):
        mock_response = MagicMock()
        mock_response.message.content = "Test response"
        mock_response.message.tool_calls = None
        mock_chat.return_value = mock_response

        manager = OllamaManager(model_name="llama3.1")
        result, tool_calls = manager.ask(prompt="Hello")

        assert result == "Test response"
        assert tool_calls is None
        mock_chat.assert_called_once()

    @patch("framework.ollama_manager.chat")
    def test_ask_with_system_prompt(self, mock_chat):
        mock_response = MagicMock()
        mock_response.message.content = "Response"
        mock_response.message.tool_calls = None
        mock_chat.return_value = mock_response

        manager = OllamaManager(model_name="llama3.1")
        manager.ask(prompt="User message", system_prompt="You are helpful")

        call_args = mock_chat.call_args
        messages = call_args.kwargs["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are helpful"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "User message"

    @patch("framework.ollama_manager.chat")
    def test_ask_with_response_format(self, mock_chat):
        mock_response = MagicMock()
        mock_response.message.content = '{"word": "pizza"}'
        mock_response.message.tool_calls = None
        mock_chat.return_value = mock_response

        manager = OllamaManager(model_name="llama3.1")
        result, _ = manager.ask(prompt="Say a word", response_format=WordOutputFormat)

        assert isinstance(result, WordOutputFormat)
        assert result.word == "pizza"

    @patch("framework.ollama_manager.chat")
    def test_ask_with_tool_calls(self, mock_chat):
        mock_tool_call = MagicMock()
        mock_tool_call.function.name = "test_tool"
        mock_tool_call.function.arguments = {"arg": "value"}

        mock_response = MagicMock()
        mock_response.message.tool_calls = [mock_tool_call]
        mock_chat.return_value = mock_response

        def test_tool(arg):
            pass

        manager = OllamaManager(model_name="llama3.1")
        result, tool_calls = manager.ask(prompt="Test", tools=[test_tool])

        assert result is None
        assert tool_calls == [mock_tool_call]

    @patch("framework.ollama_manager.chat")
    def test_ask_includes_options(self, mock_chat):
        mock_response = MagicMock()
        mock_response.message.content = "Response"
        mock_response.message.tool_calls = None
        mock_chat.return_value = mock_response

        manager = OllamaManager(model_name="llama3.1", think=True, options={"temperature": 0.5})
        manager.ask(prompt="Test")

        call_args = mock_chat.call_args
        assert call_args.kwargs["think"] is True
        assert call_args.kwargs["options"] == {"temperature": 0.5}
