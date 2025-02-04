import pygame
import pyperclip
from typing import List, Optional, Tuple
from pygame.locals import (
    K_BACKSPACE, K_DELETE, K_RETURN, K_LEFT, K_RIGHT, K_UP, K_DOWN,
    K_HOME, K_END, K_PAGEUP, K_PAGEDOWN,
    K_c, K_v, K_x, K_z,
    KMOD_LCTRL, KMOD_RCTRL, KMOD_SHIFT,
    KEYDOWN, QUIT, MOUSEBUTTONDOWN, MOUSEBUTTONUP, MOUSEMOTION, MOUSEWHEEL, TEXTINPUT
)

# Configuration Constants
WIDTH, HEIGHT = 800, 600
BACKGROUND_COLOR = (30, 30, 30)
TEXT_COLOR = (230, 230, 230)
CURSOR_COLOR = (255, 255, 255)
SELECTION_COLOR = (50, 50, 150)
LINE_NUMBER_BG_COLOR = (40, 40, 40)
LINE_NUMBER_TEXT_COLOR = (150, 150, 150)
FONT_SIZE = 24
DRAWING_COLOR = (255, 255, 255, 255)
ERASER_COLOR = (0, 0, 0, 0)
ERASER_RADIUS = 10
DRAWING_LINE_WIDTH = 2


