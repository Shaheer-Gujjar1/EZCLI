from setuptools import setup, find_packages

setup(
    name="ezcli",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "rich>=12.0.0",
    ],
    entry_points={
        "console_scripts": [
            "ezcli=ezcli_app.main:main",
        ],
    },
)
