#
# copyright (c) 2018 east301
#
# This software is released under the MIT License.
# http://opensource.org/licenses/mit-license.php
#
# ==========
# setup.py: installs GridRunner
#

from setuptools import setup


setup(
    name='gpipe',
    use_scm_version=True,
    license='MIT',

    description='GridPipe',
    long_description='GridPipe',
    url='https://github.com/east301/gpipe',

    author='east301',
    author_email='me@east301.net',

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
        'Topic :: Scientific/Engineering :: Information Analysis'
    ],
    keywords='workflow manager grid engine',

    packages=[
        'gpipe',
        'gpipe.commands',
        'gpipe.utils',
        'gpipe.workflow'
    ],
    package_data={
        'gpipe.workflow': [
            'sge/*.sh.j2'
        ]
    },

    install_requires=[
        'PyYAML==3.12',
        'Jinja2==2.10',
        'accessor==0.1',
        'click==6.7',
        'click-help-colors==0.4',
        'colorlog==3.1.2',
        'deepmerge==0.0.4',
        'humanfriendly==4.8',
        'jsonschema==2.6.0',
        'lxml==4.1.1',
        'networkx==2.1',
        'python-dotenv==0.7.1'
    ],

    entry_points="""
        [console_scripts]
        gpipe = gpipe.cli:main

        [gpipe_commands]
        clean = gpipe.commands.clean:main
        run = gpipe.commands.run:main
        cancel = gpipe.commands.cancel:main
        version = gpipe.commands.version:main

        [gpipe_template_filter_factories]
        gpipe_jinja2_filters = gpipe.utils.template:get_jinja2_filters

        [gpipe_executors]
        sge = gpipe.workflow.execution:SGEWorkflowExecutor
    """
)
