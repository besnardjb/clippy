from setuptools import setup, find_packages

setup(
    name='clippy',
    version='1.0',
    packages=find_packages(where='lib'),
    install_requires=['rich','requests','wikipedia'],
    entry_points={'console_scripts': ['cl = clippy.main:main']},
)
