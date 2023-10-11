import sys
import pyperclip 
import pygame
import imageio
import sys
from pygame.locals import *

pygame.init()
pygame.key.set_repeat(300, 50)  # Start repeating after 300ms, repeat every 50ms thereafter


# Screen settings
LARGURA = 800
ALTURA = 600
tela = pygame.display.set_mode((LARGURA, ALTURA))
pygame.display.set_caption('Code Wizard')

# Colors for dark theme
FUNDODARK = (30, 30, 30)
TEXTOBRIGHT = (230, 230, 230)
BRANCO = (255, 255, 255)
SELECAOBRIGHT = (50, 50, 150)
LINE_NUMBER_WIDTH = 50
LINE_NUMBER_COLOR = (80, 80, 80)
LINE_NUMBER_TEXT_COLOR = (150, 150, 150)


# Font
fonte = pygame.font.SysFont('arial', 24)

class TextEditor:
    def __init__(self, font):
        self.font = font
        self.lines = ['']
        self.current_line = 0
        self.cursor_pos = 0
        self.scroll_offset = 0
        self.selection_start = None
        self.selection_end = None
        self.is_selecting = False
        self.horizontal_scroll_offset = 0
        self.undo_stack = []
        self.redo_stack = []
        self.cursor_visible = True
        self.last_cursor_toggle_time = pygame.time.get_ticks()  # Initialize with the current time
        

    def copy_text(self):
        if self.selection_start is not None and self.selection_end is not None:
            start_line, start_pos = self.selection_start
            end_line, end_pos = self.selection_end
            
            # Same line selection
            if start_line == end_line:
                pyperclip.copy(self.lines[start_line][start_pos:end_pos])
            else:
                copied_text = self.lines[start_line][start_pos:]
                for line_num in range(start_line + 1, end_line):
                    copied_text += '\n' + self.lines[line_num]
                copied_text += '\n' + self.lines[end_line][:end_pos]
                pyperclip.copy(copied_text)
                
    def paste_text(self):
        self.push_undo()  # Push current state onto undo stack before making changes
        # If there's a selection, delete it first
        if self.selection_start is not None and self.selection_end is not None:
            self.delete_selection()
        
        clipboard_content = pyperclip.paste().split('\n')
        for idx, content in enumerate(clipboard_content):
            if idx == 0:
                self.lines[self.current_line] = self.lines[self.current_line][:self.cursor_pos] + content + self.lines[self.current_line][self.cursor_pos:]
                self.cursor_pos += len(content)
            else:
                self.lines.insert(self.current_line + idx, content)
                self.current_line += 1
                self.cursor_pos = len(content)


    def cut_text(self):
        self.push_undo()  # Push current state onto undo stack before making changes
        self.copy_text()
        self.delete_selection()


    def delete_selection(self):
        """
        Deletes the text between selection_start and selection_end.
        Resets the selection after deleting.
        """
        if self.selection_start is None or self.selection_end is None:
            # No selection to delete
            return

        start_line, start_pos = self.selection_start
        end_line, end_pos = self.selection_end

        # If selection is from right to left, swap start and end
        if start_line > end_line or (start_line == end_line and start_pos > end_pos):
            start_line, start_pos, end_line, end_pos = end_line, end_pos, start_line, start_pos

        # Same line selection
        if start_line == end_line:
            self.lines[start_line] = self.lines[start_line][:start_pos] + self.lines[start_line][end_pos:]
            self.cursor_pos = start_pos
        else:
            # Merge lines from start_line to end_line and delete the in-between lines
            start_line_content = self.lines[start_line][:start_pos]
            end_line_content = self.lines[end_line][end_pos:]

            self.lines[start_line] = start_line_content + end_line_content
            del self.lines[start_line + 1:end_line + 1]

            self.cursor_pos = start_pos
            self.current_line = start_line

        # Reset selection
        self.selection_start = None
        self.selection_end = None


    def input(self, event):
        CMD_PRESSED = event.mod & (KMOD_LMETA | KMOD_RMETA) or event.mod & (KMOD_LCTRL | KMOD_RCTRL)  # Check for Command key (or Ctrl key for non-Mac users)
        SHIFT_PRESSED = event.mod & KMOD_SHIFT
        
        # Handle combination of CMD key and other keys
        if CMD_PRESSED:
            if event.key == K_c:
                self.copy_text()
            elif event.key == K_v:
                self.paste_text()
            elif event.key == K_x:
                self.cut_text()
            elif event.key == K_LEFT:
                self.horizontal_scroll(-1)
                self.jump_to_start_of_line()
            elif event.key == K_RIGHT:
                self.horizontal_scroll(1)
                self.jump_to_end_of_line()
            if event.key == K_z:
                if SHIFT_PRESSED:
                    self.redo()
                else:
                    self.undo()
            return

        # Handle single key events
        if event.key == K_BACKSPACE:
            self.handle_backspace()
        elif event.key == K_RETURN:
            self.handle_return()
        elif event.key == K_UP:
            self.handle_up()
        elif event.key == K_DOWN:
            self.handle_down()
        elif event.key == K_LEFT:
            self.handle_left()
        elif event.key == K_RIGHT:
            self.handle_right()
        elif event.key == K_DELETE:
            self.handle_delete()
        elif event.key == K_PAGEUP:
            self.handle_pageup()
        elif event.key == K_PAGEDOWN:
            self.handle_pagedown()
        else:
            self.handle_character_input(event.unicode)
            
        # If SHIFT is pressed and no selection has started yet, initialize selection_start
        if SHIFT_PRESSED and self.selection_start is None:
            self.selection_start = (self.current_line, self.cursor_pos)

        # If either SHIFT or CMD is pressed, update the selection_end
        if SHIFT_PRESSED or CMD_PRESSED:
            self.selection_end = (self.current_line, self.cursor_pos)
            
        else:
            # If neither SHIFT nor CMD is pressed, reset the selection
            self.selection_start = None
            self.selection_end = None


   
    def horizontal_scroll(self, amount):
        max_offset = max(0, len(max(self.lines, key=len)) - LARGURA // 8)  # estimated, adjust as needed
        self.horizontal_scroll_offset = min(max(0, self.horizontal_scroll_offset + amount), max_offset)


    def handle_backspace(self):
        self.push_undo()  # Push current state onto undo stack before making changes
        if self.selection_start is not None and self.selection_end is not None:
            self.delete_selection()
        elif self.cursor_pos > 0:
            self.remove_char_at_cursor()
        elif self.current_line > 0:
            self.merge_with_previous_line()

    def handle_return(self):
        self.push_undo()  # Push current state onto undo stack before making changes
        self.split_line_at_cursor()
        # Check if current line is beyond the visible portion of the screen.
        if self.current_line - self.scroll_offset >= ALTURA // 30:
            self.scroll_offset += 1

    def handle_delete(self):
        self.push_undo()  # Push current state onto undo stack before making changes
        if self.selection_start is not None and self.selection_end is not None:
            self.delete_selection()
        elif self.cursor_pos < len(self.lines[self.current_line]):
            # Delete character to the right of cursor
            self.lines[self.current_line] = self.lines[self.current_line][:self.cursor_pos] + self.lines[self.current_line][self.cursor_pos + 1:]
        elif self.current_line < len(self.lines) - 1:
            # If at the end of a line, merge with the next line
            self.lines[self.current_line] += self.lines[self.current_line + 1]
            del self.lines[self.current_line + 1]

    def handle_up(self):
        if self.current_line > 0:
            self.move_cursor_up()

    def handle_down(self):
        if self.current_line < len(self.lines) - 1:
            self.move_cursor_down()

    def handle_left(self):
        if self.cursor_pos > 0:
            self.move_cursor_left()
            # Check if we need to scroll to the left
            current_line_rendered_width = self.font.size(self.lines[self.current_line][:self.cursor_pos])[0]
            if current_line_rendered_width < self.horizontal_scroll_offset * 8:  # Adjust the number as needed
                self.horizontal_scroll_offset -= 1
        elif self.current_line > 0:
            self.jump_to_end_of_previous_line()


    def handle_right(self):
        if self.cursor_pos < len(self.lines[self.current_line]):
            self.move_cursor_right()
            # Check if we need to scroll to the right
            current_line_rendered_width = self.font.size(self.lines[self.current_line][:self.cursor_pos])[0]
            if current_line_rendered_width > LARGURA - 20:  # 20 as a buffer to see the cursor
                self.horizontal_scroll_offset += 1
        elif self.current_line < len(self.lines) - 1:
            self.jump_to_start_of_next_line()




    def handle_character_input(self, char):
        if char:
            self.push_undo()  # Push current state onto undo stack before making changes
            if self.selection_start is not None and self.selection_end is not None:
                self.delete_selection()
            self.insert_char_at_cursor(char)
            
            # Check if we need to scroll to the right
            current_line_rendered_width = self.font.size(self.lines[self.current_line][:self.cursor_pos])[0]
            if current_line_rendered_width > LARGURA - 20:  # 20 as a buffer to see the cursor
                self.horizontal_scroll_offset += 1


    def handle_pageup(self):
        # Move the cursor up by the height of the window in lines.
        for _ in range(ALTURA // 30):
            if self.current_line > 0:
                self.move_cursor_up()

    def handle_pagedown(self):
        # Move the cursor down by the height of the window in lines.
        for _ in range(ALTURA // 30):
            if self.current_line < len(self.lines) - 1:
                self.move_cursor_down()

    def jump_to_start_of_line(self):
        self.cursor_pos = 0

    def jump_to_end_of_line(self):
        self.cursor_pos = len(self.lines[self.current_line])

    def remove_char_at_cursor(self):
        self.lines[self.current_line] = self.lines[self.current_line][:self.cursor_pos-1] + self.lines[self.current_line][self.cursor_pos:]
        self.cursor_pos -= 1

    def merge_with_previous_line(self):
        self.cursor_pos += len(self.lines[self.current_line - 1])
        self.lines[self.current_line - 1] += self.lines[self.current_line]
        del self.lines[self.current_line]
        self.current_line -= 1

    def split_line_at_cursor(self):
        self.lines.insert(self.current_line + 1, self.lines[self.current_line][self.cursor_pos:])
        self.lines[self.current_line] = self.lines[self.current_line][:self.cursor_pos]
        self.current_line += 1
        self.cursor_pos = 0

    def move_cursor_up(self):
        self.current_line -= 1
        if self.current_line < self.scroll_offset:
            self.scroll_offset -= 1

    def move_cursor_down(self):
        self.current_line += 1
        if self.current_line - self.scroll_offset > ALTURA // 30 - 2:
            self.scroll_offset += 1

    def move_cursor_left(self):
        self.cursor_pos -= 1

    def jump_to_end_of_previous_line(self):
        self.current_line -= 1
        self.cursor_pos = len(self.lines[self.current_line])

    def move_cursor_right(self):
        self.cursor_pos += 1

    def jump_to_start_of_next_line(self):
        self.current_line += 1
        self.cursor_pos = 0

    def insert_char_at_cursor(self, char):
        self.lines[self.current_line] = self.lines[self.current_line][:self.cursor_pos] + char + self.lines[self.current_line][self.cursor_pos:]
        self.cursor_pos += 1

    def draw_line_number(self, surface, index, line_number):
        text_surface = self.font.render(str(line_number), True, LINE_NUMBER_TEXT_COLOR)
        surface.blit(text_surface, (10, index * 30))


    def draw(self, surface):
        surface.fill(FUNDODARK)

        # Draw the vertical line number bar
        pygame.draw.rect(surface, LINE_NUMBER_COLOR, (0, 0, LINE_NUMBER_WIDTH, ALTURA))


        for index, line in enumerate(self.lines[self.scroll_offset:]):
            if index * 30 > ALTURA:
                break
            line_number = index + self.scroll_offset + 1
            self.draw_line_number(surface, index, line_number)
            self.draw_line(surface, index, line)


        
    def draw_line(self, surface, index, line):

        # Adjust horizontal scroll
        line = line[self.horizontal_scroll_offset:]

        # First, let's handle the selection background:
        SELECTION_COLOR = SELECAOBRIGHT

        # Default starting point for the non-selected text rendering:
        # Incremented by the width of three characters for padding
        x_pos = 10 + self.font.size('XXX')[0]

        if self.selection_start is not None and self.selection_end is not None:
            start_line, start_pos = min(self.selection_start, self.selection_end)
            end_line, end_pos = max(self.selection_start, self.selection_end)

            if start_line <= index + self.scroll_offset <= end_line:
                if start_line == end_line:
                    x1 = self.font.size(line[:start_pos])[0]
                    x2 = self.font.size(line[:end_pos])[0]
                elif index + self.scroll_offset == start_line:
                    x1 = self.font.size(line[:start_pos])[0]
                    x2 = self.font.size(line)[0]
                elif index + self.scroll_offset == end_line:
                    x1 = 0
                    x2 = self.font.size(line[:end_pos])[0]
                else:
                    x1 = 0
                    x2 = self.font.size(line)[0]

                pygame.draw.rect(surface, SELECTION_COLOR, (x_pos + x1, index * 30, x2 - x1, 30))
                
                # Render the segments of the line:
                # 1. Before selection
                before_text = self.font.render(line[:start_pos], True, TEXTOBRIGHT)
                surface.blit(before_text, (x_pos, index * 30))
                x_pos += self.font.size(line[:start_pos])[0]

                # 2. Selected text
                selected_text = self.font.render(line[start_pos:end_pos], True, BRANCO)
                surface.blit(selected_text, (x_pos, index * 30))
                x_pos += self.font.size(line[start_pos:end_pos])[0]

                # 3. After selection
                after_text = self.font.render(line[end_pos:], True, TEXTOBRIGHT)
                surface.blit(after_text, (x_pos, index * 30))

                return  # Return early since we've already handled this line's rendering.

        # Render the non-selected text
        rendered_text = self.font.render(line, True, TEXTOBRIGHT)
        surface.blit(rendered_text, (x_pos, index * 30))

        # And finally, render the cursor if the current line matches:
        if index == self.current_line - self.scroll_offset:
            self.draw_cursor(surface, index)

    def draw_cursor(self, surface, index):
        current_time = pygame.time.get_ticks()
        if current_time - self.last_cursor_toggle_time > 500:  # If 500ms have passed since the last toggle
            self.cursor_visible = not self.cursor_visible
            self.last_cursor_toggle_time = current_time
        
        if not self.cursor_visible:  # If the cursor is not visible, return early
            return
        
        # Calculate the width of three characters to create the desired padding.
        three_char_width = self.font.size('XXX')[0]

        cursor_offset = self.font.size(self.lines[self.current_line][:self.cursor_pos - self.horizontal_scroll_offset])[0]
        
        # Offset by the width of three characters.
        pygame.draw.line(surface, TEXTOBRIGHT, 
                        (10 + three_char_width + cursor_offset, index * 30), 
                        (10 + three_char_width + cursor_offset, index * 30 + 24), 
                        2)

    def push_undo(self):
        """Pushes the current state to the undo stack."""
        self.undo_stack.append(self.lines.copy())
        # Clear redo stack since we have a new action
        self.redo_stack.clear()

    def undo(self):
        """Reverts the editor to the previous state."""
        if self.undo_stack:
            self.redo_stack.append(self.lines.copy())
            self.lines = self.undo_stack.pop()

    def redo(self):
        """Redoes the previously undone action."""
        if self.redo_stack:
            self.undo_stack.append(self.lines.copy())
            self.lines = self.redo_stack.pop()


    def load_file(self, filename):
        try:
            with open(filename, 'r') as f:
                self.lines = f.readlines()
            # Remove newline characters from the end of each line
            self.lines = [line.rstrip() for line in self.lines]
        except Exception as e:
            print(f"Error loading file: {e}")


if __name__ == "__main__":

    # Create an instance of your TextEditor
    editor = TextEditor(fonte)

    if len(sys.argv) > 1:
        filename = sys.argv[1]
        editor.load_file(filename)

    rodando = True
    clock = pygame.time.Clock()

    # Create a list to store frames
    frames = []

    while rodando:
        for event in pygame.event.get():
            if event.type == QUIT:
                rodando = False
            elif event.type == KEYDOWN:
                editor.input(event)

        editor.draw(tela)
        pygame.display.flip()

        # Capture the frame and append to the list
        frame_data = pygame.surfarray.array3d(pygame.display.get_surface())
        frames.append(frame_data.transpose([1, 0, 2]))

        clock.tick(60)

    pygame.quit()

    # Save frames as MP4 video
    imageio.mimwrite('output_video.mp4', frames, fps=60)