class TextEditor:
    """A simple text editor built using pygame."""

    def __init__(self, font: pygame.font.Font) -> None:
        self.font = font
        self.lines: List[str] = ['']
        self.current_line: int = 0
        self.cursor_pos: int = 0
        self.scroll_offset: int = 0
        self.horizontal_scroll_offset: int = 0
        self.selection_start: Optional[Tuple[int, int]] = None
        self.selection_end: Optional[Tuple[int, int]] = None
        self.undo_stack: List[Tuple[List[str], int, int, pygame.Surface]] = []
        self.redo_stack: List[Tuple[List[str], int, int, pygame.Surface]] = []
        self.cursor_visible: bool = True
        self.last_cursor_toggle_time: int = pygame.time.get_ticks()

        # Drawing surface for freehand drawing/erasing
        self.drawing_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.drawing_surface = self.drawing_surface.convert_alpha()
        self.drawing_scroll_offset: int = 0

        # Mouse drawing state
        self.left_button_down = False
        self.right_button_down = False
        self.last_pos: Optional[Tuple[int, int]] = None

    def add_to_undo_stack(self) -> None:
        """Add the current state to the undo stack and clear the redo stack."""
        drawing_copy = self.drawing_surface.copy()
        self.undo_stack.append((self.lines.copy(), self.current_line, self.cursor_pos, drawing_copy))
        # Clear redo history on a new action
        self.redo_stack.clear()
        # Optional: Limit the undo history to the last 100 states
        if len(self.undo_stack) > 100:
            self.undo_stack.pop(0)

    def handle_event(self, event: pygame.event.EventType) -> None:
        """Handle a pygame event."""
        if event.type == TEXTINPUT:
            # TEXTINPUT events provide fully composed text (e.g. accented characters)
            self.insert_character(event.text)
        elif event.type == KEYDOWN:
            ctrl_pressed = event.mod & (KMOD_LCTRL | KMOD_RCTRL)
            shift_pressed = bool(event.mod & KMOD_SHIFT)
            # Process control shortcuts
            if ctrl_pressed:
                self.handle_ctrl_shortcuts(event, shift_pressed)
            else:
                # For non-text keys (e.g. backspace, arrow keys, etc) add undo state first
                if event.key in {
                    K_BACKSPACE, K_DELETE, K_RETURN, K_HOME, K_END,
                    K_PAGEUP, K_PAGEDOWN, K_LEFT, K_RIGHT, K_UP, K_DOWN
                }:
                    self.add_to_undo_stack()
                self.handle_regular_input(event, shift_pressed)
        elif event.type == MOUSEWHEEL:
            self.handle_scroll(event)
        elif event.type == MOUSEBUTTONDOWN:
            if event.button == 1:  # Left mouse button (drawing)
                self.add_to_undo_stack()
                self.left_button_down = True
                self.last_pos = (event.pos[0], event.pos[1] + self.drawing_scroll_offset)
            elif event.button == 3:  # Right mouse button (erasing)
                self.add_to_undo_stack()
                self.right_button_down = True
                self.last_pos = (event.pos[0], event.pos[1] + self.drawing_scroll_offset)
        elif event.type == MOUSEBUTTONUP:
            if event.button == 1:
                self.left_button_down = False
                self.last_pos = None
            elif event.button == 3:
                self.right_button_down = False
                self.last_pos = None
        elif event.type == MOUSEMOTION:
            self.handle_mouse_motion(event)

    def handle_mouse_motion(self, event: pygame.event.EventType) -> None:
        """Handle mouse movement for drawing/erasing."""
        if self.left_button_down or self.right_button_down:
            current_pos = (event.pos[0], event.pos[1] + self.drawing_scroll_offset)
            if self.last_pos is not None:
                if self.left_button_down:
                    pygame.draw.line(self.drawing_surface, DRAWING_COLOR, self.last_pos, current_pos, DRAWING_LINE_WIDTH)
                elif self.right_button_down:
                    eraser_surface = pygame.Surface((ERASER_RADIUS * 2, ERASER_RADIUS * 2), pygame.SRCALPHA)
                    pygame.draw.circle(eraser_surface, ERASER_COLOR, (ERASER_RADIUS, ERASER_RADIUS), ERASER_RADIUS)
                    self.drawing_surface.blit(
                        eraser_surface,
                        (current_pos[0] - ERASER_RADIUS, current_pos[1] - ERASER_RADIUS),
                        special_flags=pygame.BLEND_RGBA_MIN
                    )
                self.last_pos = current_pos

    def handle_scroll(self, event: pygame.event.EventType) -> None:
        """Handle mouse wheel scrolling."""
        font_height = self.font.get_height()
        max_scroll_offset = max(0, len(self.lines) - HEIGHT // font_height + 1)

        # Adjust vertical scrolling based on wheel movement
        self.scroll_offset = max(0, min(max_scroll_offset, self.scroll_offset - event.y))
        self.drawing_scroll_offset = self.scroll_offset * font_height
        self.update_scroll()

    def handle_ctrl_shortcuts(self, event: pygame.event.EventType, shift_pressed: bool) -> None:
        """Handle keyboard shortcuts with the Control key."""
        if event.key == K_c:
            self.copy_text()
        elif event.key == K_v:
            self.add_to_undo_stack()
            self.paste_text()
        elif event.key == K_x:
            self.add_to_undo_stack()
            self.cut_text()
        elif event.key == K_z:
            if not shift_pressed:
                self.undo()
            else:
                self.redo()
        elif event.key in (K_LEFT, K_RIGHT):
            self.move_word(forward=(event.key == K_RIGHT), shift_pressed=shift_pressed)

    def handle_regular_input(self, event: pygame.event.EventType, shift_pressed: bool) -> None:
        """Handle non-text keyboard input."""
        key_actions = {
            K_BACKSPACE: self.handle_backspace,
            K_DELETE: self.handle_delete,
            K_RETURN: self.handle_return,
            K_HOME: lambda: self.move_home(shift_pressed),
            K_END: lambda: self.move_end(shift_pressed),
            K_PAGEUP: lambda: self.move_pages(-1, shift_pressed),
            K_PAGEDOWN: lambda: self.move_pages(1, shift_pressed),
            K_LEFT: lambda: self.move_cursor(K_LEFT, shift_pressed),
            K_RIGHT: lambda: self.move_cursor(K_RIGHT, shift_pressed),
            K_UP: lambda: self.move_cursor(K_UP, shift_pressed),
            K_DOWN: lambda: self.move_cursor(K_DOWN, shift_pressed),
        }
        action = key_actions.get(event.key)
        if action:
            action()
        # Note: For text insertion we now rely on TEXTINPUT events.

    def move_cursor(self, direction: int, shift_pressed: bool = False) -> None:
        """Move the cursor in the specified direction."""
        if shift_pressed:
            if self.selection_start is None:
                self.selection_start = (self.current_line, self.cursor_pos)
        else:
            self.selection_start = None
            self.selection_end = None

        if direction == K_LEFT:
            if self.cursor_pos > 0:
                self.cursor_pos -= 1
            elif self.current_line > 0:
                self.current_line -= 1
                self.cursor_pos = len(self.lines[self.current_line])
        elif direction == K_RIGHT:
            if self.cursor_pos < len(self.lines[self.current_line]):
                self.cursor_pos += 1
            elif self.current_line < len(self.lines) - 1:
                self.current_line += 1
                self.cursor_pos = 0
        elif direction == K_UP and self.current_line > 0:
            self.current_line -= 1
            self.cursor_pos = min(self.cursor_pos, len(self.lines[self.current_line]))
        elif direction == K_DOWN and self.current_line < len(self.lines) - 1:
            self.current_line += 1
            self.cursor_pos = min(self.cursor_pos, len(self.lines[self.current_line]))

        if shift_pressed:
            self.selection_end = (self.current_line, self.cursor_pos)
        else:
            self.selection_start = None
            self.selection_end = None
        self.update_scroll()

    def move_home(self, shift_pressed: bool = False) -> None:
        """Move the cursor to the beginning of the line."""
        if shift_pressed:
            if self.selection_start is None:
                self.selection_start = (self.current_line, self.cursor_pos)
            self.cursor_pos = 0
            self.selection_end = (self.current_line, self.cursor_pos)
        else:
            self.cursor_pos = 0
            self.selection_start = None
            self.selection_end = None
        self.update_scroll()

    def move_end(self, shift_pressed: bool = False) -> None:
        """Move the cursor to the end of the line."""
        if shift_pressed:
            if self.selection_start is None:
                self.selection_start = (self.current_line, self.cursor_pos)
            self.cursor_pos = len(self.lines[self.current_line])
            self.selection_end = (self.current_line, self.cursor_pos)
        else:
            self.cursor_pos = len(self.lines[self.current_line])
            self.selection_start = None
            self.selection_end = None
        self.update_scroll()

    def move_word(self, forward: bool, shift_pressed: bool = False) -> None:
        """Move the cursor word by word."""
        line = self.lines[self.current_line]
        if shift_pressed:
            if self.selection_start is None:
                self.selection_start = (self.current_line, self.cursor_pos)
        else:
            self.selection_start = None
            self.selection_end = None

        if forward:
            while self.cursor_pos < len(line) and not line[self.cursor_pos].isalnum():
                self.cursor_pos += 1
            while self.cursor_pos < len(line) and line[self.cursor_pos].isalnum():
                self.cursor_pos += 1
            if self.cursor_pos >= len(line) and self.current_line < len(self.lines) - 1:
                self.current_line += 1
                self.cursor_pos = 0
        else:
            while self.cursor_pos > 0 and not line[self.cursor_pos - 1].isalnum():
                self.cursor_pos -= 1
            while self.cursor_pos > 0 and line[self.cursor_pos - 1].isalnum():
                self.cursor_pos -= 1
            if self.cursor_pos == 0 and self.current_line > 0:
                self.current_line -= 1
                self.cursor_pos = len(self.lines[self.current_line])

        if shift_pressed:
            self.selection_end = (self.current_line, self.cursor_pos)
        else:
            self.selection_start = None
            self.selection_end = None
        self.update_scroll()

    def move_pages(self, direction: int, shift_pressed: bool = False) -> None:
        """Move the cursor up or down by one page."""
        visible_lines = HEIGHT // self.font.get_height()
        if shift_pressed:
            if self.selection_start is None:
                self.selection_start = (self.current_line, self.cursor_pos)
        else:
            self.selection_start = None
            self.selection_end = None

        self.current_line = max(0, min(len(self.lines) - 1, self.current_line + direction * visible_lines))
        if shift_pressed:
            self.selection_end = (self.current_line, self.cursor_pos)
        else:
            self.selection_start = None
            self.selection_end = None
        self.update_scroll()

    def handle_backspace(self) -> None:
        """Handle the backspace key."""
        if self.selection_start and self.selection_end:
            self.delete_selection()
        elif self.cursor_pos > 0:
            line = self.lines[self.current_line]
            self.lines[self.current_line] = line[:self.cursor_pos - 1] + line[self.cursor_pos:]
            self.cursor_pos -= 1
        elif self.current_line > 0:
            prev_line_length = len(self.lines[self.current_line - 1])
            self.lines[self.current_line - 1] += self.lines[self.current_line]
            del self.lines[self.current_line]
            self.current_line -= 1
            self.cursor_pos = prev_line_length
        self.update_scroll()

    def handle_delete(self) -> None:
        """Handle the delete key."""
        if self.selection_start and self.selection_end:
            self.delete_selection()
        elif self.cursor_pos < len(self.lines[self.current_line]):
            line = self.lines[self.current_line]
            self.lines[self.current_line] = line[:self.cursor_pos] + line[self.cursor_pos + 1:]
        elif self.current_line < len(self.lines) - 1:
            self.lines[self.current_line] += self.lines[self.current_line + 1]
            del self.lines[self.current_line + 1]
        self.update_scroll()

    def handle_return(self) -> None:
        """Handle the return (enter) key."""
        if self.selection_start and self.selection_end:
            self.delete_selection()
        current_line_text = self.lines[self.current_line]
        self.lines.insert(self.current_line + 1, current_line_text[self.cursor_pos:])
        self.lines[self.current_line] = current_line_text[:self.cursor_pos]
        self.current_line += 1
        self.cursor_pos = 0
        self.update_scroll()

    def insert_character(self, char: str) -> None:
        """Insert a character (or characters) at the current cursor position."""
        if not char:
            return
        if self.selection_start and self.selection_end:
            self.delete_selection()

        line = self.lines[self.current_line]
        self.lines[self.current_line] = line[:self.cursor_pos] + char + line[self.cursor_pos:]
        self.cursor_pos += len(char)
        self.update_scroll()

    def update_scroll(self) -> None:
        """Update scroll offsets based on the cursor position."""
        font_height = self.font.get_height()
        visible_lines = HEIGHT // font_height

        # Update vertical scrolling to ensure the current line is visible.
        if self.current_line < self.scroll_offset:
            self.scroll_offset = self.current_line
        elif self.current_line >= self.scroll_offset + visible_lines:
            self.scroll_offset = self.current_line - visible_lines + 1

        # Update horizontal scrolling to keep the cursor visible.
        cursor_x = self.font.size(self.lines[self.current_line][:self.cursor_pos])[0]
        if cursor_x < self.horizontal_scroll_offset:
            self.horizontal_scroll_offset = max(0, cursor_x - 50)
        elif cursor_x > self.horizontal_scroll_offset + WIDTH - 100:
            self.horizontal_scroll_offset = cursor_x - WIDTH + 100

        self.drawing_scroll_offset = self.scroll_offset * font_height

    def copy_text(self) -> None:
        """Copy the selected text to the clipboard."""
        if self.selection_start and self.selection_end:
            start, end = self.get_selection_range()
            text = self.get_selected_text(start, end)
            pyperclip.copy(text)

    def cut_text(self) -> None:
        """Cut the selected text to the clipboard."""
        if self.selection_start and self.selection_end:
            self.copy_text()
            self.delete_selection()

    def paste_text(self) -> None:
        """Paste text from the clipboard at the cursor position."""
        text = pyperclip.paste()
        if self.selection_start and self.selection_end:
            self.delete_selection()
        lines = text.split('\n')
        current_line_text = self.lines[self.current_line]
        # Insert the first line of the pasted text
        self.lines[self.current_line] = (
            current_line_text[:self.cursor_pos] + lines[0] + current_line_text[self.cursor_pos:]
        )
        self.cursor_pos += len(lines[0])
        # If there are additional lines, insert them into the text buffer.
        if len(lines) > 1:
            self.lines[self.current_line + 1:self.current_line + 1] = lines[1:]
            self.current_line += len(lines) - 1
            self.cursor_pos = len(lines[-1])
        self.update_scroll()

    def delete_selection(self) -> None:
        """Delete the currently selected text."""
        if self.selection_start and self.selection_end:
            start, end = self.get_selection_range()
            if start[0] == end[0]:
                line = self.lines[start[0]]
                self.lines[start[0]] = line[:start[1]] + line[end[1]:]
            else:
                self.lines[start[0]] = self.lines[start[0]][:start[1]] + self.lines[end[0]][end[1]:]
                del self.lines[start[0] + 1:end[0] + 1]
            self.current_line, self.cursor_pos = start
            self.selection_start = None
            self.selection_end = None
            self.update_scroll()

    def get_selection_range(self) -> Tuple[Tuple[int, int], Tuple[int, int]]:
        """Return a tuple (start, end) for the current selection."""
        assert self.selection_start is not None and self.selection_end is not None
        start, end = self.selection_start, self.selection_end
        if start > end:
            start, end = end, start
        return start, end

    def get_selected_text(self, start: Tuple[int, int], end: Tuple[int, int]) -> str:
        """Retrieve text within the selection."""
        if start[0] == end[0]:
            return self.lines[start[0]][start[1]:end[1]]
        else:
            selected_text = [self.lines[start[0]][start[1]:]]
            selected_text.extend(self.lines[start[0] + 1:end[0]])
            selected_text.append(self.lines[end[0]][:end[1]])
            return "\n".join(selected_text)

    def undo(self) -> None:
        """Undo the last action."""
        if self.undo_stack:
            # Save current state for redo
            self.redo_stack.append((self.lines.copy(), self.current_line, self.cursor_pos, self.drawing_surface.copy()))
            self.lines, self.current_line, self.cursor_pos, self.drawing_surface = self.undo_stack.pop()
            self.update_scroll()

    def redo(self) -> None:
        """Redo the last undone action."""
        if self.redo_stack:
            # Save current state for undo
            self.undo_stack.append((self.lines.copy(), self.current_line, self.cursor_pos, self.drawing_surface.copy()))
            self.lines, self.current_line, self.cursor_pos, self.drawing_surface = self.redo_stack.pop()
            self.update_scroll()

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the entire editor interface."""
        surface.fill(BACKGROUND_COLOR)
        self.draw_line_numbers(surface)
        self.draw_text(surface)
        self.draw_selection(surface)
        self.draw_cursor(surface)
        # Blit the freehand drawing layer (scroll-adjusted)
        surface.blit(self.drawing_surface, (0, -self.drawing_scroll_offset))

    def draw_line_numbers(self, surface: pygame.Surface) -> None:
        """Draw line numbers in a left margin."""
        pygame.draw.rect(surface, LINE_NUMBER_BG_COLOR, (0, 0, 50, HEIGHT))
        font_height = self.font.get_height()
        for i, line_num in enumerate(range(self.scroll_offset + 1, self.scroll_offset + HEIGHT // font_height + 1)):
            text_surface = self.font.render(str(line_num), True, LINE_NUMBER_TEXT_COLOR)
            surface.blit(text_surface, (5, i * font_height))

    def draw_text(self, surface: pygame.Surface) -> None:
        """Render the text lines."""
        font_height = self.font.get_height()
        for i, line in enumerate(self.lines[self.scroll_offset:]):
            if i * font_height > HEIGHT:
                break
            text_surface = self.font.render(line[self.horizontal_scroll_offset:], True, TEXT_COLOR)
            surface.blit(text_surface, (60, i * font_height))

    def draw_cursor(self, surface: pygame.Surface) -> None:
        """Draw the blinking text cursor."""
        if self.cursor_visible:
            cursor_x = 60 + self.font.size(self.lines[self.current_line][:self.cursor_pos])[0] - self.horizontal_scroll_offset
            cursor_y = (self.current_line - self.scroll_offset) * self.font.get_height()
            pygame.draw.line(surface, CURSOR_COLOR, (cursor_x, cursor_y), (cursor_x, cursor_y + self.font.get_height()), 2)

    def draw_selection(self, surface: pygame.Surface) -> None:
        """Highlight the selected text."""
        if self.selection_start and self.selection_end:
            start, end = self.get_selection_range()
            font_height = self.font.get_height()
            for line_num in range(start[0], end[0] + 1):
                if line_num < self.scroll_offset or line_num >= self.scroll_offset + HEIGHT // font_height:
                    continue
                line_start = 0 if line_num != start[0] else start[1]
                line_end = len(self.lines[line_num]) if line_num != end[0] else end[1]
                start_x = 60 + self.font.size(self.lines[line_num][:line_start])[0] - self.horizontal_scroll_offset
                end_x = 60 + self.font.size(self.lines[line_num][:line_end])[0] - self.horizontal_scroll_offset
                y = (line_num - self.scroll_offset) * font_height
                pygame.draw.rect(surface, SELECTION_COLOR, (start_x, y, end_x - start_x, font_height))

    def toggle_cursor(self) -> None:
        """Toggle the visibility of the cursor to achieve a blinking effect."""
        current_time = pygame.time.get_ticks()
        if current_time - self.last_cursor_toggle_time > 500:
            self.cursor_visible = not self.cursor_visible
            self.last_cursor_toggle_time = current_time


def main() -> None:
    """Main loop to run the text editor."""
    pygame.init()
    # Enable key repeat for non-text keys (TEXTINPUT handles text input)
    pygame.key.set_repeat(300, 50)
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Code Wizard")
    font = pygame.font.SysFont("monospace", FONT_SIZE)
    editor = TextEditor(font)
    clock = pygame.time.Clock()
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            else:
                editor.handle_event(event)

        editor.toggle_cursor()
        editor.draw(screen)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
