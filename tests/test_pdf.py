"""Unit tests for PDF document handling."""

import unittest

from r_quran.pdf import QuranDocument


class TestPDF(unittest.TestCase):
    """Test loading and metadata querying on Quran PDF."""

    def test_document_page_count_and_size(self) -> None:
        doc = QuranDocument()
        self.assertEqual(doc.get_n_pages(), 614)

        width, height = doc.get_page_size(0)
        self.assertGreater(width, 0)
        self.assertGreater(height, 0)

        # Ensure caching returns identical tuple
        cached_w, cached_h = doc.get_page_size(0)
        self.assertEqual(width, cached_w)
        self.assertEqual(height, cached_h)

    def test_page_index_out_of_bounds(self) -> None:
        doc = QuranDocument()
        with self.assertRaises(IndexError):
            doc.get_page(-1)
        with self.assertRaises(IndexError):
            doc.get_page(1000)


if __name__ == "__main__":
    unittest.main()
