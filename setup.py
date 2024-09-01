from setuptools import setup, find_packages

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name='your_project_name',
    version='1.0',
    description='Your project description',
    author='Your Name',
    author_email='your_email@example.com',
    install_requires=requirements,
    packages=find_packages(),
)