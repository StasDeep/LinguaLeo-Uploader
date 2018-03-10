from setuptools import setup, find_packages

with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(
    name='LinguaLeo-Uploader',
    version='1.0',
    description='Shell command for uploading YouTube videos to LinguaLeo',
    author='Stas Glubokiy',
    author_email='glubokiy.stas@gmail.com',
    url='https://github.com/StasDeep/LinguaLeo-Uploader',
    packages=find_packages(),
    install_requires=required,
    entry_points={
        'console_scripts': [
            'leo = leo.main:main',
        ]
    }
)
