import unittest

from appearance import colour_css, contrast_ratio, mix_colour, readable_colour, text_on


class ContrastTests(unittest.TestCase):
    def test_low_contrast_preferences_are_corrected(self):
        for background in ('#000000', '#FFFFFF', '#555555', '#B070A0', '#001144'):
            for preferred in ('#111111', '#FAFAFA', '#663388', background):
                self.assertGreaterEqual(contrast_ratio(readable_colour(preferred, background), background), 4.5)

    def test_every_button_state_meets_text_contrast(self):
        for bg, surface, accent in (('#100B20', '#281A45', '#8B3DFF'), ('#FAFAFA', '#E8E8E8', '#5A20B5'), ('#777777', '#888888', '#999999')):
            button = mix_colour(bg, surface, .72)
            for colour in (button, mix_colour(button, accent, .18), mix_colour(button, accent, .3), accent):
                self.assertGreaterEqual(contrast_ratio(text_on(colour), colour), 4.5)
            css = colour_css({'background': bg, 'surface': surface, 'foreground': bg, 'accent': accent})
            self.assertIn('button:disabled { opacity: 1;', css)
            self.assertIn('outline: 2px solid', css)


if __name__ == '__main__':
    unittest.main()
