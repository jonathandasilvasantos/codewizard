import unittest
from codewizard import TextEditor

class TestTextEditor(unittest.TestCase):

    def setUp(self):
        # Create a mock font object (this won't actually be used for rendering)
        mock_font = lambda: None
        mock_font.size = lambda s: (len(s) * 10, 24)  # Assume each character is 10 pixels wide
        self.editor = TextEditor(mock_font)

    def test_initial_state(self):
        self.assertEqual(self.editor.lines, [''])
        self.assertEqual(self.editor.current_line, 0)
        self.assertEqual(self.editor.cursor_pos, 0)

    def test_insert_char_at_cursor(self):
        self.editor.insert_char_at_cursor('a')
        self.assertEqual(self.editor.lines[0], 'a')

    def test_handle_backspace(self):
        self.editor.insert_char_at_cursor('a')
        self.editor.handle_backspace()
        self.assertEqual(self.editor.lines[0], '')

    def test_handle_return(self):
        self.editor.insert_char_at_cursor('a')
        self.editor.handle_return()
        self.assertEqual(self.editor.lines, ['a', ''])

    def test_handle_delete(self):
        self.editor.insert_char_at_cursor('a')
        self.editor.insert_char_at_cursor('b')
        self.editor.cursor_pos = 1
        self.editor.handle_delete()
        self.assertEqual(self.editor.lines[0], 'a')

    def test_jump_to_start_of_line(self):
        self.editor.insert_char_at_cursor('a')
        self.editor.insert_char_at_cursor('b')
        self.editor.jump_to_start_of_line()
        self.assertEqual(self.editor.cursor_pos, 0)

    def test_jump_to_end_of_line(self):
        self.editor.insert_char_at_cursor('a')
        self.editor.insert_char_at_cursor('b')
        self.editor.jump_to_start_of_line()
        self.editor.jump_to_end_of_line()
        self.assertEqual(self.editor.cursor_pos, 2)

    def test_handle_up(self):
        self.editor.insert_char_at_cursor('a')
        self.editor.handle_return()
        self.editor.handle_up()
        self.assertEqual(self.editor.current_line, 0)

    def test_handle_down(self):
        self.editor.insert_char_at_cursor('a')
        self.editor.handle_return()
        self.editor.handle_down()
        self.assertEqual(self.editor.current_line, 1)

    def test_handle_left(self):
        self.editor.insert_char_at_cursor('a')
        self.editor.handle_left()
        self.assertEqual(self.editor.cursor_pos, 0)

    def test_handle_right(self):
        self.editor.insert_char_at_cursor('a')
        self.editor.handle_right()
        self.assertEqual(self.editor.cursor_pos, 1)

    def test_handle_pageup(self):
        for _ in range(50):
            self.editor.insert_char_at_cursor('a')
            self.editor.handle_return()
        self.editor.handle_pageup()
        self.assertLess(self.editor.current_line, 50)

    def test_handle_pagedown(self):
        for _ in range(50):
            self.editor.insert_char_at_cursor('a')
            self.editor.handle_return()
        self.editor.handle_pagedown()
        self.assertGreater(self.editor.current_line, 0)

    def test_selection(self):
        self.editor.insert_char_at_cursor('a')
        self.editor.insert_char_at_cursor('b')
        self.editor.insert_char_at_cursor('c')
        self.editor.selection_start = (0, 0)
        self.editor.selection_end = (0, 2)
        self.editor.handle_backspace()
        self.assertEqual(self.editor.lines[0], 'c')

if __name__ == '__main__':
    unittest.main()
