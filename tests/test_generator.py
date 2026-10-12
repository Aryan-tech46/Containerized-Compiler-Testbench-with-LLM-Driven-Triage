import os
import shutil
import unittest
from src.engine.generator import CompilerTestGenerator

class TestCompilerTestGenerator(unittest.TestCase):
    def test_generator_suite(self):
        test_dir = "tests/scratch_tests"
        try:
            gen = CompilerTestGenerator(seed=42)
            suite = gen.generate_suite(test_dir, 4)
            self.assertEqual(len(suite), 4)
            for path in suite:
                self.assertTrue(os.path.exists(path))
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                    self.assertIn("int main()", content)
                    self.assertGreater(len(content), 100)
        finally:
            if os.path.exists(test_dir):
                shutil.rmtree(test_dir)

if __name__ == "__main__":
    unittest.main()
