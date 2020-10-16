import json
from os import remove, mkdir, getcwd
from os.path import join, exists, samefile
from shutil import rmtree
from sys import modules
from tempfile import mkdtemp, NamedTemporaryFile
from unittest import TestCase, defaultTestLoader, skipIf
from importlib import reload, invalidate_caches

try:
    import yaml
except ImportError:
    yaml = None

import modularconfig

example_dict = {
    "Foo": "foo",
    "Bar": [1, 2, 3],
    "Nested": {
        "bar": "inside_bar"
    }
}
example_text = "Hello World"
new_example_text = "Hello Universe"

missing_file = "/I/Really/Hope/This/File/Does/Not/Exist/On/Any/System/Ever"


class DangerousClass:
    def __init__(self):
        self.name = "Exploitable"


class SimpleFiles(TestCase):
    def setUp(self):
        json_file = NamedTemporaryFile(mode="w", delete=False)
        json.dump(example_dict, json_file)
        self.json_file = json_file.name

        text_file = NamedTemporaryFile(mode="w", delete=False)
        text_file.write(example_text)
        self.text_file = text_file.name

    def tearDown(self):
        remove(self.json_file)
        remove(self.text_file)

    def test_json(self):
        self.assertDictEqual(
            modularconfig.get(self.json_file),
            example_dict
        )

    def test_inside_attribute(self):
        self.assertEqual(
            modularconfig.get(join(self.json_file, "./Bar")),
            example_dict["Bar"]
        )
        self.assertEqual(
            modularconfig.get(join(self.json_file, "./Nested/bar")),
            example_dict["Nested"]["bar"]
        )

    def test_text(self):
        self.assertEqual(
            modularconfig.get(self.text_file),
            example_text
        )

    @skipIf(exists(missing_file), f"{missing_file} exist on this system")
    def test_unexisting(self):
        self.assertRaises(
            modularconfig.ConfigFileNotFoundError,
            modularconfig.get, missing_file
        )
        self.assertRaises(
            modularconfig.ConfigFileNotFoundError,
            modularconfig.get, join(missing_file, "./Foo/Bar")
        )

    def test_reload(self):
        modularconfig.ensure(self.text_file)  # load the file
        with open(self.text_file, "w") as out:
            out.write(new_example_text)
        with self.subTest("do nothing"):
            self.assertEqual(modularconfig.get(self.text_file), example_text)  # nothing has changed
        with self.subTest("load again"):
            modularconfig.ensure(self.text_file)
            self.assertEqual(modularconfig.get(self.text_file), example_text)  # nothing has changed
        with self.subTest("reload explicity"):
            modularconfig.ensure(self.text_file, reload=True)
            self.assertEqual(modularconfig.get(self.text_file), new_example_text)  # nothing has changed


class HeadedFiles(TestCase):
    def setUp(self):
        json_in_text_file = NamedTemporaryFile(mode="w", delete=False)
        json_in_text_file.write("#type: text\n")
        json.dump(example_dict, json_in_text_file)  # writing valid json
        self.json_in_text_file = json_in_text_file.name

        wrong_headed_file = NamedTemporaryFile(mode="w", delete=False)
        wrong_headed_file.write("#type: json\n")
        wrong_headed_file.write(example_text)
        self.wrong_headed_file = wrong_headed_file.name

        strange_header = NamedTemporaryFile(mode="w", delete=False)
        strange_header.write("#type: unknown\n")
        strange_header.write(example_text)
        self.strange_header = strange_header.name

    def tearDown(self):
        remove(self.json_in_text_file)
        remove(self.wrong_headed_file)
        remove(self.strange_header)

    def test_json_in_text_file(self):
        data = modularconfig.get(self.json_in_text_file)
        self.assertIsInstance(data, str)  # it should be loaded as a string
        self.assertEqual(
            data,
            json.dumps(example_dict)
        )

    def test_wrong_headed_file(self):
        self.assertRaises(
            json.JSONDecodeError, modularconfig.get, self.wrong_headed_file
        )

    def test_strange_header(self):
        try:
            modularconfig.get(self.strange_header)
        except modularconfig.LoaderMissingError as e:
            self.assertEqual(e.args[0], "unknown")
        except Exception as e:
            self.fail(f"Expected LoaderMissingError, got {e}")
        else:
            self.fail("Got no exception from a wrong header")


