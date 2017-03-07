# coding: utf-8
from setuptools import setup

setup(
    name='watch-rsync',
    version='1.1',
    description='Watch PATH and rsync to DEST',
    author='guyskk',
    author_email='guyskk@qq.com',
    url='https://github.com/guyskk/watch-rsync',
    py_modules=['watch_rsync'],
    entry_points={
        'console_scripts': ['watch-rsync=watch_rsync:main']
    },
    license='MIT',
    install_requires=['sh>=1.0', 'watchdog>=0.6', 'click>=5.0'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX',
        'Programming Language :: Python',
    ],
)
