# modularconfig
A python config loader that permit the access via path indexing, hiding the config structure

Example:

Given the directory structure

    /opt/myapp/config
       |-mainconf
       |-version_number
       |-pyscript
       |-nested
       | |-answer
       | |-precise_answer
       |-myformat
       
And the given documents:

mainconf:

    #type: json
    {
      "content": "this is a json file"
    }

version_number:

    #type: text
    3.2
      
pyscript:

    #type: python
    a = 45.4
    b = range(1,34)
    
nested/answer:

    42
    
nested/precise_answer:

    42.06
   
myformat

    #type: myloader
    >>>put data here<<
    
All is accessible with a simple command:
   
    import modularconfig
    # opening whole files
    modularconfig.get("/opt/myapp/config/mainconf")  # {"content": "this is a json file"}
    # entries in files can be directly accessed
    modularconfig.get("/opt/myapp/config/mainconf/content")   # "this is a json file"
    # whole directories can be loaded trasparently, can't be separed from files
    modularconfig.get("/opt/myapp/config/nested")  # {"answer":42, "precise_answer":42.01}
    
File type specification is not necessary:

    modularconfig.get("/opt/myapp/config/nested/answer")  # 42, type == int
    modularconfig.get("/opt/myapp/config/nested/precise_answer")  # 42.01, type == float

The default order in which the formats will be tried is in modularconfig.loaders.auto_loaders.

Filetype can include options for the loader:
    
    #type: <loader>: <opt1> =<optval>; <opt2>=<optval>;<flag1>; etc...
    
An important option is "encoding": the rest of the file will be decoded using the encoding specified. Type specification is always in UTF-8

A base directory can be choosed:

    modularconfig.set_config_directory("/opt/myapp/config")
    modularconfig.get("mainconf/content")   # "this is a json file"
    with modularconfig.open_config_directory("nested"):
        modularconfig.get_config_directory()  # '/opt/myapp/config/nested'
        modularconfig.get("answer")  # 42
    modularconfig.get_config_directory()  # '/opt/myapp/config'
    
Directories / files can be preloaded and reloaded. They will never be reloaded if not asked

    modularconfig.ensure("/opt/myapp/config")
    # nested changed
    modularconfig.ensure("/opt/myapp/config/nested", reload=True)
    
Dangerous loaders are disabled by default:

    modularconfig.set_config_directory("/opt/myapp/config")
    try:
        modularconfig.get("pyscript/a")
    except modularconfig.LoadingError as e:
        print(e.args[0])  # "Python loader is disabled"
    modularconfig.loaders.dangerous_loaders["python"] = True
    modularconfig.get("pyscript/a") # 45.4
    
Filetypes supported:

  - json
  - python [disabled]
  - yaml [if pyyaml is installed, use safe_load by default, can switch by setting dangerous_loaders["yaml"]]
  - int, integer
  - float, real
  - complex
  - number  [try to parse as a int, then float, then complex]
  - bool, boolean
  - none, null [always parse to None]
  - base64 [will use the altchars and validate options if given]
  - text
  
Other loaders can be installed
    
    class MyLoader:
        def __init__(self):
            self.name = "myloader"
            self.aliases = ["other_name"]  # optional
    
        def load(self, text, options):
            if text == "answer":
                return 42
            else:
                return "What???"
    modularconfig.loaders.register_loader(MyLoader())
    
And the order of autodetect can be changed

    modularconfig.loaders.auto_loader = ["myloader", "json", "text"]
    
A loader can specify a more powerful loader, but that should not be used with untrusted input:

    class MyLoader:
        def __init__(self):
            self.name = "myloader"
            self.aliases = ["other_name"]  # optional
         
        def load(self, text, options):
            return "safe parse"
    
        def dangerous_load(self, text, options):
            return "spooky parse"
    modularconfig.loaders.register_loader(MyLoader())
   
The "load" method will still be used if the flag in modularconfig.loaders.dangerous_loaders isn't set:

    modularconfig.get("/opt/myapp/config/myformat")  # return "safe parse"
    modularconfig.loaders.dangerous_loaders["myloader"] = True
    modularconfig.ensure("/opt/myapp/config/nested", reload=True)
    modularconfig.get("/opt/myapp/config/myformat")  # return "spooky parse"