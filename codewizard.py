import pygame
import pyperclip
import sys
from typing import List, Optional, Tuple
from pygame.locals import (
    K_BACKSPACE, K_DELETE, K_RETURN, K_LEFT, K_RIGHT, K_UP, K_DOWN,
    K_HOME, K_END, K_PAGEUP, K_PAGEDOWN,
    K_c, K_v, K_x, K_z, K_s,  # Added K_s for save shortcut.
    KMOD_LCTRL, KMOD_RCTRL, KMOD_LMETA, KMOD_RMETA, KMOD_SHIFT, KMOD_ALT,
    KEYDOWN, QUIT, MOUSEBUTTONDOWN, MOUSEBUTTONUP, MOUSEMOTION, MOUSEWHEEL, TEXTINPUT,
    VIDEORESIZE
)

# Configuration Constants
INITIAL_WIDTH, INITIAL_HEIGHT = 800, 600
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
LINE_NUMBER_WIDTH = 50
TEXT_X_OFFSET = 60  # Margin for text (accounts for line numbers)

class TextEditor:
    """A simple text editor with drawing capability and improved undo/redo support.
    
    Supports loading a file at startup and saving the edited text with a shortcut.
    Also, on macOS, if the Option key is held while clicking, the cursor jumps
    to the clicked line and column.
    """

    def __init__(self, font: pygame.font.Font, width: int, height: int, file_path: Optional[str] = None) -> None:
        self.font = font
        self.width = width
        self.height = height
        self.file_path: Optional[str] = file_path

        # Load file if a file path is provided, otherwise start with an empty line.
        if file_path is not None:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                self.lines: List[str] = content.splitlines()
                if not self.lines:
                    self.lines = ['']
            except Exception as e:
                print(f"Error loading file {file_path}: {e}")
                self.lines = ['']
        else:
            self.lines: List[str] = ['']

        self.current_line: int = 0
        self.cursor_pos: int = 0
        self.scroll_offset: int = 0
        # horizontal_scroll_offset is in pixels.
        self.horizontal_scroll_offset: int = 0
        self.selection_start: Optional[Tuple[int, int]] = None
        self.selection_end: Optional[Tuple[int, int]] = None
        # Undo/redo stacks storing (lines, current_line, cursor_pos, drawing_surface)
        self.undo_stack: List[Tuple[List[str], int, int, pygame.Surface]] = []
        self.redo_stack: List[Tuple[List[str], int, int, pygame.Surface]] = []
        self.cursor_visible: bool = True
        self.last_cursor_toggle_time: int = pygame.time.get_ticks()

        # --- NEW: Create a persistent drawing canvas.
        # We use a canvas that is larger than the visible window so that drawings
        # persist even when scrolling or resizing. (We start with a 2000x2000 surface.)
        self.canvas_width = max(2000, width)
        self.canvas_height = max(2000, height)
        self.drawing_surface = pygame.Surface((self.canvas_width, self.canvas_height), pygame.SRCALPHA).convert_alpha()
        self.drawing_surface.fill((0, 0, 0, 0))  # Make sure it is transparent.
        # The vertical offset (in pixels) used when blitting the drawing layer.
        self.drawing_scroll_offset: int = 0

        # Mouse drawing state
        self.left_button_down = False
        self.right_button_down = False
        self.last_pos: Optional[Tuple[int, int]] = None
        self.drawing_in_progress = False  # Track drawing stroke as a single action

    def ensure_canvas_size(self, x: int, y: int) -> None:
        """Ensure the drawing canvas is large enough to include the point (x, y) (in document coordinates)."""
        current_width, current_height = self.drawing_surface.get_size()
        new_width = current_width
        new_height = current_height
        margin = 100  # extra space
        if x >= current_width:
            new_width = x + margin
        if y >= current_height:
            new_height = y + margin
        if new_width != current_width or new_height != current_height:
            new_surface = pygame.Surface((new_width, new_height), pygame.SRCALPHA).convert_alpha()
            new_surface.fill((0, 0, 0, 0))
            new_surface.blit(self.drawing_surface, (0, 0))
            self.drawing_surface = new_surface

    def resize(self, width: int, height: int) -> None:
        """Resize the editor’s view (not the persistent drawing canvas) and update width and height."""
        # We no longer recreate the drawing canvas on resize.
        self.width = width
        self.height = height

    def add_to_undo_stack(self) -> None:
        """Save the current state into the undo stack and clear the redo stack."""
        drawing_copy = self.drawing_surface.copy()
        # Save a copy of text lines and the drawing surface.
        self.undo_stack.append((self.lines.copy(), self.current_line, self.cursor_pos, drawing_copy))
        self.redo_stack.clear()
        # Limit the undo history to the last 100 states.
        if len(self.undo_stack) > 100:
            self.undo_stack.pop(0)

    def handle_event(self, event: pygame.event.EventType) -> None:
        """Process a pygame event."""
        if event.type == TEXTINPUT:
            self.insert_character(event.text)
        elif event.type == KEYDOWN:
            # Support both Control and Command (Meta) keys for shortcuts.
            ctrl_cmd_pressed = event.mod & (KMOD_LCTRL | KMOD_RCTRL | KMOD_LMETA | KMOD_RMETA)
            shift_pressed = bool(event.mod & KMOD_SHIFT)
            if ctrl_cmd_pressed:
                self.handle_ctrl_shortcuts(event, shift_pressed)
            else:
                # For keys that change text, record the state first.
                if event.key in {
                    K_BACKSPACE, K_DELETE, K_RETURN, K_HOME, K_END,
                    K_PAGEUP, K_PAGEDOWN, K_LEFT, K_RIGHT, K_UP, K_DOWN
                }:
                    self.add_to_undo_stack()
                self.handle_regular_input(event, shift_pressed)
        elif event.type == MOUSEWHEEL:
            self.handle_scroll(event)
        elif event.type == MOUSEBUTTONDOWN:
            # NEW FEATURE: On macOS, if Option (Alt) is held during a left-click,
            # move the cursor to the clicked position.
            if sys.platform == "darwin" and (pygame.key.get_mods() & KMOD_ALT):
                self.handle_option_click(event)
                return

            # For drawing/erasing actions, start a new drawing stroke (if one isn’t already in progress)
            if event.button in (1, 3):  # 1: left (drawing), 3: right (erasing)
                if not self.drawing_in_progress:
                    self.add_to_undo_stack()
                    self.drawing_in_progress = True
                if event.button == 1:
                    self.left_button_down = True
                elif event.button == 3:
                    self.right_button_down = True
                # Convert the mouse position to document coordinates.
                doc_x = event.pos[0] - TEXT_X_OFFSET + self.horizontal_scroll_offset
                doc_y = event.pos[1] + self.drawing_scroll_offset
                self.ensure_canvas_size(doc_x, doc_y)
                self.last_pos = (doc_x, doc_y)
        elif event.type == MOUSEBUTTONUP:
            if event.button == 1:
                self.left_button_down = False
            elif event.button == 3:
                self.right_button_down = False
            # End drawing stroke.
            self.drawing_in_progress = False
            self.last_pos = None
        elif event.type == MOUSEMOTION:
            self.handle_mouse_motion(event)

    def handle_option_click(self, event: pygame.event.EventType) -> None:
        """NEW FEATURE: On macOS, when the Option key is held and the user clicks,
        move the cursor to the corresponding line and column.
        """
        font_height = self.font.get_height()
        # Calculate the target line based on the y-coordinate and scroll offset.
        target_line = self.scroll_offset + event.pos[1] // font_height
        # Clamp the target line to available lines.
        target_line = max(0, min(target_line, len(self.lines) - 1))
        line_text = self.lines[target_line]
        # Calculate the effective x coordinate relative to the start of text (adjusting for scrolling).
        effective_x = event.pos[0] - TEXT_X_OFFSET + self.horizontal_scroll_offset
        if effective_x < 0:
            target_col = 0
        else:
            target_col = 0
            # Increment target_col until the width of the rendered substring exceeds effective_x.
            while target_col < len(line_text) and self.font.size(line_text[:target_col + 1])[0] <= effective_x:
                target_col += 1

        # Set the cursor to the computed line and column.
        self.current_line = target_line
        self.cursor_pos = target_col
        # Clear any selection.
        self.selection_start = None
        self.selection_end = None
        self.update_scroll()

    def handle_mouse_motion(self, event: pygame.event.EventType) -> None:
        """Handle drawing/erasing during mouse motion."""
        if self.left_button_down or self.right_button_down:
            # Convert current mouse position to document coordinates.
            doc_x = event.pos[0] - TEXT_X_OFFSET + self.horizontal_scroll_offset
            doc_y = event.pos[1] + self.drawing_scroll_offset
            self.ensure_canvas_size(doc_x, doc_y)
            current_pos = (doc_x, doc_y)
            if self.last_pos is not None:
                if self.left_button_down:
                    pygame.draw.line(
                        self.drawing_surface,
                        DRAWING_COLOR,
                        self.last_pos,
                        current_pos,
                        DRAWING_LINE_WIDTH
                    )
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
        """Handle vertical scrolling using the mouse wheel."""
        font_height = self.font.get_height()
        max_scroll_offset = max(0, len(self.lines) - self.height // font_height + 1)
        self.scroll_offset = max(0, min(max_scroll_offset, self.scroll_offset - event.y))
        self.drawing_scroll_offset = self.scroll_offset * font_height
        self.update_scroll()

    def handle_ctrl_shortcuts(self, event: pygame.event.EventType, shift_pressed: bool) -> None:
        """Process shortcuts when Control/Command key is pressed."""
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
        elif event.key == K_s:
            self.save_file()
        elif event.key in (K_LEFT, K_RIGHT):
            self.move_word(forward=(event.key == K_RIGHT), shift_pressed=shift_pressed)

    def handle_regular_input(self, event: pygame.event.EventType, shift_pressed: bool) -> None:
        """Process non-shortcut key events."""
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
        visible_lines = self.height // self.font.get_height()
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
        """Insert character(s) at the current cursor position."""
        if not char:
            return
        if self.selection_start and self.selection_end:
            self.delete_selection()

        line = self.lines[self.current_line]
        self.lines[self.current_line] = line[:self.cursor_pos] + char + line[self.cursor_pos:]
        self.cursor_pos += len(char)
        self.update_scroll()

    def update_scroll(self) -> None:
        """Adjust scroll offsets to keep the cursor visible."""
        font_height = self.font.get_height()
        visible_lines = self.height // font_height
        if self.current_line < self.scroll_offset:
            self.scroll_offset = self.current_line
        elif self.current_line >= self.scroll_offset + visible_lines:
            self.scroll_offset = self.current_line - visible_lines + 1

        # Calculate cursor's pixel position in the line.
        cursor_x = self.font.size(self.lines[self.current_line][:self.cursor_pos])[0]
        # Adjust horizontal scroll so that the cursor is within a left/right margin.
        if cursor_x < self.horizontal_scroll_offset:
            self.horizontal_scroll_offset = max(0, cursor_x - 50)
        elif cursor_x > self.horizontal_scroll_offset + self.width - 100:
            self.horizontal_scroll_offset = cursor_x - self.width + 100

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
        self.lines[self.current_line] = (
            current_line_text[:self.cursor_pos] + lines[0] + current_line_text[self.cursor_pos:]
        )
        self.cursor_pos += len(lines[0])
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
        """Return the normalized (start, end) positions for the selection."""
        assert self.selection_start is not None and self.selection_end is not None
        start, end = self.selection_start, self.selection_end
        if start > end:
            start, end = end, start
        return start, end

    def get_selected_text(self, start: Tuple[int, int], end: Tuple[int, int]) -> str:
        """Retrieve text within the selection."""
        if start[0] == end[0]:
            return self.lines[start[0]][start[1]:end[1]]
        selected_text = [self.lines[start[0]][start[1]:]]
        selected_text.extend(self.lines[start[0] + 1:end[0]])
        selected_text.append(self.lines[end[0]][:end[1]])
        return "\n".join(selected_text)

    def undo(self) -> None:
        """Undo the last action."""
        if self.undo_stack:
            # Save the current state for redo.
            self.redo_stack.append((self.lines.copy(), self.current_line, self.cursor_pos, self.drawing_surface.copy()))
            self.lines, self.current_line, self.cursor_pos, self.drawing_surface = self.undo_stack.pop()
            self.update_scroll()

    def redo(self) -> None:
        """Redo the last undone action."""
        if self.redo_stack:
            self.undo_stack.append((self.lines.copy(), self.current_line, self.cursor_pos, self.drawing_surface.copy()))
            self.lines, self.current_line, self.cursor_pos, self.drawing_surface = self.redo_stack.pop()
            self.update_scroll()

    def save_file(self) -> None:
        """Save the current text to the file.
        
        If no file was loaded, the text is saved to "untitled.txt".
        """
        if not self.file_path:
            self.file_path = "untitled.txt"
        try:
            with open(self.file_path, 'w') as f:
                f.write("\n".join(self.lines))
            print(f"File saved to {self.file_path}")
        except Exception as e:
            print(f"Error saving file {self.file_path}: {e}")

    def draw(self, surface: pygame.Surface) -> None:
        """Render the editor interface on the given surface."""
        surface.fill(BACKGROUND_COLOR)
        self.draw_line_numbers(surface)
        self.draw_text(surface)
        self.draw_selection(surface)
        self.draw_cursor(surface)
        # Blit the freehand drawing layer.
        # The drawing canvas is in document coordinates.
        # Its origin (0,0) corresponds to the top‐left of the text area.
        # To map it to the screen, we shift by (TEXT_X_OFFSET - horizontal_scroll_offset, -drawing_scroll_offset).
        surface.blit(self.drawing_surface, (TEXT_X_OFFSET - self.horizontal_scroll_offset, -self.drawing_scroll_offset))

    def draw_line_numbers(self, surface: pygame.Surface) -> None:
        """Render the line numbers in the left margin."""
        pygame.draw.rect(surface, LINE_NUMBER_BG_COLOR, (0, 0, LINE_NUMBER_WIDTH, self.height))
        font_height = self.font.get_height()
        for i, line_num in enumerate(range(self.scroll_offset + 1, self.scroll_offset + self.height // font_height + 1)):
            text_surface = self.font.render(str(line_num), True, LINE_NUMBER_TEXT_COLOR)
            surface.blit(text_surface, (5, i * font_height))

    def draw_text(self, surface: pygame.Surface) -> None:
        """Render the text lines with proper horizontal scrolling.
        
        The entire line is rendered and then blitted with an x-offset of TEXT_X_OFFSET minus
        the horizontal_scroll_offset.
        """
        font_height = self.font.get_height()
        for i, line in enumerate(self.lines[self.scroll_offset:]):
            if i * font_height > self.height:
                break
            # Render the full line.
            text_surface = self.font.render(line, True, TEXT_COLOR)
            # Blit the text shifted horizontally by the scroll offset.
            surface.blit(text_surface, (TEXT_X_OFFSET - self.horizontal_scroll_offset, i * font_height))

    def draw_cursor(self, surface: pygame.Surface) -> None:
        """Render the blinking text cursor."""
        if self.cursor_visible:
            cursor_x = TEXT_X_OFFSET + self.font.size(self.lines[self.current_line][:self.cursor_pos])[0] - self.horizontal_scroll_offset
            cursor_y = (self.current_line - self.scroll_offset) * self.font.get_height()
            pygame.draw.line(surface, CURSOR_COLOR, (cursor_x, cursor_y),
                             (cursor_x, cursor_y + self.font.get_height()), 2)

    def draw_selection(self, surface: pygame.Surface) -> None:
        """Highlight the selected text."""
        if self.selection_start and self.selection_end:
            start, end = self.get_selection_range()
            font_height = self.font.get_height()
            for line_num in range(start[0], end[0] + 1):
                if line_num < self.scroll_offset or line_num >= self.scroll_offset + self.height // font_height:
                    continue
                line_start = 0 if line_num != start[0] else start[1]
                line_end = len(self.lines[line_num]) if line_num != end[0] else end[1]
                start_x = TEXT_X_OFFSET + self.font.size(self.lines[line_num][:line_start])[0] - self.horizontal_scroll_offset
                end_x = TEXT_X_OFFSET + self.font.size(self.lines[line_num][:line_end])[0] - self.horizontal_scroll_offset
                y = (line_num - self.scroll_offset) * font_height
                pygame.draw.rect(surface, SELECTION_COLOR, (start_x, y, end_x - start_x, font_height))

    def toggle_cursor(self) -> None:
        """Toggle the visibility of the cursor to create a blinking effect."""
        current_time = pygame.time.get_ticks()
        if current_time - self.last_cursor_toggle_time > 500:
            self.cursor_visible = not self.cursor_visible
            self.last_cursor_toggle_time = current_time

def main() -> None:
    """Main loop to run the text editor."""
    pygame.init()
    # Enable key repeat for non-text keys.
    pygame.key.set_repeat(300, 50)
    screen = pygame.display.set_mode((INITIAL_WIDTH, INITIAL_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("Code Wizard")
    font = pygame.font.SysFont("monospace", FONT_SIZE)

    # Load a file if provided as a command-line argument.
    file_path = sys.argv[1] if len(sys.argv) > 1 else None
    if file_path:
        print(f"Loading file: {file_path}")

    editor = TextEditor(font, INITIAL_WIDTH, INITIAL_HEIGHT, file_path)
    clock = pygame.time.Clock()
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            elif event.type == VIDEORESIZE:
                # Update the display and editor on window resize.
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                editor.resize(event.w, event.h)
            else:
                editor.handle_event(event)

        editor.toggle_cursor()
        editor.draw(screen)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()
