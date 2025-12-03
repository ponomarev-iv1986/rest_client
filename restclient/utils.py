import json
from json import JSONDecodeError
from typing import Callable, Any

import allure
import curlify2
from httpx import Response


def allure_attach(func: Callable) -> Callable:
    async def wrapper(*args: Any, **kwargs: Any) -> Response:
        body = kwargs.get("json")
        if body:
            allure.attach(
                json.dumps(body, indent=4),
                name="request_body",
                attachment_type=allure.attachment_type.JSON,
            )
        response = await func(*args, **kwargs)
        curl = curlify2.Curlify(response.request).to_curl()
        allure.attach(curl, name="curl", attachment_type=allure.attachment_type.TEXT)
        allure.attach(
            str(response.status_code),
            name="status code",
            attachment_type=allure.attachment_type.TEXT,
        )
        try:
            response_json = response.json()
            allure.attach(
                json.dumps(response_json, indent=4),
                name="response body",
                attachment_type=allure.attachment_type.JSON,
            )
        except JSONDecodeError:
            response_text = response.text
            allure.attach(
                response_text,
                name="response text",
                attachment_type=allure.attachment_type.TEXT,
            )
        return response

    return wrapper
