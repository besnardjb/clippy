from setuptools import setup, find_packages

setup(
    name='clippy',
    version='1.0',
    packages=["clippy"],
    install_requires=['rich','requests'],
    entry_points={'console_scripts': ['cl = clippy.main:main']},
)
