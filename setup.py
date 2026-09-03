from setuptools import setup, find_packages

setup(
    name="ezcli",
    version="0.2.0",
    packages=find_packages(),
    install_requires=[
        "rich>=12.0.0",
        "textual>=2.0.0",
    ],
    entry_points={
        "console_scripts": [
            "ezcli=ezcli_app.main:main",
        ],
    },
)
