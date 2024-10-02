# Server Sent Events for [Starlette](https://github.com/encode/starlette) and [FastAPI](https://fastapi.tiangolo.com/)

[![Downloads](https://static.pepy.tech/badge/sse-starlette/week)](https://pepy.tech/project/sse-starlette)
[![PyPI Version][pypi-image]][pypi-url]
[![Build Status][build-image]][build-url]
[![Code Coverage][coverage-image]][coverage-url]

> Implements the [Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events) specification.

Background: https://sysid.github.io/server-sent-events/

Installation:

```shell
pip install sse-starlette
```

Usage:

```python
import asyncio
import uvicorn
from starlette.applications import Starlette
from starlette.routing import Route
from sse_starlette.sse import EventSourceResponse

async def numbers(minimum, maximum):
    for i in range(minimum, maximum + 1):
        await asyncio.sleep(0.9)
        yield dict(data=i)

async def sse(request):
    generator = numbers(1, 5)
    return EventSourceResponse(generator)

routes = [
    Route("/", endpoint=sse)
]

app = Starlette(debug=True, routes=routes)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level='info')
```

Output:
![output](output.png)

**Caveat:** SSE streaming does not work in combination with [GZipMiddleware](https://github.com/encode/starlette/issues/20#issuecomment-704106436).

Be aware that for proper server shutdown your application must stop all
running tasks (generators). Otherwise you might experience the following warnings
at shutdown: `Waiting for background tasks to complete. (CTRL+C to force quit)`.

Client disconnects need to be handled in your Request handler (see example.py):
```python
async def endless(req: Request):
    async def event_publisher():
        i = 0
        try:
          while True:
              i += 1
              yield dict(data=i)
              await asyncio.sleep(0.2)
        except asyncio.CancelledError as e:
          _log.info(f"Disconnected from client (via refresh/close) {req.client}")
          # Do any other cleanup, if any
          raise e
    return EventSourceResponse(event_publisher())
```

# Thread Safety with SQLAlchemy Sessions and Similar Objects

The streaming portion of this package is accomplished via anyio TaskGroups. Care
needs to be taken to avoid passing objects that are not thread-safe to generators
you use to yield streaming data.

For example, if you are using SQLAlchemy, you should not use/pass an `AsyncSession`
object to your generator:

```python
# ❌ This can result in "The garbage collector is trying to clean up non-checked-in connection..." errors
async def bad_route():
    async with AsyncSession() as session:
        async def generator():
            async for row in session.execute(select(User)):
                yield dict(data=row)

        return EventSourceResponse(generator)
```

Instead, ensure you create sessions within the generator itself

```python
# ✅ This is safe
async def good_route():
    async def generator():
        async with AsyncSession() as session:
            async for row in session.execute(select(User)):
                yield dict(data=row)

    return EventSourceResponse(generator)
```

## Special use cases
### Customize Ping
By default, the server sends a ping every 15 seconds. You can customize this by:
1. setting the `ping` parameter
2. by changing the `ping` event to a comment event so that it is not visible to the client
```python
@router.get("")
async def handle():
    generator = numbers(1, 100)
    return EventSourceResponse(
        generator,
        headers={"Server": "nini"},
        ping=5,
        ping_message_factory=lambda: ServerSentEvent(**{"comment": "You can't see\r\nthis ping"}),
    )
```
### SSE Send Timeout
To avoid 'hanging' connections in case HTTP connection from a certain client was kept open, but the client
stopped reading from the connection you can specifiy a send timeout (see
[#89](https://github.com/sysid/sse-starlette/issues/89)).
```python
EventSourceResponse(..., send_timeout=5)  # terminate hanging send call after 5s
```

### Fan out Proxies
Fan out proxies usually rely on response being cacheable. To support that, you can set the value of `Cache-Control`.
For example:
```python
return EventSourceResponse(
        generator(), headers={"Cache-Control": "public, max-age=29"}
    )
```
### Error Handling
See example: `examples/error_handling.py`

### Sending Responses without Async Generators
Async generators can expose tricky error and cleanup behavior especially when they are interrupted.

[Background: Cleanup in async generators](https://vorpus.org/blog/some-thoughts-on-asynchronous-api-design-in-a-post-asyncawait-world/#cleanup-in-generators-and-async-generators).

Example [`no_async_generators.py`](https://github.com/sysid/sse-starlette/pull/56#issue-1704495339) shows an alternative implementation
that does not rely on async generators but instead uses memory channels (`examples/no_async_generators.py`).


## Development, Contributing
1. install pdm: `pip install pdm`
2. install dependencies using pipenv: `pdm install -d`.
3. To run tests:

### Makefile
- make sure your virtualenv is active
- check `Makefile` for available commands and development support, e.g. run the unit tests:
```shell
make test
make tox
```

For integration testing you can use the provided examples in `tests` and `examples`.

If you are using Postman, please see: https://github.com/sysid/sse-starlette/issues/47#issuecomment-1445953826


<!-- Badges -->

[pypi-image]: https://badge.fury.io/py/sse-starlette.svg
[pypi-url]: https://pypi.org/project/sse-starlette/
[build-image]: https://github.com/sysid/sse-starlette/actions/workflows/build.yml/badge.svg
[build-url]: https://github.com/sysid/sse-starlette/actions/workflows/build.yml
[coverage-image]: https://codecov.io/gh/sysid/sse-starlette/branch/master/graph/badge.svg
[coverage-url]: https://codecov.io/gh/sysid/sse-starlette
