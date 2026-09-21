from setuptools import setup, find_packages

setup(
    name="rag-knowledge-qa-system",
    version="1.0.0",
    author="RAG Agent Team",
    description="企业知识库问答系统 - 基于RAG技术的智能问答",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "fastapi==0.104.1",
        "uvicorn[standard]==0.24.0",
        "langchain==0.0.340",
        "langchain-community==0.0.6",
        "langchain-core==0.0.6",
        "chromadb==0.4.18",
        "pypdf2==3.0.1",
        "python-docx==1.1.0",
        "unstructured==0.11.0",
        "sentence-transformers==2.2.2",
        "python-dotenv==1.0.0",
        "pydantic==2.5.2",
        "python-multipart==0.0.6",
    ],
    extras_require={
        "dev": [
            "pytest==7.4.3",
            "black==23.11.0",
            "flake8==6.1.0",
        ],
        "openai": [
            "openai==1.6.1",
            "tiktoken==0.5.2",
        ],
    },
    entry_points={
        "console_scripts": [
            "rag-system=run:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
)