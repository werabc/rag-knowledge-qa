"""
统一错误契约：所有失败响应都是 {"error": {"code", "message", "detail"}}
"""

from typing import Any, Dict, Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str,
                 detail: Optional[Dict[str, Any]] = None):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.detail = detail or {}
        super().__init__(message)


_HTTP_CODE_MAP = {
    400: "bad_request",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "payload_too_large",
    422: "invalid_parameters",
    500: "internal_error",
    502: "upstream_error",
}


def _body(code: str, message: str, detail: Any = None) -> Dict[str, Any]:
    return {"error": {"code": code, "message": message, "detail": detail or {}}}


def install_error_handlers(app: FastAPI):
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError):
        return JSONResponse(status_code=exc.status_code,
                            content=_body(exc.code, exc.message, exc.detail))

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError):
        return JSONResponse(status_code=400,
                            content=_body("invalid_parameters", "请求参数不合法",
                                          {"errors": exc.errors()[:5]}))

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException):
        code = _HTTP_CODE_MAP.get(exc.status_code, f"http_{exc.status_code}")
        return JSONResponse(status_code=exc.status_code,
                            content=_body(code, str(exc.detail)))
