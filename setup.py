from setuptools import setup, find_packages, Extension
from os.path import abspath

setup(
    name="lightweight blockchain",
    description="Implementation of the lightweight blockchain protocol",
    url="https://github.com/utlagi/Lightweight-Blockchain",
    python_requires=">=3.7",
    packages=find_packages(
        exclude=[
            "src_old",
            "thesispaper",
            "references",
            "blockchain_webinterface",
            "src/tests",
            "src/txtfiles",
        ]
    ),
)
