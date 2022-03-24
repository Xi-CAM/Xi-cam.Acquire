"""
Usage: pip install -e .
       python setup.py install
       python setup.py bdist_wheel
       python setup.py sdist bdist_egg
       twine upload dist/*
"""

from setuptools import setup

setup(
    name='xicam.Acquire',

    # Versions should comply with PEP440.  For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    version='0.1.0',

    description="Xi-CAM Acquire Plugin",
    long_description="Supports acquisition of data",
    long_description_content_type='text/markdown',

    # The project's main homepage.
    url='https://github.com/ronpandolfi/Xi-cam',

    # Author details
    author='Ronald J Pandolfi',
    author_email='ronpandolfi@lbl.gov',

    # Choose your license
    license='BSD',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 4 - Beta',

        # Indicate who your project is intended for
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Physics',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: BSD License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 3.6'
    ],

    # What does your project relate to?
    keywords='synchrotron analysis x-ray scattering tomography ',

    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages().
    packages=['xicam.Acquire'],

    package_dir={},

    # Alternatively, if you want to distribute just a my_module.py, uncomment
    # this:
    # py_modules=["__init__"],

    # List run-time dependencies here.  These will be installed by pip when
    # your project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    # ophyd 1.6 series (1.6.1) doesn't work with the Acquire live view (stuck on "waiting for data...")
    install_requires=['xicam', 'numpy', 'qtpy', 'databroker', 'bluesky', 'ophyd==1.5.4', 'happi', 'bluesky-darkframes',
                                                                                  'ipykernel!=5.0*,!=5.1.0',
                      'pyqode.python', 'typhos', 'pydm==1.13.0', 'caproto',
                      # 'git+https://github.com/pcdshub/typhos.git',
                      # 'git+https://github.com/pcdshub/happi.git'  # ipykernel has faulty releases
                      ],

    setup_requires=[],

    # List additional groups of dependencies here (e.g. development
    # dependencies). You can install these using the following syntax,
    # for example:
    # $ pip install -e .[dev,tests]
    extras_require={
        # 'dev': ['check-manifest'],
        'tests': ['pytest', 'coverage'],
    },

    # If there are data files included in your packages that need to be
    # installed, specify them here.  If using Python 2.6 or less, then these
    # have to be included in MANIFEST.in as well.
    package_data={},

    # Although 'package_data' is the preferred approach, in some case you may
    # need to place data files outside of your packages. See:
    # http://docs.python.org/3.4/distutils/setupscript.html#installing-additional-files # noqa
    # In this case, 'data_file' will be installed into '<sys.prefix>/my_data'
    # data_files=[#('lib/python2.7/site-packages/gui', glob.glob('gui/*')),
    #            ('lib/python2.7/site-packages/yaml/tomography',glob.glob('yaml/tomography/*'))],

    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # pip to create the appropriate form of executable for the target platform.
    entry_points={'xicam.plugins.ControllerPlugin': [
        'areadetector = xicam.Acquire.controllers.areadetector:AreaDetectorController',
        'saxsdetector = xicam.Acquire.controllers.saxsdetector:SAXSDetectorController',
        'fastccd_controller = xicam.Acquire.controllers.fastccd_controller:FastCCDController',
        'typhos = xicam.Acquire.controllers.typhoscontroller:TyphosController',
        'diodecontroller = xicam.Acquire.controllers.diodecontroller:DiodeController',
        'psu = xicam.Acquire.controllers.psu:PSUController'],
        'xicam.plugins.DataResourcePlugin': [
            'bluesky = xicam.Acquire.datasources.BlueskyDataResource:BlueskyDataResourcePlugin',
            'ophyd = xicam.Acquire.datasources.OphydDataResource:OphydDataResourcePlugin'],
        'xicam.plugins.SettingsPlugin': ['devices = xicam.Acquire.devices:DeviceSettingsPlugin',
                                         'happi_devices = xicam.Acquire.devices.happi:HappiSettingsPlugin',
                                         'plans = xicam.Acquire.plans:PlanSettingsPlugin'],
        'xicam.plugins.GUIPlugin': ['acquire = xicam.Acquire:AcquirePlugin']},

    ext_modules=[],
    include_package_data=True
)
