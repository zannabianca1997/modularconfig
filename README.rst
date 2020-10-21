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

File type can be specified directly (see `Loading Files`_):

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

Loading Files
-------------

The config files can include an intestation that specify the datatype and evntual options::

    #type:text:encoding=utf-8
    #type:json
    #type:base64:altchars=-_;validate=false

Type specification is always decoded from utf-8. The special option "encoding" is not passed to the loader but used to decode the rest of the file.

The available loaders are:

- Dict types:

  - json
  - yaml [if pyyaml is installed, throw a MissingLoaderError otherwise]
  - python [disabled by default, see `Dangerous Loaders`_]

- Primitive types:

  - int, integer
  - float, real
  - complex
  - number, num [try in order to parse the text as a int, then a float, then a complex number]
  - base64 [accept altchars and validate as options]
  - text

Users can define their own loaders:

.. code-block:: python

    class myloader:
        name = "myloader"
        aliases = ["other_name"]  # optional

        # At least one of the following methods must be defined:
        def load(self, text:str, options: Dict[str, str]):
            # parse untrusted text, safely
            return parsed_obj

        def dangerous_load(self, text:str, options: Dict[str, str]):
            # parse trusted text, can have side-effects
            return parsed_obj

    modularconfig.loaders.register_loader(myloader())

Dangerous Loaders
-----------------

Some loader are too powerful to be used on untrusted input (e.g. ``python``). To make sure that no side effect is caused by config files those loaders are disabled by default:

``pyscript.py``::

    #type: python
    a=4
    b=5

>>> modularconfig.get("pyscript.py")
Traceback (most recent call last):
  ...
modularconfig.errors.DisabledLoaderError: 'python' loader is disabled. Set dangerous_loaders['python'] to True to enable
>>> modularconfig.loaders.dangerous_loaders["python"] = True
>>> modularconfig.get("pyscript.py")
{'a': 4, 'b': 5}

Some loaders (like yaml) can offer both functionality: a safe subset and a full loader. In that case the full loader will be used only if the flag is True

