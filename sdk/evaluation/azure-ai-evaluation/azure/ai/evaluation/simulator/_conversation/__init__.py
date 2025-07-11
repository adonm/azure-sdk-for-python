# ---------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# ---------------------------------------------------------
# noqa: E402

import copy
import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple, Union, cast
import base64
import re
import jinja2

from azure.ai.evaluation._exceptions import ErrorBlame, ErrorCategory, ErrorTarget, EvaluationException
from azure.ai.evaluation._http_utils import AsyncHttpPipeline
from .._model_tools import LLMBase, OpenAIChatCompletionsModel, RAIClient
from azure.ai.evaluation._common.onedp._client import AIProjectClient
from .._model_tools._template_handler import TemplateParameters
from .constants import ConversationRole


@dataclass
class ConversationTurn:
    """Class to represent a turn in a conversation.

    A "turn" involves only one exchange between the user and the chatbot.

    :param role: The role of the participant in the conversation. Accepted values are
        "user" and "assistant".
    :type role: ~azure.ai.evaluation.simulator._conversation.constants.ConversationRole
    :param name: The name of the participant in the conversation.
    :type name: Optional[str]
    :param message: The message exchanged in the conversation. Defaults to an empty string.
    :type message: str
    :param full_response: The full response.
    :type full_response: Optional[Any]
    :param request: The request.
    :type request: Optional[Any]
    """

    role: "ConversationRole"
    name: Optional[str] = None
    message: str = ""
    full_response: Optional[Dict[str, Any]] = None
    request: Optional[Any] = None

    def to_openai_chat_format(self, reverse: bool = False) -> Dict[str, str]:
        """Convert the conversation turn to the OpenAI chat format.

        OpenAI chat format is a dictionary with two keys: "role" and "content".

        :param reverse: Whether to reverse the conversation turn. Defaults to False.
        :type reverse: bool
        :return: The conversation turn in the OpenAI chat format.
        :rtype: Dict[str, str]
        """
        if reverse is False:
            return {"role": self.role.value, "content": self.message}
        if self.role == ConversationRole.ASSISTANT:
            return {"role": ConversationRole.USER.value, "content": self.message}
        return {"role": ConversationRole.ASSISTANT.value, "content": self.message}

    def to_annotation_format(self, turn_number: int) -> Dict[str, Any]:
        """Convert the conversation turn to an annotation format.

        Annotation format is a dictionary with the following keys:
        - "turn_number": The turn number.
        - "response": The response.
        - "actor": The actor.
        - "request": The request.
        - "full_json_response": The full JSON response.

        :param turn_number: The turn number.
        :type turn_number: int
        :return: The conversation turn in the annotation format.
        :rtype: Dict[str, Any]
        """
        return {
            "turn_number": turn_number,
            "response": self.message,
            "actor": self.role.value if self.name is None else self.name,
            "request": self.request,
            "full_json_response": self.full_response,
        }

    def __str__(self) -> str:
        return f"({self.role.value}): {self.message}"


