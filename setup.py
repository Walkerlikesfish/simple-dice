from setuptools import setup, find_packages

setup(
    name="simple_dice",
    version="0.1.0",
    description="A simple dice package",
    author="Walker",
    author_email="walkerlikefish@gmail.com",
    packages=find_packages("src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
    ],
)