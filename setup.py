from setuptools import setup, find_packages

setup(
    name="ghostrate",
    version="1.0.4",
    description="Audio Steganography & Forensic Tool — Hide and reveal spoken messages in music",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Jawad Amin",
    url="https://ghostrate-xi.vercel.app",
    license="MIT",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    entry_points={
        "console_scripts": [
            "ghostrate=ghostrate.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Multimedia :: Sound/Audio :: Analysis",
        "Topic :: Security :: Cryptography",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
)

