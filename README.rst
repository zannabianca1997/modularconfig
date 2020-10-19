=================
``modularconfig``
=================

``modularconfig`` is a python library used to load complex config file configurations from disk, hiding the underlying filesystem structure and the specific file format(json, yaml, etc.)

Basic Usage
-----------

Let's say that we order our config like this::

    /opt/myapp/config
    ├── mainconf.json
    ├── nested
    │   ├── answer
    │   ├── precise_answer
    │   └── complex_answer
    ├── notjson.txt
    └── confscript.py

And we want to access `mainconf.json`:

.. code-block:: json

    {
        "content": "this is, obviously, a json file",
        "version": [2, 3]
    }

We can simply write:

>>> import modularconfig
>>> modularconfig.get("/opt/myapp/config/mainconf.json/version")
[2, 3]

or load the entire file:

>>> modularconfig.get("/opt/myapp/config/mainconf.json")
{'content': 'this is, obviously, a json file', 'version': [2, 3]}

or even the entire directory tree!

>>> modularconfig.get("/opt/myapp/config")
{'mainconf.json': {'content': 'this is, obviously, a json file', 'version': [2, 3]}, 'nested': { ...

File type can be specified directly:

.. code-block:: text

    #type: text
    {
        "content": "this is, less obviously, not a json file",
        "version": [2, 3]
    }

>>> modularconfig.get("/opt/myapp/config/notjson.txt")
'{\n    "content": "this is, less obviously, not a json file",\n    "version": [2, 3]\n}'

but is usually not necessary:

>>> modularconfig.get("/opt/myapp/config/nested")
{'answer': 42, 'precise_answer': 42.0, 'complex_answer': (42+0j)}

To ease on the paths a common prefix can be specified (similar to the cd command):

>>> modularconfig.set_config_directory("/opt/myapp/config")
>>> modularconfig.get("mainconf.json/version")
[2, 3]

and a context manger is provided to temporarily change it

>>> with modularconfig.using_config_directory("./nested"):
...     modularconfig.get("answer")
42

