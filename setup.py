#!/usr/bin/env python

import importlib.util

from setuptools import find_namespace_packages, setup

with open("README.rst", encoding="utf-8") as f:
    README = f.read()

spec = importlib.util.spec_from_file_location(
    "circuit_build.version",
    "circuit_build/version.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
VERSION = module.__version__

setup(
    name="circuit-build",
    author="bbp-ou-nse",
    author_email="bbp-ou-nse@groupes.epfl.ch",
    version=VERSION,
    long_description=README,
    long_description_content_type="text/x-rst",
    description="Tool for building circuits",
    url="https://bbpteam.epfl.ch/documentation/projects/circuit-build/latest/index.html",
    project_urls={
        "Tracker": "https://bbpteam.epfl.ch/project/issues/projects/NSETM/issues",
        "Source": "git@bbpgitlab.epfl.ch:nse/circuit-build.git",
    },
    entry_points={"console_scripts": ["circuit-build=circuit_build.cli:cli"]},
    license="BBP-internal-confidential",
    python_requires=">=3.9",
    install_requires=[
        "click>=7.0",
        "jsonschema>=3.2.0",
        "pyyaml>=5.0",
        "snakemake>=6.0",
        # Explicitly pin pulp because snakemake<8.0 is broken with pulp>=2.8.0
        "pulp<2.8",
        "bluepysnap",
    ],
    extras_require={
        "reports": ["snakemake[reports]"],
    },
    packages=find_namespace_packages(include=["circuit_build*"]),
    include_package_data=True,
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
