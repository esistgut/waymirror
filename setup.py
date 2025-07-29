#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(
    name="waymirror",
    version="0.1.0",
    description="Screen capture application for Wayland using FreeDesktop Portal API",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(),
    install_requires=[
        "PyQt6",
        "PyGObject",
        "dbus-python",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "waymirror=main:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: POSIX :: Linux",
        "Topic :: Multimedia :: Video :: Capture",
    ],
)
