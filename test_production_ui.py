"""Run with VERSEWORK_TEST_GTK=1 on a display or under Xvfb."""
import os
import unittest


@unittest.skipUnless(os.environ.get('VERSEWORK_TEST_GTK') == '1', 'Requires GTK display')
class ProductionControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import Gtk
        if not Gtk.init_check():
            raise unittest.SkipTest('GTK display unavailable')

    def controls(self, value=None):
        from app import box
        from production_ui import ProductionMixin
        class Harness(ProductionMixin):
            settings = {}
        return Harness().production_controls(box(), value)

    def test_default_does_not_impose_drum_feel(self):
        collect = self.controls()
        self.assertIsNone(collect()['drums'])
        collect.widgets['follow_style'].set_active(False)
        collect.widgets['drums'].set_value(90)
        self.assertEqual(collect()['drums'], 90)
        collect.widgets['follow_style'].set_active(True)
        self.assertIsNone(collect()['drums'])

    def test_explicit_machine_perfect_value_is_preserved(self):
        collect = self.controls({'drums': 0})
        self.assertFalse(collect.widgets['follow_style'].get_active())
        self.assertEqual(collect()['drums'], 0)


if __name__ == '__main__':
    unittest.main()
