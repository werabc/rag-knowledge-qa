"""
G1 REST 契约测试：端点 × 状态码 × 错误体形状矩阵。
跑法：python -X utf8 scripts/api_contract_test.py
不碰 LLM 网络调用；用上传→删除临时文档验证 201/204/404 生命周期。
"""

import io
import sys

sys.path.insert(0, ".")

from fastapi.testclient import TestClient

from app.main import app

BASE = "/api/v1"
failures = []


def check(name, cond, got=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else f"  <- {got}"))
    if not cond:
        failures.append(name)


def err_shape_ok(r, code):
    body = r.json()
    return (r.status_code == code
            and set(body) == {"error"}
            and {"code", "message", "detail"} <= set(body["error"])
            and body["error"]["code"] != "")


with TestClient(app) as c:
    r = c.get("/health")
    check("GET /health 200", r.status_code == 200, r.text[:120])

    r = c.get("/")
    check("GET / 暴露 api_base", r.status_code == 200
          and r.json().get("api_base") == BASE, r.text[:120])

    r = c.get(f"{BASE}/documents/", params={"page": 1, "size": 2})
    j = r.json()
    check("文档列表分页信封", r.status_code == 200
          and {"items", "total", "page", "size"} <= set(j) and len(j["items"]) <= 2,
          r.text[:150])

    r = c.get(f"{BASE}/documents/", params={"page": 0})
    check("page=0 → 400 invalid_parameters",
          err_shape_ok(r, 400) and r.json()["error"]["code"] == "invalid_parameters",
          r.text[:150])

    r = c.get(f"{BASE}/documents/no-such-doc")
    check("文档 404 document_not_found",
          err_shape_ok(r, 404) and r.json()["error"]["code"] == "document_not_found",
          r.text[:150])

    r = c.delete(f"{BASE}/documents/no-such-doc")
    check("删除不存在文档 → 404", err_shape_ok(r, 404), r.text[:150])

    r = c.post(f"{BASE}/documents/upload",
               files={"file": ("bad.exe", io.BytesIO(b"x"), "application/x-msdownload")})
    check("上传 .exe → 400 unsupported_file_type",
          err_shape_ok(r, 400) and r.json()["error"]["code"] == "unsupported_file_type",
          r.text[:200])

    r = c.post(f"{BASE}/documents/upload",
               files={"file": ("contract_tmp.txt", io.BytesIO("契约测试临时文档。".encode()), "text/plain")})
    ok_up = r.status_code == 200 and "id" in r.json()
    check("上传 .txt → 200 返回文档", ok_up, r.text[:200])
    if ok_up:
        doc_id = r.json()["id"]
        r = c.delete(f"{BASE}/documents/{doc_id}")
        check("删除成功 → 204 无响应体", r.status_code == 204 and r.content == b"",
              f"{r.status_code} {r.text[:80]}")
        r = c.get(f"{BASE}/documents/{doc_id}")
        check("删后再查 → 404", err_shape_ok(r, 404), r.text[:120])

    r = c.get(f"{BASE}/chat/sessions", params={"size": 1})
    j = r.json()
    check("会话列表分页信封", r.status_code == 200
          and {"items", "total", "page", "size"} <= set(j), r.text[:150])

    r = c.get(f"{BASE}/chat/sessions/no-such")
    check("会话 404 session_not_found",
          err_shape_ok(r, 404) and r.json()["error"]["code"] == "session_not_found",
          r.text[:150])

    r = c.post(f"{BASE}/chat/query", json={})
    check("query 缺 question → 400", err_shape_ok(r, 400), r.text[:200])

    fact = "契约测试专用事实-可删除"
    r = c.post(f"{BASE}/chat/memories", json={"fact": fact})
    ok_add = r.status_code == 201 and "id" in r.json()
    check("添加事实 → 201", ok_add, r.text[:150])
    if ok_add:
        fid = r.json()["id"]
        r = c.post(f"{BASE}/chat/memories", json={"fact": fact})
        check("重复事实 → 409 fact_exists_or_empty",
              err_shape_ok(r, 409)
              and r.json()["error"]["code"] == "fact_exists_or_empty", r.text[:150])
        r = c.delete(f"{BASE}/chat/memories/{fid}")
        check("删除事实 → 204", r.status_code == 204, str(r.status_code))
        r = c.delete(f"{BASE}/chat/memories/{fid}")
        check("再删 → 404 memory_not_found",
              err_shape_ok(r, 404)
              and r.json()["error"]["code"] == "memory_not_found", r.text[:150])

    r = c.post(f"{BASE}/chat/memories", json={"fact": ""})
    check("空事实 → 400", err_shape_ok(r, 400), r.text[:150])

    r = c.get(f"{BASE}/nothing-here")
    check("未知 v1 路由 → 404 not_found",
          err_shape_ok(r, 404) and r.json()["error"]["code"] == "not_found",
          r.text[:150])

    r = c.get("/openapi.json")
    paths = set(r.json().get("paths", {}))
    expected = {
        f"{BASE}/documents/upload", f"{BASE}/documents/",
        f"{BASE}/documents/{{doc_id}}", f"{BASE}/documents/{{doc_id}}/chunks",
        f"{BASE}/documents/reindex", f"{BASE}/documents/stats/summary",
        f"{BASE}/chat/query", f"{BASE}/chat/agent", f"{BASE}/chat/stats",
        f"{BASE}/chat/memories", f"{BASE}/chat/memories/{{fact_id}}",
        f"{BASE}/chat/sessions", f"{BASE}/chat/sessions/{{session_id}}",
        f"{BASE}/chat/sessions/{{session_id}}/history",
    }
    check("openapi 全端点在 /api/v1 下", expected <= paths,
          str(sorted(expected - paths)))
    check("无旧 /api/ 路径残留", not any(p.startswith("/api/") and not p.startswith(BASE)
                                     for p in paths),
          str([p for p in paths if p.startswith("/api/") and not p.startswith(BASE)]))

print()
if failures:
    print(f"契约测试失败 {len(failures)} 项: {failures}")
    sys.exit(1)
print("契约测试全部通过")
