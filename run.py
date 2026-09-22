#!/usr/bin/env python3
"""RAG 知识库问答系统启动脚本"""

import os

import uvicorn
from dotenv import load_dotenv


def main():
    load_dotenv()
    host = os.getenv("APP_HOST", "127.0.0.1")
    port = int(os.getenv("APP_PORT", "8000"))
    debug = os.getenv("DEBUG", "False").lower() == "true"

    print(f"访问地址: http://{host}:{port}")
    print(f"面板: /ui  API文档: /docs")

    uvicorn.run("app.main:app", host=host, port=port, reload=debug, log_level="info")


if __name__ == "__main__":
    main()
