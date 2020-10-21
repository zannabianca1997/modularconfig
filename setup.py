from setuptools import setup

version = '0.2.4-alpha'

setup(
    name='modularconfig',
    version=version,
    description="Modular config loader",
    long_description=open("README.rst").read(),
    keywords=['configs', 'modular'],
    author='Giuseppe Zanichelli',
    author_email='zannabianca199712@gmail.com',
    url='https://github.com/zannabianca1997/modularconfig',
    download_url='https://github.com/zannabianca1997/modularconfig/archive/v_0.2.4-alpha.tar.gz',
    license='BSD',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 3',
    ],
    python_requires='>=3.6',  # todo: check minimal version
    include_package_data=True,
    zip_safe=True,
    install_requires=[],
    extras_require={
        "yaml": ["pyyaml"]
    },
    packages=['modularconfig', 'modularconfig.loaders'],
    test_suite='tests.test_suite',
)
