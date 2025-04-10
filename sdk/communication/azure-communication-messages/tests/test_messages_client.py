# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import os
from typing import List
from devtools_testutils import recorded_by_proxy
from _decorators import MessagesPreparers
from azure.core.credentials import AccessToken
from azure.communication.messages import NotificationMessagesClient
from azure.communication.messages.models import (
    TextNotificationContent,
    ImageNotificationContent,
    TemplateNotificationContent,
    MessageReceipt,
    MessageTemplate,
    MessageTemplateText,
    MessageTemplateBindings,
    MessageTemplateValue,
    WhatsAppMessageTemplateBindings,
    WhatsAppMessageTemplateBindingsComponent,
)
from _shared.utils import get_http_logging_policy
from _messages_test_case import MessagesRecordedTestCase
from azure.communication.messages._shared.utils import parse_connection_str


class TestNotificationMessageClientForText(MessagesRecordedTestCase):

    @MessagesPreparers.messages_test_decorator
    @recorded_by_proxy
    def test_text_send_message(self):
        phone_number: str = "+14254360097"
        raised = False

        text_options = TextNotificationContent(
            channel_registration_id="75476a19-a68d-4e10-806c-3680f099e069",
            to=[phone_number],
            content="Thanks for your feedback Hello.",
        )

        message_response: MessageReceipt
        message_client: NotificationMessagesClient = self.create_notification_message_client()

        try:
            with message_client:
                message_responses = message_client.send(text_options)
                message_response = message_responses.receipts[0]
        except:
            raised = True
            raise
        assert raised is False
        assert message_response.message_id is not None
        assert message_response.to is not None

    @MessagesPreparers.messages_test_decorator
    @recorded_by_proxy
    def test_template_send_message(self):
        phone_number: str = "+14254360097"
        input_template: MessageTemplate = MessageTemplate(name="cpm_welcome", language="en_US")
        raised = False

        message_client: NotificationMessagesClient = self.create_notification_message_client()

        template_options = TemplateNotificationContent(
            channel_registration_id="75476a19-a68d-4e10-806c-3680f099e069", to=[phone_number], template=input_template
        )

        message_response: MessageReceipt

        try:
            with message_client:
                message_responses = message_client.send(template_options)
                message_response = message_responses.receipts[0]
        except:
            raised = True
            raise
        assert raised is False
        assert message_response.message_id is not None
        assert message_response.to is not None

    @MessagesPreparers.messages_test_decorator
    @recorded_by_proxy
    def test_template_with_parameters_send_message(self):

        phone_number: str = "+14254360097"
        parammeter1 = MessageTemplateText(name="first", text="2")

        input_template: MessageTemplate = MessageTemplate(
            name="sample_shipping_confirmation",
            language="en_us",
            template_values=[parammeter1],
            bindings=WhatsAppMessageTemplateBindings(
                body=[WhatsAppMessageTemplateBindingsComponent(ref_value="first")]
            ),
        )
        raised = False

        template_options = TemplateNotificationContent(
            channel_registration_id="75476a19-a68d-4e10-806c-3680f099e069", to=[phone_number], template=input_template
        )

        message_response: MessageReceipt
        message_client: NotificationMessagesClient = self.create_notification_message_client()

        try:
            with message_client:
                message_responses = message_client.send(template_options)
                message_response = message_responses.receipts[0]
        except:
            raised = True
            raise
        assert raised is False
        assert message_response.message_id is not None
        assert message_response.to is not None

    @MessagesPreparers.messages_test_decorator
    @recorded_by_proxy
    def test_image_send_message(self):
        phone_number: str = "+14254360097"
        input_media_uri: str = "https://aka.ms/acsicon1"
        raised = False

        template_options = ImageNotificationContent(
            channel_registration_id="75476a19-a68d-4e10-806c-3680f099e069", to=[phone_number], media_uri=input_media_uri
        )

        message_response: MessageReceipt
        message_client: NotificationMessagesClient = self.create_notification_message_client()

        try:
            with message_client:
                message_responses = message_client.send(template_options)
                message_response = message_responses.receipts[0]
        except:
            raised = True
            raise
        assert raised is False
        assert message_response.message_id is not None
        assert message_response.to is not None

    @MessagesPreparers.messages_test_decorator
    @recorded_by_proxy
    def test_download_media(self):
        phone_number: str = "+14254360097"
        input_media_id: str = "53a5dbc2-65ec-4b93-b652-b4bcc8830645"
        raised = False
        message_client: NotificationMessagesClient = self.create_notification_message_client()
        try:
            with message_client:
                media_stream = message_client.download_media(input_media_id)
        except:
            raised = True
            raise
        assert raised is False
        assert media_stream is not None
