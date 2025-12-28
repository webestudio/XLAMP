#!/usr/bin/env python3
"""
Setup script para XLAMP - LAMP Stack Manager
"""

from setuptools import setup, find_packages
from pathlib import Path

# Leer README
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

# Leer requirements
requirements = []
with open('requirements.txt') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name='xlamp',
    version='1.0.3',
    description='LAMP Stack Manager - Gestión completa del stack LAMP para Linux',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Jorge Bravo',
    author_email='contact@jorgebravo.info',
    url='https://github.com/webestudio/xlamp',
    license='MIT',
    
    packages=find_packages(),
    include_package_data=True,
    
    # Archivos de datos
    package_data={
        'src': [
            'data/*.db',
            'ui/*.css',
            'ui/*.ui',
        ],
        '': [
            'icon.png',
            'resources/*',
            'data/*',
        ],
    },
    
    # Dependencias
    install_requires=requirements,
    
    # Python version
    python_requires='>=3.8',
    
    # Scripts ejecutables
    entry_points={
        'console_scripts': [
            'xlamp=src.main:main',
        ],
        'gui_scripts': [
            'xlamp-gui=src.main:main',
        ],
    },
    
    # Clasificadores PyPI
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: System Administrators',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Topic :: System :: Systems Administration',
        'Topic :: Utilities',
        'Environment :: X11 Applications :: GTK',
    ],
    
    keywords='lamp apache mysql php linux system-administration',
    
    # Metadata adicional
    project_urls={
        'Bug Reports': 'https://github.com/webestudio/xlamp/issues',
        'Source': 'https://github.com/webestudio/xlamp',
    },
)
