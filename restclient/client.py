import asyncio
import uuid
from json import JSONDecodeError
from typing import Any

import curlify2
import httpx
import structlog
from httpx import Response
from swagger_coverage_py.request_schema_handler import RequestSchemaHandler
from swagger_coverage_py.uri import URI

from restclient.configuration import Configuration
from restclient.utils import allure_attach


class RestClient:
    def __init__(self, configuration: Configuration) -> None:
        self.host = configuration.host
        self.headers = configuration.headers
        self.disable_log = configuration.disable_log
        self.session = httpx.AsyncClient(verify=False)
        self.log = structlog.get_logger(__name__).bind(service="api")

    @staticmethod
    def _get_json(response: Response) -> dict[str, Any]:
        try:
            return response.json()
        except JSONDecodeError:
            return {}

    @allure_attach
    async def _send_request(self, method: str, path: str, **kwargs: Any) -> Response:
        log = self.log.bind(event_id=str(uuid.uuid4()))
        full_url = self.host + path

        if self.disable_log:
            rest_response = await self.session.request(method=method, url=full_url, **kwargs)
            rest_response.raise_for_status()
            return rest_response

        log.msg(
            event="Request",
            method=method,
            full_url=full_url,
            params=kwargs.get("params"),
            headers=kwargs.get("headers"),
            json=kwargs.get("json"),
            data=kwargs.get("data"),
        )

        rest_response = await self.session.request(method=method, url=full_url, **kwargs)
        curl = curlify2.Curlify(rest_response.request).to_curl()
        print(f"CURL: {curl}")

        uri = URI(
            host=self.host,
            base_path="",
            unformatted_path=path,
            uri_params=kwargs.get("params"),
        )
        handler = RequestSchemaHandler(uri, method.lower(), rest_response, kwargs)
        await asyncio.to_thread(handler.write_schema)

        log.msg(
            event="Response",
            status_code=rest_response.status_code,
            headers=rest_response.headers,
            json=self._get_json(rest_response),
        )
        print("_" * 100)

        rest_response.raise_for_status()
        return rest_response

    def update_headers(self, headers: dict[str, Any]) -> None:
        if self.headers:
            self.headers.update(headers)
        else:
            self.headers = headers

    async def get(self, path: str, **kwargs: Any) -> Response:
        return await self._send_request(method="GET", path=path, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> Response:
        return await self._send_request(method="POST", path=path, **kwargs)

    async def put(self, path: str, **kwargs: Any) -> Response:
        return await self._send_request(method="PUT", path=path, **kwargs)

    async def delete(self, path: str, **kwargs: Any) -> Response:
        return await self._send_request(method="DELETE", path=path, **kwargs)
