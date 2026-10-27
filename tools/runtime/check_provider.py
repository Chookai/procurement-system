"""Small, paid OpenRouter compatibility probes. Not a RAG evaluation runner."""
import asyncio
import json
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from agent_framework import Agent
from agent_framework.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel
import httpx2

ROOT = Path(__file__).resolve().parents[2]


class Outstanding(BaseModel):
    outstanding: int


async def main():
    load_dotenv(ROOT / 'backend/.env', override=False)
    target = ROOT / 'runtime-results/provider-live.json'
    report = {'timestamp': datetime.now(timezone.utc).isoformat(), 'scope': 'live provider contracts; synthetic prompts; not RAG quality', 'checks': []}
    key = os.getenv('OPENROUTER_API_KEY')
    if not key:
        report['checks'].append({'check': 'credentials', 'status': 'pending', 'reason': 'OPENROUTER_API_KEY not set'})
        target.write_text(json.dumps(report, indent=2)+'\n')
        print('Live provider checks pending: set backend/.env (never paste the key into chat).')
        return 2
    base_url = os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')
    if base_url.rstrip('/') != 'https://openrouter.ai/api/v1':
        raise ValueError('Live probe only permits the approved OpenRouter endpoint')
    model = os.getenv('OPENROUTER_CHAT_MODEL', 'openai/gpt-4.1-mini')
    embedding_model = os.getenv('OPENROUTER_EMBEDDING_MODEL', 'openai/text-embedding-3-small')
    provider = os.getenv('OPENROUTER_PROVIDER', 'openai')
    route = {'provider': {'only': [provider], 'allow_fallbacks': False, 'require_parameters': True}}
    report.update({'base_url': base_url, 'chat_model': model, 'embedding_model': embedding_model, 'routing': route})
    options = {'temperature': 0, 'max_tokens': 200, 'extra_body': route}
    report['http_exchanges'] = []
    async def record_response(response):
        body = json.loads(response.request.content)
        assert body.get('provider') == route['provider'], 'Provider routing was not applied'
        row = {'path': response.request.url.path, 'status': response.status_code, 'stream': body.get('stream', False), 'requested_model': body.get('model'), 'request_id': response.headers.get('x-request-id')}
        if not row['stream'] and response.is_success:
            await response.aread()
            data = response.json()
            row.update({name: data.get(name) for name in ['id', 'model', 'provider', 'usage']})
        report['http_exchanges'].append(row)
    http_client = httpx2.AsyncClient(event_hooks={'response': [record_response]})
    async with AsyncOpenAI(api_key=key, base_url=base_url, timeout=30, max_retries=0, http_client=http_client) as sdk:
        client = OpenAIChatCompletionClient(model=model, async_client=sdk)
        async def probe(name, function):
            start=time.monotonic()
            try:
                details=await function()
                report['checks'].append({'check':name,'status':'passed','seconds':round(time.monotonic()-start,3),'details':details})
            except Exception as error:
                # Never serialize exception bodies, request objects or keys.
                report['checks'].append({'check':name,'status':'failed','error_type':type(error).__name__,'http_status':getattr(error,'status_code',None)})
        async def basic():
            response=await Agent(client=client).run('Reply with exactly: COMPATIBLE',options=options)
            assert response.text.strip()=='COMPATIBLE'
            return {'text':response.text,'usage':response.usage_details,'response_id':response.response_id}
        async def streaming():
            agent=Agent(client=client)
            updates=[]
            async for update in agent.run('Reply with exactly: Four units remain outstanding.',stream=True,options=options):
                if update.text: updates.append(update.text)
            text=''.join(updates)
            assert 'Four units' in text
            return {'text':text,'text_updates':len(updates)}
        async def tools():
            calls=[]
            def get_outstanding(po_id: str) -> int:
                """Read the outstanding quantity for synthetic purchase order PO-COMPAT."""
                assert po_id=='PO-COMPAT'
                calls.append(po_id)
                return 4
            response=await Agent(client=client,tools=[get_outstanding],instructions='Use get_outstanding once to answer. Never invent the quantity.').run('How many units remain for PO-COMPAT? State the numeric quantity.', options=options)
            assert calls==['PO-COMPAT'] and '4' in response.text
            return {'text':response.text,'tool_calls':calls,'usage':response.usage_details,'response_id':response.response_id}
        async def structured():
            response=await Agent(client=client).run('Ten units were ordered, six accepted. Return outstanding quantity.',options={**options,'response_format':Outstanding})
            parsed=Outstanding.model_validate_json(response.text)
            assert parsed.outstanding==4
            return {'parsed':parsed.model_dump(),'usage':response.usage_details,'response_id':response.response_id}
        async def embeddings():
            # Direct SDK adapter: the framework embedding client does not pass provider routing options.
            response=await sdk.embeddings.create(model=embedding_model,input=['PO: ten units ordered.','GR: six units accepted.'],encoding_format='float',extra_body=route)
            vectors=[item.embedding for item in sorted(response.data,key=lambda item:item.index)]
            assert len(vectors)==2 and len(vectors[0])==len(vectors[1])==1536
            assert all(math.isfinite(x) for row in vectors for x in row)
            return {'model':response.model,'dimensions':len(vectors[0]),'count':len(vectors),'usage':response.usage.model_dump(),'request_id':response._request_id}
        for name,function in [('chat',basic),('streaming',streaming),('read_tool',tools),('structured_output',structured),('embeddings',embeddings)]:
            await probe(name,function)
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(report,indent=2,default=str)+'\n')
    print(json.dumps(report,indent=2,default=str))
    return 0 if all(item['status']=='passed' for item in report['checks']) else 1


if __name__=='__main__':
    raise SystemExit(asyncio.run(main()))
