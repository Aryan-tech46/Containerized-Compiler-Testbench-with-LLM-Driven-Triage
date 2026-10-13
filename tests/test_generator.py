import os
import shutil
import unittest
from src.engine.generator import CompilerTestGenerator, TestMetadata

class TestCompilerTestGenerator(unittest.TestCase):
    def setUp(self):
        self.test_dir = "tests/scratch_tests"

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_generator_suite_backward_compatibility(self):
        gen = CompilerTestGenerator(seed=42)
        suite = gen.generate_suite(self.test_dir, 4)
        self.assertEqual(len(suite), 4)
        for path in suite:
            self.assertTrue(os.path.exists(path))
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertIn("int main()", content)
                self.assertGreater(len(content), 100)

    def test_generator_suite_with_metadata(self):
        gen = CompilerTestGenerator(seed=123)
        metadata_list = gen.generate_suite_with_metadata(self.test_dir, count=8, mode="balanced")
        self.assertEqual(len(metadata_list), 8)
        
        categories = set()
        for meta in metadata_list:
            self.assertIsInstance(meta, TestMetadata)
            self.assertTrue(os.path.exists(meta.filepath))
            self.assertIn(meta.expected_outcome, ["PASS", "COMPILE_ERROR"])
            self.assertTrue(len(meta.category) > 0)
            self.assertTrue(len(meta.target_pass) > 0)
            categories.add(meta.category)

        # Confirm multiple distinct stress categories are present
        self.assertGreaterEqual(len(categories), 3)

    def test_new_stress_generators(self):
        gen = CompilerTestGenerator(seed=99)
        vec_code = gen.generate_loop_vectorizer_stress()
        self.assertIn("#pragma GCC ivdep", vec_code)
        self.assertIn("execute_vector_stress", vec_code)

        concept_code = gen.generate_cpp20_concepts_stress()
        self.assertIn("concept", concept_code)
        self.assertIn("requires", concept_code)

        inliner_code = gen.generate_deep_inliner_stress()
        self.assertIn("ALWAYS_INLINE", inliner_code)
        self.assertIn("stage_10", inliner_code)

if __name__ == "__main__":
    unittest.main()