class ConfigDir(TestCase):
    def setUp(self):
        self.dir = mkdtemp()
        with open(join(self.dir, "example.txt"), "w") as out:
            out.write(example_text)
        with open(join(self.dir, "./example.json"), "w") as out:
            json.dump(example_dict, out)
        mkdir(join(self.dir, "Nested"))
        with open(join(self.dir, "./Nested/nested.json"), "w") as out:
            json.dump(example_dict, out)

    def tearDown(self):
        rmtree(self.dir)

    def test_get_dir(self):
        self.assertDictEqual(
            modularconfig.get(self.dir),
            {"example.txt": example_text, "example.json": example_dict, "Nested": {'nested.json': example_dict}}
        )

    def test_set_config_dir(self):
        if samefile(self.dir, getcwd()):
            self.skipTest("Temporary directory is working directory")

        modularconfig.set_config_directory(self.dir)
        self.assertEqual(
            modularconfig.get("example.txt"),  # we should be able to access it directly, even if it isn't the cwd
            example_text
        )

    def test_relative_set_config_dir(self):
        if samefile(self.dir, getcwd()):
            self.skipTest("Temporary directory is working directory")

        modularconfig.set_config_directory(self.dir)
        modularconfig.set_config_directory("./example.json/Nested")

        self.assertEqual(
            modularconfig.get("bar"),
            example_dict["Nested"]["bar"]
        )

    def test_config_dir_context(self):
        if samefile(self.dir, getcwd()):
            self.skipTest("Temporary directory is working directory")
        old_config_dir = modularconfig.get_config_directory()
        with modularconfig.using_config_directory(self.dir):
            self.assertEqual(
                modularconfig.get("example.txt"),  # we should be able to access it directly, even if it isn't the cwd
                example_text
            )
        self.assertEqual(modularconfig.get_config_directory(), old_config_dir)

    def test_nested_config_dir_context(self):
        with modularconfig.using_config_directory(self.dir):
            # now we are inside the directory, no "bar" here
            self.assertRaises(
                modularconfig.ConfigNotFoundError,
                modularconfig.get, "bar"
            )
            with modularconfig.using_config_directory("./example.json/Nested"):
                # we entered the json file, there is the "bar" here
                self.assertEqual(
                    modularconfig.get("bar"),
                    example_dict["Nested"]["bar"]
                )
            # now we are again inside the directory, no "bar" here
            self.assertRaises(
                modularconfig.ConfigNotFoundError,
                modularconfig.get, "bar"
            )


@skipIf(yaml is None, "No yaml detected")
class Yaml(TestCase):
    def setUp(self):
        safe_yaml = NamedTemporaryFile(mode="w", delete=False)
        safe_yaml.write("#type: yaml\n")
        yaml.safe_dump(example_dict, safe_yaml)  # writing valid json
        self.safe_yaml = safe_yaml.name

        unsafe_yaml = NamedTemporaryFile(mode="w", delete=False)
        unsafe_yaml.write("#type: yaml\n")
        yaml.dump(DangerousClass(), unsafe_yaml)
        self.unsafe_yaml = unsafe_yaml.name

    def tearDown(self):
        remove(self.safe_yaml)
        remove(self.unsafe_yaml)

    def test_safe_load(self):
        modularconfig.loaders.dangerous_loaders["yaml_full_loader"] = False
        self.assertDictEqual(
            modularconfig.get(self.safe_yaml),
            example_dict
        )

    def test_safe_load_unsafe(self):
        modularconfig.loaders.dangerous_loaders["yaml_full_loader"] = False
        try:
            modularconfig.get(self.unsafe_yaml)
        except ValueError as e:
            self.assertIsInstance(
                e.__cause__,
                yaml.YAMLError
            )
        else:
            self.fail("Loaded unsafe yaml in safe mode")

    def test_load_unsafe(self):
        modularconfig.loaders.dangerous_loaders["yaml_full_loader"] = True
        self.assertIsInstance(
            modularconfig.get(self.unsafe_yaml),
            DangerousClass
        )

#todo: write loaders tests

def test_suite():
    return defaultTestLoader.loadTestsFromName(__name__)