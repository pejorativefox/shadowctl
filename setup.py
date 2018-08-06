from setuptools import setup, find_packages


setup(
    name='shadowctl',
    version='0.0.1',
    description='A simple command line tool to manage you local shadowsocks'
                'connection.',
    url='changeme',
    classifiers=[
        'Development Status :: 3 - Alpha'],
    keywords='shadowsocks proxy socks5 vpn',
    packages=['shadowctl'],
    install_requires=['shadowsocks', 'xdg==3.0.2'],
    entry_points={
        'console_scripts': [
            'shadowctl=shadowctl:main']},
    )
