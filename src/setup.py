from setuptools import setup, find_packages

setup(
    name="testcrush",
    description="An assembly-STL compaction toolkit based on VCS-Z01X.",
    version="0.5.0",
    packages=find_packages(),
    install_requires=['toml'],
    url="https://github.com/cad-polito-it/testcrush",
    licence="MIT",
    author="Nick Deligiannis",
    author_email="nd.serv.acc@gmail.com",
    maintainer="Nick Deligiannis",
    maintainer_email="nd.serv.acc@gmail.com",
    include_package_data=True,
    python_requires=">=3.10"
)
