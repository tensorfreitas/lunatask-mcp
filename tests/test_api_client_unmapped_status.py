"""Unmapped HTTP status handling tests for LunaTaskClient."""
# pyright: reportPrivateUsage=false

from __future__ import annotations

import httpx
import pytest
from pytest_mock import MockerFixture

from lunatask_mcp.api.client import LunaTaskClient
from lunatask_mcp.api.exceptions import LunaTaskAPIError
from lunatask_mcp.config import ServerConfig
from tests.test_api_client_common import DEFAULT_API_URL, TEST_TOKEN

HTTP_IM_A_TEAPOT = 418


class TestLunaTaskClientUnmappedStatus:
    """Tests for unmapped HTTP status codes raising base API error."""

    @pytest.mark.asyncio
    async def test_unmapped_status_raises_api_error(self, mocker: MockerFixture) -> None:
        """HTTP 418 results in LunaTaskAPIError with correct status and no token leakage."""
        config = ServerConfig(
            lunatask_bearer_token=TEST_TOKEN,
            lunatask_base_url=DEFAULT_API_URL,
        )
        client = LunaTaskClient(config)

        # Mock a response whose raise_for_status() raises HTTPStatusError with 418
        mock_response = mocker.Mock()
        mock_response.status_code = HTTP_IM_A_TEAPOT
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "418 I'm a teapot",
            request=mocker.Mock(),
            response=mock_response,
        )

        mock_http_client = mocker.AsyncMock()
        mock_http_client.request.return_value = mock_response
        mocker.patch.object(client, "_get_http_client", return_value=mock_http_client)

        with pytest.raises(LunaTaskAPIError) as exc_info:
            await client.make_request("GET", "ping")

        err = exc_info.value
        assert err.status_code == HTTP_IM_A_TEAPOT
        # Ensure no bearer token appears in the error string
        err_str = str(err)
        assert TEST_TOKEN not in err_str
        assert "Bearer" not in err_str
