import io
import json
from types import SimpleNamespace

from ai_scientist.web.api import ReviewAPI
from ai_scientist.web.server import handler


def request(api, request_bytes):
    class Socket:
        def makefile(self, *args, **kwargs):
            return io.BytesIO(request_bytes)

        def sendall(self, data):
            output.write(data)

    output = io.BytesIO()
    handler(api, "secret")(Socket(), ("127.0.0.1", 1234), SimpleNamespace(server_port=8765))
    return output.getvalue()


def test_review_api_hides_token_hashes(approvals):
    operation = approvals.request("send_email", "account-a", {"body": "Hello"})
    token = approvals.grant(operation.id)
    response = ReviewAPI(approvals.store).get("/api/approvals")
    assert "token_hash" not in response[0]
    assert token not in json.dumps(response)


def test_review_http_requires_auth_and_rejects_mutations(comm_store):
    api = ReviewAPI(comm_store)
    response = request(api, b"GET /api/drafts HTTP/1.0\r\nHost: 127.0.0.1:8765\r\n\r\n")
    assert b"401" in response.splitlines()[0]
    response = request(
        api,
        b"GET /api/drafts HTTP/1.0\r\nHost: 127.0.0.1:8765\r\nAuthorization: Bearer secret\r\n\r\n",
    )
    assert b"200" in response.splitlines()[0]
    response = request(api, b"POST /api/approve HTTP/1.0\r\nHost: 127.0.0.1:8765\r\n\r\n")
    assert b"405" in response.splitlines()[0]


def test_review_rejects_dns_rebinding_and_escapes_data(comm_store):
    api = ReviewAPI(comm_store)
    response = request(
        api,
        b"GET /api/drafts HTTP/1.0\r\nHost: attacker.example\r\n"
        b"Authorization: Bearer secret\r\n\r\n",
    )
    assert b"403" in response.splitlines()[0]
    response = request(api, b"GET /app.js HTTP/1.0\r\nHost: 127.0.0.1:8765\r\n\r\n")
    assert b"content.textContent =" in response
    assert b"Content-Security-Policy" in response