class ConversationBot:
    """
    A conversation chat bot with a specific name, persona and a sentence that can be used as a conversation starter.

    :param role: The role of the bot in the conversation, either "user" or "assistant".
    :type role: ~azure.ai.evaluation.simulator._conversation.constants.ConversationRole
    :param model: The LLM model to use for generating responses.
    :type model: Union[
        ~azure.ai.evaluation.simulator._model_tools.LLMBase,
        ~azure.ai.evaluation.simulator._model_tools.OpenAIChatCompletionsModel
    ]
    :param conversation_template: A Jinja2 template describing the conversation to generate the prompt for the LLM
    :type conversation_template: str
    :param instantiation_parameters: A dictionary of parameters used to instantiate the conversation template
    :type instantiation_parameters: Dict[str, str]
    """

    def __init__(
        self,
        *,
        role: ConversationRole,
        model: Union[LLMBase, OpenAIChatCompletionsModel],
        conversation_template: str,
        instantiation_parameters: TemplateParameters,
    ) -> None:
        self.role = role
        self.conversation_template_orig = conversation_template
        self.conversation_template: jinja2.Template = jinja2.Template(
            conversation_template, undefined=jinja2.StrictUndefined
        )
        self.persona_template_args = instantiation_parameters
        if self.role == ConversationRole.USER:
            self.name: str = cast(str, self.persona_template_args.get("name", role.value))
        else:
            self.name = cast(str, self.persona_template_args.get("chatbot_name", role.value)) or model.name
        self.model = model

        self.logger = logging.getLogger(repr(self))
        self.conversation_starter: Optional[Union[str, jinja2.Template, Dict]] = None
        if role == ConversationRole.USER:
            if "conversation_starter" in self.persona_template_args:
                conversation_starter_content = self.persona_template_args["conversation_starter"]
                if isinstance(conversation_starter_content, dict):
                    self.conversation_starter = conversation_starter_content
                else:
                    try:
                        self.conversation_starter = jinja2.Template(
                            conversation_starter_content, undefined=jinja2.StrictUndefined
                        )
                    except jinja2.exceptions.TemplateSyntaxError as e:  # noqa: F841
                        self.conversation_starter = conversation_starter_content
            else:
                self.logger.info(
                    "This simulated bot will generate the first turn as no conversation starter is provided"
                )

    async def generate_response(
        self,
        session: Union[AsyncHttpPipeline, AIProjectClient],
        conversation_history: List[ConversationTurn],
        max_history: int,
        turn_number: int = 0,
        session_state: Optional[Dict[str, Any]] = None,
    ) -> Tuple[dict, dict, float, dict]:
        """
        Prompt the ConversationBot for a response.

        :param session: AsyncHttpPipeline to use for the request.
        :type session: AsyncHttpPipeline
        :param conversation_history: The turns in the conversation so far.
        :type conversation_history: List[ConversationTurn]
        :param max_history: Parameters used to query GPT-4 model.
        :type max_history: int
        :param turn_number: Parameters used to query GPT-4 model.
        :type turn_number: int
        :return: The response from the ConversationBot.
        :rtype: Tuple[dict, dict, float, dict]
        """

        # check if this is the first turn and the conversation_starter is not None,
        # return the conversations starter rather than generating turn using LLM
        if turn_number == 0 and self.conversation_starter is not None:
            # if conversation_starter is a dictionary, pass it into samples as is
            if isinstance(self.conversation_starter, dict):
                samples: List[Union[str, jinja2.Template, Dict]] = [self.conversation_starter]
            if isinstance(self.conversation_starter, jinja2.Template):
                samples = [self.conversation_starter.render(**self.persona_template_args)]
            else:
                samples = [self.conversation_starter]
            jailbreak_string = self.persona_template_args.get("jailbreak_string", None)
            if jailbreak_string:
                samples = [f"{jailbreak_string} {samples[0]}"]
            time_taken = 0

            finish_reason = ["stop"]

            parsed_response = {"samples": samples, "finish_reason": finish_reason, "id": None}
            full_response = parsed_response
            return parsed_response, {}, time_taken, full_response

        try:
            prompt = self.conversation_template.render(
                conversation_turns=conversation_history[-max_history:],
                role=self.role.value,
                **self.persona_template_args,
            )
        except Exception:  # pylint: disable=broad-except
            import code

            code.interact(local=locals())

        messages = [{"role": "system", "content": prompt}]

        # The ChatAPI must respond as ASSISTANT, so if this bot is USER, we need to reverse the messages
        if (self.role == ConversationRole.USER) and (isinstance(self.model, (OpenAIChatCompletionsModel))):
            # in here we need to simulate the user, The chatapi only generate turn as assistant and
            # can't generate turn as user
            # thus we reverse all rules in history messages,
            # so that messages produced from the other bot passed here as user messages
            messages.extend([turn.to_openai_chat_format(reverse=True) for turn in conversation_history[-max_history:]])
            prompt_role = ConversationRole.USER.value
        else:
            messages.extend([turn.to_openai_chat_format() for turn in conversation_history[-max_history:]])
            prompt_role = self.role.value

        response = await self.model.get_conversation_completion(
            messages=messages,
            session=session,
            role=prompt_role,
        )

        return response["response"], response["request"], response["time_taken"], response["full_response"]

    def __repr__(self):
        return f"Bot(name={self.name}, role={self.role.name}, model={self.model.__class__.__name__})"


class CallbackConversationBot(ConversationBot):
    """Conversation bot that uses a user provided callback to generate responses.

    :param callback: The callback function to use to generate responses.
    :type callback: Callable
    :param user_template: The template to use for the request.
    :type user_template: str
    :param user_template_parameters: The template parameters to use for the request.
    :type user_template_parameters: Dict
    :param args: Optional arguments to pass to the parent class.
    :type args: Any
    :param kwargs: Optional keyword arguments to pass to the parent class.
    :type kwargs: Any
    """

    def __init__(
        self,
        callback: Callable,
        user_template: str,
        user_template_parameters: TemplateParameters,
        *args,
        **kwargs,
    ) -> None:
        self.callback = callback
        self.user_template = user_template
        self.user_template_parameters = user_template_parameters

        super().__init__(*args, **kwargs)

    async def generate_response(
        self,
        session: Union[AsyncHttpPipeline, AIProjectClient],
        conversation_history: List[Any],
        max_history: int,
        turn_number: int = 0,
        session_state: Optional[Dict[str, Any]] = None,
    ) -> Tuple[dict, dict, float, dict]:
        chat_protocol_message = self._to_chat_protocol(
            self.user_template, conversation_history, self.user_template_parameters
        )
        msg_copy = copy.deepcopy(chat_protocol_message)
        result = {}
        start_time = time.time()
        result = await self.callback(msg_copy, session_state=session_state)
        end_time = time.time()
        if not result:
            result = {
                "messages": [{"content": "Callback did not return a response.", "role": "assistant"}],
                "finish_reason": ["stop"],
                "id": None,
                "template_parameters": {},
            }
        time_taken = end_time - start_time
        try:
            response = {
                "samples": [result["messages"][-1]["content"]],
                "finish_reason": ["stop"],
                "id": None,
            }
        except Exception as exc:
            msg = "User provided callback does not conform to chat protocol standard."
            raise EvaluationException(
                message=msg,
                internal_message=msg,
                target=ErrorTarget.CALLBACK_CONVERSATION_BOT,
                category=ErrorCategory.INVALID_VALUE,
                blame=ErrorBlame.USER_ERROR,
            ) from exc

        return response, {}, time_taken, result

    # Bug 3354264: template is unused in the method - is this intentional?
    def _to_chat_protocol(self, template, conversation_history, template_parameters):  # pylint: disable=unused-argument
        messages = []

        for _, m in enumerate(conversation_history):
            messages.append({"content": m.message, "role": m.role.value})

        return {
            "template_parameters": template_parameters,
            "messages": messages,
            "$schema": "http://azureml/sdk-2-0/ChatConversation.json",
        }


