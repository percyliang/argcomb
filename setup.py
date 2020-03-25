#from distutils.core import setup
import setuptools

with open("README.md", "r") as f:
    long_description = f.read()

setuptools.setup(
    name="argcomb",
    #packages=["argcomb"],
    version="1.0",
    license="MIT",
    description="A simple library for building command-line arguments",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(),
    author="Percy Liang",
    author_email="percyliang@gmail.com",
    url="https://github.com/percyliang/argcomb",
    keywords=["command-line"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=[],
)
