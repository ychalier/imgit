import os
from setuptools import find_packages, setup

with open(os.path.join(os.path.dirname(__file__), 'README.md')) as readme:
    README = readme.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='imgit',
    version='0.1.0',
    packages=find_packages(),
    include_package_data=True,
    license='GNU GPLv3',
    description='Synchronize local folders with Imgur albums.',
    long_description=README,
    url='https://chalier.fr/',
    author='Yohan Chalier',
    author_email='yohan@chalier.fr',
    install_requires=[
        "requests",
        "tqdm"
    ],
)