"""
Seamless TypeSafeClient factory for openjev-1.5b (10.10.27.105:8088)
"""

import json
import httpx2
from typesafe_sdk import TypeSafeClient


class _OpenJevTransport(httpx2.HTTPTransport):
    """
    Ensures Pydantic discriminator 'type' and 'legend' fields are populated
    for 100% strict compatibility with the official TypeSafe SDK models.
    """
    def handle_request(self, request):
        resp = super().handle_request(request)
        if "/v1/systemone" in str(request.url) and resp.status_code == 200:
            data = json.loads(resp.read().decode())
            req_data = json.loads(request.read().decode())
            questions = req_data.get("questions", {})

            if "answers" in data:
                for qid, ans in data["answers"].items():
                    q_spec = questions.get(qid, {})
                    q_type = q_spec.get("type")
                    if q_type:
                        ans["type"] = q_type
                    elif "noul" in ans:
                        ans["type"] = "noul"
                    elif "choice" in ans:
                        ans["type"] = "choice"
                    elif "score" in ans:
                        ans["type"] = "score"

                    if ans.get("type") == "score" and "legend" not in ans:
                        criteria = q_spec.get("criteria", [])
                        ans["legend"] = {str(i): c for i, c in enumerate(criteria)}

            new_content = json.dumps(data).encode()
            headers = [(k, v) for k, v in resp.headers.raw if k.lower() != b"content-length"]
            headers.append((b"content-length", str(len(new_content)).encode()))
            return httpx2.Response(status_code=resp.status_code, headers=headers, content=new_content, request=request)
        return resp


def get_openjev_client(base_url: str = "http://10.10.27.105:8088", api_key: str = "openjev") -> TypeSafeClient:
    """Return a standard TypeSafeClient pre-configured for your local openJev service."""
    return TypeSafeClient(
        api_key=api_key,
        base_url=base_url,
        http_client=httpx2.Client(transport=_OpenJevTransport())
    )
