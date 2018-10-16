import os
import io

from setuptools import setup, find_packages

from datacast import __version__

here = os.path.abspath(os.path.dirname(__file__))
with io.open(os.path.join(here, 'README.rst'), encoding='utf-8') as fp:
    README = fp.read()


setup(
    name='datacast',
    version=__version__,
    description='Simple way to cast your data.',
    long_description=README,
    url='https://github.com/fatemonk/datacast',
    author='Alexander Rulkov',
    author_email='fatemonk@gmail.com',
    license='MIT',
    classifiers=[
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
    ],
    keywords='config, env, data, cast',
    packages=find_packages(),
    python_requires=">=3.3",
)
