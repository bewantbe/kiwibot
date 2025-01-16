from setuptools import setup, find_packages

setup(
    name="kiwibot",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "langchain-anthropic",
        "python-dotenv"
    ]
)