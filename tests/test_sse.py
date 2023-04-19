import pytest
from sse_starlette.sse import EventSourceResponse, ServerSentEvent


def test_compression_not_implemented():
    response = EventSourceResponse(0)
    with pytest.raises(NotImplementedError):
        response.enable_compression()


@pytest.mark.parametrize(
    "input, expected",
    [
        ("foo", b"data: foo\r\n\r\n"),
        (dict(data="foo", event="bar"), b"event: bar\r\ndata: foo\r\n\r\n"),
        (
            dict(data="foo", event="bar", id="xyz"),
            b"id: xyz\r\nevent: bar\r\ndata: foo\r\n\r\n",
        ),
        (
            dict(data="foo", event="bar", id="xyz", retry=1),
            b"id: xyz\r\nevent: bar\r\ndata: foo\r\nretry: 1\r\n\r\n",
        ),
        (
            dict(comment="a comment"),
            b": a comment\r\n\r\n",
        ),
    ],
)
def test_server_sent_event(input, expected):
    print(input, expected)
    if isinstance(input, str):
        assert ServerSentEvent(input).encode() == expected
    else:
        assert ServerSentEvent(**input).encode() == expected


@pytest.mark.parametrize(
    "stream_sep,line_sep",
    [
        ("\n", "\n"),
        ("\n", "\r"),
        ("\n", "\r\n"),
        ("\r", "\n"),
        ("\r", "\r"),
        ("\r", "\r\n"),
        ("\r\n", "\n"),
        ("\r\n", "\r"),
        ("\r\n", "\r\n"),
    ],
    ids=(
        "stream-LF:line-LF",
        "stream-LF:line-CR",
        "stream-LF:line-CR+LF",
        "stream-CR:line-LF",
        "stream-CR:line-CR",
        "stream-CR:line-CR+LF",
        "stream-CR+LF:line-LF",
        "stream-CR+LF:line-CR",
        "stream-CR+LF:line-CR+LF",
    ),
)
def test_multiline_data(stream_sep, line_sep):
    lines = line_sep.join(["foo", "bar", "xyz"])
    result = ServerSentEvent(lines, event="event", sep=stream_sep).encode()
    assert (
        result
        == "event: event{0}data: foo{0}data: bar{0}data: xyz{0}{0}".format(
            stream_sep
        ).encode()
    )


@pytest.mark.parametrize("sep", ["\n", "\r", "\r\n"], ids=("LF", "CR", "CR+LF"))
def test_custom_sep(sep):
    result = ServerSentEvent("foo", event="event", sep=sep).encode()
    assert result == "event: event{0}data: foo{0}{0}".format(sep).encode()


def test_ping_property():
    response = EventSourceResponse(0)
    default = response.DEFAULT_PING_INTERVAL
    assert response.ping_interval == default
    response.ping_interval = 25
    assert response.ping_interval == 25
    with pytest.raises(TypeError) as ctx:
        response.ping_interval = "ten"

    assert str(ctx.value) == "ping interval must be int"

    with pytest.raises(ValueError):
        response.ping_interval = -42


def test_retry_is_int():
    response = ServerSentEvent(0, retry=1)
    assert response.retry == 1

    with pytest.raises(TypeError) as ctx:
        _ = ServerSentEvent(0, retry="ten").encode()  # type: ignore
    assert str(ctx.value) == "retry argument must be int"
