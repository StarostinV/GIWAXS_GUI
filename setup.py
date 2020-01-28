from setuptools import setup
from pathlib import Path
from setuptools import find_packages


def read(filename: str):
    with open(Path(__file__).parent / filename, mode='r', encoding='utf-8') as f:
        return f.read()


setup(
    name='giwaxs_gui',
    packages=find_packages(),
    version='0.0.5',
    author='Vladimir Starostin',
    author_email='vladimir.starostin@uni-tuebingen.de',
    description='A graphical tool for basic analysis of GIWAXS images.',
    long_description=read('README.md'),
    long_description_content_type='text/markdown',
    license='GPLv3',
    python_requires='>=3.6.*',
    install_requires=[
        'numpy>=1.18.1',
        'matplotlib>=3.1.2',
        'pillow',
        'scipy>=1.4.1',
        'h5py>=2.10.0',
        'PyQt5',
        'pyqtgraph'
    ],
    include_package_data=True,
    keywords='xray python giwaxs scientific-analysis',
    url='http://packages.python.org/giwaxs_gui',
)
