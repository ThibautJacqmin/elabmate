from pathlib import Path

from setuptools import find_packages, setup

BASE_DIR = Path(__file__).resolve().parent
README = (BASE_DIR / "README.md").read_text(encoding="utf-8")

setup(
    name="elabmate",
    version="0.1.0",
    description="Save to ElabFTW from Python",
    long_description=README,
    long_description_content_type="text/markdown",
    author="ThibautJacqmin",
    packages=find_packages(exclude=("tests", "examples")),
    python_requires=">=3.10",
    install_requires=[
        "elabapi-python",
        "urllib3",
    ],
    extras_require={
        "labmate": ["labmate"],
    },
)