class MultiModalConversationBot(ConversationBot):
    """MultiModal Conversation bot that uses a user provided callback to generate responses.

    :param callback: The callback function to use to generate responses.
    :type callback: Callable
    :param user_template: The template to use for the request.
    :type user_template: str
    :param user_template_parameters: The template parameters to use for the request.
    :type user_template_parameters: Dict
    :param args: Optional arguments to pass to the parent class.
    :type args: Any
    :param kwargs: Optional keyword arguments to pass to the parent class.
    :type kwargs: Any
    """

    def __init__(
        self,
        callback: Callable,
        user_template: str,
        user_template_parameters: TemplateParameters,
        rai_client: Union[RAIClient, AIProjectClient],
        *args,
        **kwargs,
    ) -> None:
        self.callback = callback
        self.user_template = user_template
        self.user_template_parameters = user_template_parameters
        self.rai_client = rai_client

        super().__init__(*args, **kwargs)

    async def generate_response(
        self,
        session: Union[AsyncHttpPipeline, AIProjectClient],
        conversation_history: List[Any],
        max_history: int,
        turn_number: int = 0,
        session_state: Optional[Dict[str, Any]] = None,
    ) -> Tuple[dict, dict, float, dict]:
        previous_prompt = conversation_history[-1]
        chat_protocol_message = await self._to_chat_protocol(conversation_history, self.user_template_parameters)

        # replace prompt with {image.jpg} tags with image content data.
        conversation_history.pop()
        conversation_history.append(
            ConversationTurn(
                role=previous_prompt.role,
                name=previous_prompt.name,
                message=chat_protocol_message["messages"][0]["content"],
                full_response=previous_prompt.full_response,
                request=chat_protocol_message,
            )
        )
        msg_copy = copy.deepcopy(chat_protocol_message)
        result = {}
        start_time = time.time()
        result = await self.callback(msg_copy)
        end_time = time.time()
        if not result:
            result = {
                "messages": [{"content": "Callback did not return a response.", "role": "assistant"}],
                "finish_reason": ["stop"],
                "id": None,
                "template_parameters": {},
            }

        time_taken = end_time - start_time
        try:
            response = {
                "samples": [result["messages"][-1]["content"]],
                "finish_reason": ["stop"],
                "id": None,
            }
        except Exception as exc:
            msg = "User provided callback does not conform to chat protocol standard."
            raise EvaluationException(
                message=msg,
                internal_message=msg,
                target=ErrorTarget.CALLBACK_CONVERSATION_BOT,
                category=ErrorCategory.INVALID_VALUE,
                blame=ErrorBlame.USER_ERROR,
            ) from exc

        return response, chat_protocol_message, time_taken, result

    async def _to_chat_protocol(self, conversation_history, template_parameters):  # pylint: disable=unused-argument
        messages = []

        for _, m in enumerate(conversation_history):
            if "image:" in m.message:
                content = await self._to_multi_modal_content(m.message)
                messages.append({"content": content, "role": m.role.value})
            else:
                messages.append({"content": m.message, "role": m.role.value})

        return {
            "template_parameters": template_parameters,
            "messages": messages,
            "$schema": "http://azureml/sdk-2-0/ChatConversation.json",
        }

    async def _to_multi_modal_content(self, text: str) -> list:
        split_text = re.findall(r"[^{}]+|\{[^{}]*\}", text)
        messages = [
            text.strip("{}").replace("image:", "").strip() if text.startswith("{") else text for text in split_text
        ]
        contents = []
        for msg in messages:
            if msg.startswith("image_understanding/"):
                if isinstance(self.rai_client, RAIClient):
                    encoded_image = await self.rai_client.get_image_data(msg)
                else:
                    response = self.rai_client.red_teams.get_template_parameters_image(path=msg, stream="true")
                    image_data = b"".join(response)
                    encoded_image = base64.b64encode(image_data).decode("utf-8")

                contents.append(
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded_image}"}},
                )
            else:
                contents.append({"type": "text", "text": msg})
        return contents


__all__ = [
    "ConversationRole",
    "ConversationBot",
    "CallbackConversationBot",
    "MultiModalConversationBot",
    "ConversationTurn",
]
