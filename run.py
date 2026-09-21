#!/usr/bin/env python3
"""
企业知识库问答系统启动脚本
"""

import uvicorn
import os
from dotenv import load_dotenv

def main():
    # 加载环境变量
    load_dotenv()
    
    # 获取配置
    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("APP_PORT", "8000"))
    debug = os.getenv("DEBUG", "True").lower() == "true"
    
    print(f"🚀 启动企业知识库问答系统...")
    print(f"📍 访问地址: http://{host}:{port}")
    print(f"📚 API文档: http://{host}:{port}/docs")
    print(f"🔧 调试模式: {'开启' if debug else '关闭'}")
    print("-" * 50)
    
    # 启动服务
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )

if __name__ == "__main__":
    main()