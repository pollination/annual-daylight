#!/usr/bin/env python
import sys
import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

with open('requirements.txt') as f:
    requirements = f.read().splitlines()
    requirements = [req.replace('==', '>=') for req in requirements]

with open('extras-requirements.txt') as f:
    extras_requirements = f.read().splitlines()
    extras_requirements = [req.replace('==', '>=') for req in extras_requirements]


# read branch input and remove it from sys.argv
if '--branch' in sys.argv:
    index = sys.argv.index('--branch')
    sys.argv.pop(index)
    branch = sys.argv.pop(index)
else:
    branch = 'master'

name = 'pollination-annual-daylight'
if branch == 'viz':
    name = f'{name}.viz'
elif branch == 'full':
    name = f'{name}.full'


def _clean_version():
    """Make sure the version will not be a local version."""

    def get_version(version):
        tag = str(version.tag)
        return tag

    def empty(version):
        return ''

    return {'local_scheme': get_version, 'version_scheme': empty}


# normal setuptool inputs
setuptools.setup(
    name=name,                                                              # will be used for package name unless it is overwritten using __queenbee__ info.
    author='ladybug-tools',                                                 # the owner account for this package - required if pushed to Pollination
    author_email='info@ladybug.tools',
    packages=setuptools.find_namespace_packages(                            # required - that's how pollination find the package
        include=['pollination.*'], exclude=['tests', '.github']
    ),
    install_requires=requirements,
    extras_require={'viz': extras_requirements},
    use_scm_version=_clean_version,
    setup_requires=['setuptools_scm'],
    url='https://github.com/pollination/annual-daylight',                   # will be translated to home
    project_urls={
        'icon': 'https://raw.githubusercontent.com/ladybug-tools/artwork/master/icons_components/honeybee/png/annualrecipe.png',
        'docker': 'https://hub.docker.com/r/ladybugtools/honeybee-radiance'
    },
    description='Annual daylight recipe for Pollination.',                  # will be used as package description
    long_description=long_description,                                      # will be translated to ReadMe content on Pollination
    long_description_content_type="text/markdown",
    maintainer='mostapha, ladybug-tools',                                   # Package maintainers. For multiple maintainers use comma
    maintainer_email='mostapha@ladybug.tools, info@ladybug.tools',
    keywords='honeybee, radiance, ladybug-tools, daylight, annual-daylight',# will be used as keywords
    license='PolyForm Shield License 1.0.0, https://polyformproject.org/wp-content/uploads/2020/06/PolyForm-Shield-1.0.0.txt',  # the license link should be separated by a comma
    zip_safe=False
)
