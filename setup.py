# -*- coding: utf-8 -*-
"""
    setup.py
    ~~~~~~~~

    :copyright: (c) 2014, VLEAD. see AUTHORS file for more details.
    :license: MIT License, see LICENSE for more details.
"""

"""
OVPL
----

One VM per Lab - An automated deployment environment to deploy labs as web
applications on different kinds of hosting infrastructure.

This project is part of the Virtual Labs project by MHRD, India.

"""
from setuptools import setup

requires = [
    'tornado==4.3',
    'requests',
    'pymongo',
    'netaddr',
    'sh',
    'boto'
]


setup(
    name='OVPL',
    version='0.1',
    url='https://github.com/vlead/ovpl',
    license='MIT',
    author='VLEAD',
    author_email='engg@virtual-labs.ac.in',
    description='Automated Deployment Service',
    long_description=__doc__,
    # packages=['src', 'config', 'scripts'],
    packages=['src'],
    zip_safe=False,
    platforms='any',
    install_requires=requires,
    include_package_data=True,
    classifiers=[
        'Development Status :: 0.1 - Alpha',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet',
        'Topic :: WWW/HTTP :: Automated:: Deployment :: Cloud :: Hosting',
    ]
)
