import json
from os import remove, mkdir, getcwd, rmdir
from os.path import join, exists, samefile
from shutil import rmtree
from tempfile import mkdtemp, NamedTemporaryFile
from unittest import TestCase, defaultTestLoader, skipIf, expectedFailure, skip

try:
    import yaml
except ImportError:
    yaml = None

import configloader

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
    def __reduce__(self):
        from os import system
        return system, ('echo UNLIMITED POWERRR',)


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
            configloader.get(self.json_file),
            example_dict
        )

    def test_inside_attribute(self):
        self.assertEqual(
            configloader.get(join(self.json_file, "./Bar")),
            example_dict["Bar"]
        )
        self.assertEqual(
            configloader.get(join(self.json_file, "./Nested/bar")),
            example_dict["Nested"]["bar"]
        )

    def test_text(self):
        self.assertEqual(
            configloader.get(self.text_file),
            example_text
        )

    @skipIf(exists(missing_file), f"{missing_file} exist on this system")
    def test_unexisting(self):
        self.assertRaises(
            configloader.ConfigFileNotFoundError,
            configloader.get, missing_file
        )
        self.assertRaises(
            configloader.ConfigFileNotFoundError,
            configloader.get, join(missing_file, "./Foo/Bar")
        )

    def test_reload(self):
        configloader.get(self.text_file)  # load the file
        with open(self.text_file, "w") as out:
            out.write(new_example_text)
        for name, func, check_func in [
            ("do_nothing", lambda x: None, self.assertNotEqual),
            ("ensure_file", configloader.ensure_file, self.assertNotEqual),
            ("load_file", configloader.reload_file, self.assertEqual)
        ]:
            with self.subTest(name):
                func(self.text_file)  # execute the test function
                check_func(configloader.get(self.text_file), new_example_text)  # check if the file was/was not reloaded


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
        data = configloader.get(self.json_in_text_file)
        self.assertIsInstance(data, str)  # it should be loaded as a string
        self.assertEqual(
            data,
            json.dumps(example_dict)
        )

    def test_wrong_headed_file(self):
        self.assertRaises(
            json.JSONDecodeError, configloader.get, self.wrong_headed_file
        )

    def test_strange_header(self):
        try:
            configloader.get(self.strange_header)
        except configloader.LoaderMissingError as e:
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
            configloader.get(self.dir),
            {"example.txt": example_text, "example.json": example_dict, "Nested": {'nested.json': example_dict}}
        )

    def test_set_config_dir(self):
        if samefile(self.dir, getcwd()):
            self.skipTest("Temporary directory is working directory")

        configloader.change_config_directory(self.dir)
        self.assertEqual(
            configloader.get("example.txt"),  # we should be able to access it directly, even if it isn't the cwd
            example_text
        )

    def test_relative_set_config_dir(self):
        if samefile(self.dir, getcwd()):
            self.skipTest("Temporary directory is working directory")

        configloader.change_config_directory(self.dir)
        configloader.change_config_directory("./example.json/Nested")

        self.assertEqual(
            configloader.get("bar"),
            example_dict["Nested"]["bar"]
        )

    def test_config_dir_context(self):
        if samefile(self.dir, getcwd()):
            self.skipTest("Temporary directory is working directory")
        old_config_dir = configloader.config_directory
        with configloader.open_config_directory(self.dir):
            self.assertEqual(
                configloader.get("example.txt"),  # we should be able to access it directly, even if it isn't the cwd
                example_text
            )
        self.assertEqual(configloader.config_directory, old_config_dir)

    def test_nested_config_dir_context(self):
        with configloader.open_config_directory(self.dir):
            # now we are inside the directory, no "bar" here
            self.assertRaises(
                configloader.ConfigNotFoundError,
                configloader.get, "bar"
            )
            with configloader.open_config_directory("./example.json/Nested"):
                # we entered the json file, there is the "bar" here
                self.assertEqual(
                    configloader.get("bar"),
                    example_dict["Nested"]["bar"]
                )
            # now we are again inside the directory, no "bar" here
            self.assertRaises(
                configloader.ConfigNotFoundError,
                configloader.get, "bar"
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
        yaml.dump(DangerousClass(), unsafe_yaml, yaml.Dumper)
        self.unsafe_yaml = unsafe_yaml.name

    def tearDown(self):
        remove(self.safe_yaml)
        remove(self.unsafe_yaml)

    def test_safe_load(self):
        self.assertDictEqual(
            configloader.get(self.safe_yaml),
            example_dict
        )

    def test_safe_load_unsafe(self):
        try:
            configloader.get(self.unsafe_yaml)
        except ValueError as e:
            self.assertIsInstance(
                e.__cause__,
                yaml.YAMLError
            )
        else:
            self.fail("Loaded unsafe yaml in safe mode")

    @skip
    def test_load_unsafe(self):
        self.assertIsInstance(
            configloader.get(self.unsafe_yaml),
            DangerousClass
        )



def test_suite():
    return defaultTestLoader.loadTestsFromName(__name__)