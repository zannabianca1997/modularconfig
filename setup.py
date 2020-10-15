from setuptools import setup

version = '0.2'

setup(
    name='configloader',
    version=version,
    description="Modular config loader",
    long_description='\n'.join([
    #    open("README.rst").read(),  #todo: write readme
    #    open('CHANGES.rst').read(),
    ]),
    keywords='config',
    author='Giuseppe Zanichelli',
    author_email='zannabianca199712@gmail.com',
    license='BSD',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 3',
    ],
    python_requires='~=3.8',  #todo: check minimal version
    include_package_data=True,
    zip_safe=True,
    install_requires=[],
    extras_require={
        "yaml": ["pyyaml"]
    },
    py_modules=['configloader'],
    test_suite='tests.test_suite',
)