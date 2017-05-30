#!/usr/bin/env python
# -*- coding: utf-8 -*-


try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


with open('README.md') as readme_file:
    readme = readme_file.read()

requirements = [
    'futures',
    'celery[redis]',
    'iziconf',
    'requests',
    'flask',
    'Flask>=0.10.1',
    'flask-cors',
    'PyJWT',
    'PyYaml',
    'gitpython',
    'cryptography',
    'celery',
    'flower'
]

test_requirements = [
    "pytest",
    "coverage",
    "pytest-cov",
    "pytest-ordering",
    "requests-mock"
]

setup(
    name='hub2lab-hook',
    version='0.2.7',
    description="hub2lab-hook",
    long_description=readme,
    author="Antoine Legrand",
    author_email='2t.antoine@gmail.com',
    url='https://github.com/ant31/hub2lab-hook',
    packages=[
        'hub2labhook',
        "hub2labhook.api",
        "hub2labhook.jobs"
    ],
    package_dir={'hub2labhook':
                 'hub2labhook'},
    include_package_data=True,
    install_requires=requirements,
    license="Apache License version 2",
    zip_safe=False,
    keywords=['hub2lab-hook'],
    dependency_links=[
        "https://github.com/mher/flower/zipball/master#egg=flower-1.0.0"
        "https://github.com/ant31/iziconf/zipball/master#egg=flower-0.0.3"
    ],
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
    ],
    test_suite='tests',
    tests_require=test_requirements,
)
