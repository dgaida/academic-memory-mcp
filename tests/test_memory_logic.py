import unittest
from mcp_university.utils.memory import resolve_memory_index_names

class TestMemoryLogic(unittest.TestCase):
    def test_shared_paths(self):
        class_paths = {
            "PAV_Anerkennung": "D:/TH_Koeln/PAV/Memory",
            "PAV_Nachteilsausgleich": "D:/TH_Koeln/PAV/Memory",
            "Individual": "D:/Other/Path"
        }
        mapping = resolve_memory_index_names(class_paths)

        self.assertEqual(mapping["PAV_Anerkennung"], "PAV")
        self.assertEqual(mapping["PAV_Nachteilsausgleich"], "PAV")
        self.assertEqual(mapping["Individual"], "Individual")

    def test_shared_paths_no_underscore(self):
        class_paths = {
            "ClassA": "D:/shared",
            "ClassB": "D:/shared"
        }
        mapping = resolve_memory_index_names(class_paths)

        index_name = mapping["ClassA"]
        self.assertIn(index_name, ["ClassA", "ClassB"])
        self.assertEqual(mapping["ClassB"], index_name)

    def test_unique_paths(self):
        class_paths = {
            "A": "path/a",
            "B": "path/b"
        }
        mapping = resolve_memory_index_names(class_paths)
        self.assertEqual(mapping["A"], "A")
        self.assertEqual(mapping["B"], "B")

if __name__ == "__main__":
    unittest.main()
