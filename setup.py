from __future__ import print_function

try:
    from setuptools import find_packages, setup
except ImportError:
    import sys
    print("Please install 'setuptools' package in order to install this library", file=sys.stderr)
    raise

setup(
    name='amqttrpc',
    version='0.0.1',
    author='kodachi77',
    author_email='--==--',
    packages=find_packages(exclude=['tests']),
    license='MIT',
    keywords='amqtt rpc',
    url='http://github.com/kodachi77/python-amqttrpc',
    description='RPC interface over MQTT',
    long_description='Making JSON-RPC requests from MQTT agents via MQTT',
    install_requires=['amqtt', 'tinyrpc'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9'
    ]
)
