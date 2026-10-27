"""Adapter failure contracts using simulated transport; no model quality claims."""
import httpx2
import pytest
from agent_framework import Agent
from agent_framework.exceptions import ChatClientException
from agent_framework.openai import OpenAIChatCompletionClient
from openai import AsyncOpenAI, APITimeoutError


@pytest.mark.asyncio
@pytest.mark.parametrize('status', [401, 429, 500])
async def test_provider_failure_is_not_converted_to_an_answer(status):
    requests = []
    def handler(request):
        requests.append(request)
        return httpx2.Response(status, json={'error': {'message': 'synthetic failure', 'code': status}}, headers={'Retry-After':'1'})
    async with AsyncOpenAI(api_key='synthetic-contract-key', base_url='https://provider.invalid/api/v1', max_retries=0, http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handler))) as sdk:
        agent = Agent(client=OpenAIChatCompletionClient(model='synthetic-model', async_client=sdk))
        with pytest.raises(ChatClientException) as raised:
            await agent.run('Synthetic test')
        assert raised.value.__cause__.status_code == status
        assert len(requests) == 1  # No unbounded hidden SDK retry loop.


@pytest.mark.asyncio
async def test_timeout_is_not_converted_to_a_success():
    def handler(request):
        raise httpx2.ReadTimeout('synthetic timeout', request=request)
    async with AsyncOpenAI(api_key='synthetic-contract-key', base_url='https://provider.invalid/api/v1', max_retries=0, timeout=0.1, http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handler))) as sdk:
        agent = Agent(client=OpenAIChatCompletionClient(model='synthetic-model', async_client=sdk))
        with pytest.raises(ChatClientException) as raised:
            await agent.run('Synthetic test')
        assert isinstance(raised.value.__cause__, APITimeoutError)
