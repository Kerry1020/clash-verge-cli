from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="clash-verge-cli",
    version="1.0.0",
    author="Clash Verge CLI",
    author_email="contact@example.com",
    description="Enhanced CLI for Clash Verge VPN client",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/lingion/clash-verge-cli",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS :: MacOS X",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "clash-verge=clash_verge_cli:cli",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
