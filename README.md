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
  - yaml [if pyyaml is installed, use safe_load by default, can switch by setting dangerous_loaders["yaml_full_loader"]]
  - int, integer
  - float, real
  - complex
  - number  [try to parse as a int, then float, then complex]
  - bool, boolean
  - none, null [always parse to None]
  - base64
  - text
  
Other loaders can be installed
    
    def myloader(text: str) -> object:
      ...
    
    modularconfig.loaders.loaders["mytype"] = myloaders
    
And the order of autodetect can be changed

    modularconfig.loaders.auto_loader = ["myloader", "json", "text"]
