from setuptools import setup, find_packages

import bee

requirements = [
    'Twisted==19.10.0',
    'pyasn1==0.4.5',
    'cryptography==3.0',
    'simplejson==3.16.0',
    'requests==2.21.0',
    'zope.interface==5.0.0',
    'PyPDF2==1.26.0',
    'fpdf==1.7.2',
    'passlib==1.7.1',
    'Jinja2==2.10.1',
    'ntlmlib==0.72',
    'bcrypt==3.1.7',
    'hpfeeds==3.0.0']

setup(
    name='bee',
    version=bee.__version__,
    url='',
    author='',
    author_email='',
    description='Bee daemon',
    long_description='A low interaction honeypot intended to be run on internal networks.',
    install_requires=requirements,
    setup_requires=[
        'setuptools_git'
    ],
    license='BSD',
    packages=find_packages(exclude='test'),
    scripts=['bin/beed', 'bin/bee.tac'],
    platforms='any',
    include_package_data=True,
    classifiers=[
        "Development Status :: 5 - Production/Dev",
        "Intended Audience :: Developers",
        "Framework :: Twisted",
        "Topic :: System :: Networking",
        "Topic :: Security",
        "Topic :: System :: Networking :: Monitoring",
        "Natural Language :: English",
        "Operating System :: Unix",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: Apache License",
    ],
)
