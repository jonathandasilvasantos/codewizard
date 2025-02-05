import sys
import re
import pygame
import pyperclip
from typing import List, Optional, Tuple
from pygame.locals import (
    K_BACKSPACE, K_DELETE, K_RETURN, K_LEFT, K_RIGHT, K_UP, K_DOWN,
    K_HOME, K_END, K_PAGEUP, K_PAGEDOWN,
    K_c, K_v, K_x, K_z, K_s,
    KMOD_LCTRL, KMOD_RCTRL, KMOD_LMETA, KMOD_RMETA, KMOD_SHIFT, KMOD_ALT,
    KEYDOWN, QUIT, MOUSEBUTTONDOWN, MOUSEBUTTONUP, MOUSEMOTION, MOUSEWHEEL, TEXTINPUT,
    VIDEORESIZE
)

# --------------------
# Configuration Constants
# --------------------
INITIAL_WIDTH, INITIAL_HEIGHT = 800, 600

# Colors used in both apps
BACKGROUND_COLOR = (30, 30, 30)
TEXT_COLOR = (230, 230, 230)
CURSOR_COLOR = (255, 255, 255)
GRID_COLOR = (255, 255, 255)

# Constants for Text Editor
LINE_NUMBER_BG_COLOR = (40, 40, 40)
LINE_NUMBER_TEXT_COLOR = (150, 150, 150)
FONT_SIZE = 24
DRAWING_COLOR = (255, 255, 255, 255)
ERASER_COLOR = (0, 0, 0, 0)
ERASER_RADIUS = 10
DRAWING_LINE_WIDTH = 2
LINE_NUMBER_WIDTH = 50
TEXT_X_OFFSET = 60  # Margin for text (accounts for line numbers)

# Constants for Spreadsheet
NUM_ROWS, NUM_COLS = 20, 10
CELL_WIDTH = 100
CELL_HEIGHT = 30
HEADER_WIDTH = 50     # For row numbers
HEADER_HEIGHT = 30    # For column headers
SPREADSHEET_FONT_SIZE = 20  # You can change as needed

# Constants for Footer Bar
FOOTER_HEIGHT = 40
FOOTER_BG_COLOR = (50, 50, 50)
FOOTER_ACTIVE_COLOR = (100, 100, 100)
FOOTER_INACTIVE_COLOR = (50, 50, 50)


# --------------------
# Text Editor Class
# --------------------
class TextEditor:
    """A simple text editor with drawing capability and improved undo/redo support."""
    def __init__(self, font: pygame.font.Font, width: int, height: int, file_path: Optional[str] = None) -> None:
        self.font = font
        self.width = width
        self.height = height
        self.file_path: Optional[str] = file_path

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
        self.horizontal_scroll_offset: int = 0  # in pixels
        self.selection_start: Optional[Tuple[int, int]] = None
        self.selection_end: Optional[Tuple[int, int]] = None
        # Undo/redo stacks storing (lines, current_line, cursor_pos, drawing_surface)
        self.undo_stack: List[Tuple[List[str], int, int, pygame.Surface]] = []
        self.redo_stack: List[Tuple[List[str], int, int, pygame.Surface]] = []
        self.cursor_visible: bool = True
        self.last_cursor_toggle_time: int = pygame.time.get_ticks()

        # Persistent drawing canvas (larger than the visible window)
        self.canvas_width = max(2000, width)
        self.canvas_height = max(2000, height)
        self.drawing_surface = pygame.Surface((self.canvas_width, self.canvas_height), pygame.SRCALPHA).convert_alpha()
        self.drawing_surface.fill((0, 0, 0, 0))
        self.drawing_scroll_offset: int = 0

        # Mouse drawing state
        self.left_button_down = False
        self.right_button_down = False
        self.last_pos: Optional[Tuple[int, int]] = None
        self.drawing_in_progress = False  # Track drawing stroke as a single action

    def ensure_canvas_size(self, x: int, y: int) -> None:
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
        """Resize the editor’s view (not the persistent drawing canvas)."""
        self.width = width
        self.height = height

    def add_to_undo_stack(self) -> None:
        drawing_copy = self.drawing_surface.copy()
        self.undo_stack.append((self.lines.copy(), self.current_line, self.cursor_pos, drawing_copy))
        self.redo_stack.clear()
        if len(self.undo_stack) > 100:
            self.undo_stack.pop(0)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == TEXTINPUT:
            self.insert_character(event.text)
        elif event.type == KEYDOWN:
            ctrl_cmd_pressed = event.mod & (KMOD_LCTRL | KMOD_RCTRL | KMOD_LMETA | KMOD_RMETA)
            shift_pressed = bool(event.mod & KMOD_SHIFT)
            if ctrl_cmd_pressed:
                self.handle_ctrl_shortcuts(event, shift_pressed)
            else:
                if event.key in {
                    K_BACKSPACE, K_DELETE, K_RETURN, K_HOME, K_END,
                    K_PAGEUP, K_PAGEDOWN, K_LEFT, K_RIGHT, K_UP, K_DOWN
                }:
                    self.add_to_undo_stack()
                self.handle_regular_input(event, shift_pressed)
        elif event.type == MOUSEWHEEL:
            self.handle_scroll(event)
        elif event.type == MOUSEBUTTONDOWN:
            # On macOS: Option-click jumps to position.
            if sys.platform == "darwin" and (pygame.key.get_mods() & KMOD_ALT):
                self.handle_option_click(event)
                return
            if event.button in (1, 3):  # left for drawing, right for erasing
                if not self.drawing_in_progress:
                    self.add_to_undo_stack()
                    self.drawing_in_progress = True
                if event.button == 1:
                    self.left_button_down = True
                elif event.button == 3:
                    self.right_button_down = True
                doc_x = event.pos[0] - TEXT_X_OFFSET + self.horizontal_scroll_offset
                doc_y = event.pos[1] + self.drawing_scroll_offset
                self.ensure_canvas_size(doc_x, doc_y)
                self.last_pos = (doc_x, doc_y)
        elif event.type == MOUSEBUTTONUP:
            if event.button == 1:
                self.left_button_down = False
            elif event.button == 3:
                self.right_button_down = False
            self.drawing_in_progress = False
            self.last_pos = None
        elif event.type == MOUSEMOTION:
            self.handle_mouse_motion(event)

    def handle_option_click(self, event: pygame.event.Event) -> None:
        font_height = self.font.get_height()
        target_line = self.scroll_offset + event.pos[1] // font_height
        target_line = max(0, min(target_line, len(self.lines) - 1))
        line_text = self.lines[target_line]
        effective_x = event.pos[0] - TEXT_X_OFFSET + self.horizontal_scroll_offset
        target_col = 0
        while target_col < len(line_text) and self.font.size(line_text[:target_col + 1])[0] <= effective_x:
            target_col += 1
        self.current_line = target_line
        self.cursor_pos = target_col
        self.selection_start = None
        self.selection_end = None
        self.update_scroll()

    def handle_mouse_motion(self, event: pygame.event.Event) -> None:
        if self.left_button_down or self.right_button_down:
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

    def handle_scroll(self, event: pygame.event.Event) -> None:
        font_height = self.font.get_height()
        max_scroll_offset = max(0, len(self.lines) - self.height // font_height + 1)
        self.scroll_offset = max(0, min(max_scroll_offset, self.scroll_offset - event.y))
        self.drawing_scroll_offset = self.scroll_offset * font_height
        self.update_scroll()

    def handle_ctrl_shortcuts(self, event: pygame.event.Event, shift_pressed: bool) -> None:
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

    def handle_regular_input(self, event: pygame.event.Event, shift_pressed: bool) -> None:
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
        if self.selection_start and self.selection_end:
            self.delete_selection()
        current_line_text = self.lines[self.current_line]
        self.lines.insert(self.current_line + 1, current_line_text[self.cursor_pos:])
        self.lines[self.current_line] = current_line_text[:self.cursor_pos]
        self.current_line += 1
        self.cursor_pos = 0
        self.update_scroll()

    def insert_character(self, char: str) -> None:
        if not char:
            return
        if self.selection_start and self.selection_end:
            self.delete_selection()
        line = self.lines[self.current_line]
        self.lines[self.current_line] = line[:self.cursor_pos] + char + line[self.cursor_pos:]
        self.cursor_pos += len(char)
        self.update_scroll()

    def update_scroll(self) -> None:
        font_height = self.font.get_height()
        visible_lines = self.height // font_height
        if self.current_line < self.scroll_offset:
            self.scroll_offset = self.current_line
        elif self.current_line >= self.scroll_offset + visible_lines:
            self.scroll_offset = self.current_line - visible_lines + 1

        cursor_x = self.font.size(self.lines[self.current_line][:self.cursor_pos])[0]
        if cursor_x < self.horizontal_scroll_offset:
            self.horizontal_scroll_offset = max(0, cursor_x - 50)
        elif cursor_x > self.horizontal_scroll_offset + self.width - 100:
            self.horizontal_scroll_offset = cursor_x - self.width + 100

        self.drawing_scroll_offset = self.scroll_offset * font_height

    def copy_text(self) -> None:
        if self.selection_start and self.selection_end:
            start, end = self.get_selection_range()
            text = self.get_selected_text(start, end)
            pyperclip.copy(text)

    def cut_text(self) -> None:
        if self.selection_start and self.selection_end:
            self.copy_text()
            self.delete_selection()

    def paste_text(self) -> None:
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
        assert self.selection_start is not None and self.selection_end is not None
        start, end = self.selection_start, self.selection_end
        if start > end:
            start, end = end, start
        return start, end

    def get_selected_text(self, start: Tuple[int, int], end: Tuple[int, int]) -> str:
        if start[0] == end[0]:
            return self.lines[start[0]][start[1]:end[1]]
        selected_text = [self.lines[start[0]][start[1]:]]
        selected_text.extend(self.lines[start[0] + 1:end[0]])
        selected_text.append(self.lines[end[0]][:end[1]])
        return "\n".join(selected_text)

    def undo(self) -> None:
        if self.undo_stack:
            self.redo_stack.append((self.lines.copy(), self.current_line, self.cursor_pos, self.drawing_surface.copy()))
            self.lines, self.current_line, self.cursor_pos, self.drawing_surface = self.undo_stack.pop()
            self.update_scroll()

    def redo(self) -> None:
        if self.redo_stack:
            self.undo_stack.append((self.lines.copy(), self.current_line, self.cursor_pos, self.drawing_surface.copy()))
            self.lines, self.current_line, self.cursor_pos, self.drawing_surface = self.redo_stack.pop()
            self.update_scroll()

    def save_file(self) -> None:
        if not self.file_path:
            self.file_path = "untitled.txt"
        try:
            with open(self.file_path, 'w') as f:
                f.write("\n".join(self.lines))
            print(f"File saved to {self.file_path}")
        except Exception as e:
            print(f"Error saving file {self.file_path}: {e}")

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(BACKGROUND_COLOR)
        self.draw_line_numbers(surface)
        self.draw_text(surface)
        self.draw_selection(surface)
        self.draw_cursor(surface)
        # Blit the drawing layer (shifted from document to screen coordinates)
        surface.blit(self.drawing_surface, (TEXT_X_OFFSET - self.horizontal_scroll_offset, -self.drawing_scroll_offset))

    def draw_line_numbers(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, LINE_NUMBER_BG_COLOR, (0, 0, LINE_NUMBER_WIDTH, self.height))
        font_height = self.font.get_height()
        for i, line_num in enumerate(range(self.scroll_offset + 1, self.scroll_offset + self.height // font_height + 1)):
            text_surface = self.font.render(str(line_num), True, LINE_NUMBER_TEXT_COLOR)
            surface.blit(text_surface, (5, i * font_height))

    def draw_text(self, surface: pygame.Surface) -> None:
        font_height = self.font.get_height()
        for i, line in enumerate(self.lines[self.scroll_offset:]):
            if i * font_height > self.height:
                break
            text_surface = self.font.render(line, True, TEXT_COLOR)
            surface.blit(text_surface, (TEXT_X_OFFSET - self.horizontal_scroll_offset, i * font_height))

    def draw_cursor(self, surface: pygame.Surface) -> None:
        if self.cursor_visible:
            cursor_x = TEXT_X_OFFSET + self.font.size(self.lines[self.current_line][:self.cursor_pos])[0] - self.horizontal_scroll_offset
            cursor_y = (self.current_line - self.scroll_offset) * self.font.get_height()
            pygame.draw.line(surface, CURSOR_COLOR, (cursor_x, cursor_y),
                             (cursor_x, cursor_y + self.font.get_height()), 2)

    def draw_selection(self, surface: pygame.Surface) -> None:
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
                pygame.draw.rect(surface, (50, 50, 150), (start_x, y, end_x - start_x, font_height))

    def toggle_cursor(self) -> None:
        current_time = pygame.time.get_ticks()
        if current_time - self.last_cursor_toggle_time > 500:
            self.cursor_visible = not self.cursor_visible
            self.last_cursor_toggle_time = current_time


# --------------------
# Spreadsheet Class
# --------------------
class Spreadsheet:
    def __init__(self, font: pygame.font.Font, rows=NUM_ROWS, cols=NUM_COLS):
        self.font = font
        self.rows = rows
        self.cols = cols
        self.cells = [['' for _ in range(cols)] for _ in range(rows)]
        self.selected_row = 0
        self.selected_col = 0
        self.editing = False
        self.edit_buffer = ""
        self.edit_cursor_pos = 0
        self.edit_sel_start = None
        self.edit_sel_end = None
        self.edit_undo_stack = []
        self.edit_redo_stack = []
        self.cursor_visible = True
        self.last_cursor_toggle_time = pygame.time.get_ticks()

    # --- Editing Helpers ---
    def start_edit(self, clear=False):
        self.editing = True
        if clear:
            self.edit_buffer = ""
        else:
            self.edit_buffer = self.cells[self.selected_row][self.selected_col]
        self.edit_cursor_pos = len(self.edit_buffer)
        self.edit_sel_start = None
        self.edit_sel_end = None
        self.edit_undo_stack = []
        self.edit_redo_stack = []
        self.push_edit_undo()

    def commit_edit(self):
        if self.editing:
            self.cells[self.selected_row][self.selected_col] = self.edit_buffer
        self.editing = False

    def push_edit_undo(self):
        state = (self.edit_buffer, self.edit_cursor_pos, self.edit_sel_start, self.edit_sel_end)
        self.edit_undo_stack.append(state)
        self.edit_redo_stack.clear()

    def undo_edit(self):
        if len(self.edit_undo_stack) > 1:
            current_state = (self.edit_buffer, self.edit_cursor_pos, self.edit_sel_start, self.edit_sel_end)
            self.edit_redo_stack.append(current_state)
            self.edit_undo_stack.pop()
            prev_state = self.edit_undo_stack[-1]
            self.edit_buffer, self.edit_cursor_pos, self.edit_sel_start, self.edit_sel_end = prev_state

    def redo_edit(self):
        if self.edit_redo_stack:
            state = self.edit_redo_stack.pop()
            self.push_edit_undo()
            self.edit_buffer, self.edit_cursor_pos, self.edit_sel_start, self.edit_sel_end = state

    def _delete_selection_if_any(self):
        if (self.edit_sel_start is not None and self.edit_sel_end is not None and
                self.edit_sel_start != self.edit_sel_end):
            start = min(self.edit_sel_start, self.edit_sel_end)
            end = max(self.edit_sel_start, self.edit_sel_end)
            self.edit_buffer = self.edit_buffer[:start] + self.edit_buffer[end:]
            self.edit_cursor_pos = start
            self.edit_sel_start = None
            self.edit_sel_end = None

    # --- Event Handling ---
    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # left-click
                x, y = event.pos
                if x >= HEADER_WIDTH and y >= HEADER_HEIGHT:
                    self.commit_edit()
                    col = (x - HEADER_WIDTH) // CELL_WIDTH
                    row = (y - HEADER_HEIGHT) // CELL_HEIGHT
                    if row < self.rows and col < self.cols:
                        self.selected_row = row
                        self.selected_col = col
                        self.editing = False
        elif event.type == KEYDOWN:
            mod = event.mod
            ctrl_pressed = mod & pygame.KMOD_CTRL
            shift_pressed = mod & pygame.KMOD_SHIFT
            if self.editing:
                if ctrl_pressed:
                    if event.key == pygame.K_z:
                        self.undo_edit()
                    elif event.key == pygame.K_y:
                        self.redo_edit()
                    elif event.key == pygame.K_c:
                        if (self.edit_sel_start is not None and self.edit_sel_end is not None and
                                self.edit_sel_start != self.edit_sel_end):
                            start = min(self.edit_sel_start, self.edit_sel_end)
                            end = max(self.edit_sel_start, self.edit_sel_end)
                            pyperclip.copy(self.edit_buffer[start:end])
                    elif event.key == pygame.K_v:
                        paste_text = pyperclip.paste()
                        self.push_edit_undo()
                        self._delete_selection_if_any()
                        self.edit_buffer = (self.edit_buffer[:self.edit_cursor_pos] +
                                            paste_text +
                                            self.edit_buffer[self.edit_cursor_pos:])
                        self.edit_cursor_pos += len(paste_text)
                        self.edit_sel_start = None
                        self.edit_sel_end = None
                    elif event.key == pygame.K_x:
                        if (self.edit_sel_start is not None and self.edit_sel_end is not None and
                                self.edit_sel_start != self.edit_sel_end):
                            start = min(self.edit_sel_start, self.edit_sel_end)
                            end = max(self.edit_sel_start, self.edit_sel_end)
                            pyperclip.copy(self.edit_buffer[start:end])
                            self.push_edit_undo()
                            self._delete_selection_if_any()
                else:
                    if event.key == pygame.K_RETURN:
                        self.commit_edit()
                    elif event.key == pygame.K_ESCAPE:
                        self.editing = False
                    elif event.key == pygame.K_BACKSPACE:
                        self.push_edit_undo()
                        if (self.edit_sel_start is not None and self.edit_sel_end is not None and
                                self.edit_sel_start != self.edit_sel_end):
                            self._delete_selection_if_any()
                        elif self.edit_cursor_pos > 0:
                            self.edit_buffer = (self.edit_buffer[:self.edit_cursor_pos - 1] +
                                                self.edit_buffer[self.edit_cursor_pos:])
                            self.edit_cursor_pos -= 1
                            self.edit_sel_start = None
                            self.edit_sel_end = None
                    elif event.key == pygame.K_DELETE:
                        self.push_edit_undo()
                        if (self.edit_sel_start is not None and self.edit_sel_end is not None and
                                self.edit_sel_start != self.edit_sel_end):
                            self._delete_selection_if_any()
                        elif self.edit_cursor_pos < len(self.edit_buffer):
                            self.edit_buffer = (self.edit_buffer[:self.edit_cursor_pos] +
                                                self.edit_buffer[self.edit_cursor_pos + 1:])
                            self.edit_sel_start = None
                            self.edit_sel_end = None
                    elif event.key == pygame.K_LEFT:
                        if shift_pressed:
                            if self.edit_sel_start is None:
                                self.edit_sel_start = self.edit_cursor_pos
                            if self.edit_cursor_pos > 0:
                                self.edit_cursor_pos -= 1
                            self.edit_sel_end = self.edit_cursor_pos
                        else:
                            if self.edit_cursor_pos > 0:
                                self.edit_cursor_pos -= 1
                            self.edit_sel_start = None
                            self.edit_sel_end = None
                    elif event.key == pygame.K_RIGHT:
                        if shift_pressed:
                            if self.edit_sel_start is None:
                                self.edit_sel_start = self.edit_cursor_pos
                            if self.edit_cursor_pos < len(self.edit_buffer):
                                self.edit_cursor_pos += 1
                            self.edit_sel_end = self.edit_cursor_pos
                        else:
                            if self.edit_cursor_pos < len(self.edit_buffer):
                                self.edit_cursor_pos += 1
                            self.edit_sel_start = None
                            self.edit_sel_end = None
            else:
                # Navigation mode when not editing.
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.commit_edit()
                    if self.selected_row < self.rows - 1:
                        self.selected_row += 1
                elif event.key == pygame.K_LEFT:
                    self.commit_edit()
                    if self.selected_col > 0:
                        self.selected_col -= 1
                elif event.key == pygame.K_RIGHT:
                    self.commit_edit()
                    if self.selected_col < self.cols - 1:
                        self.selected_col += 1
                elif event.key == pygame.K_UP:
                    self.commit_edit()
                    if self.selected_row > 0:
                        self.selected_row -= 1
                elif event.key == pygame.K_DOWN:
                    self.commit_edit()
                    if self.selected_row < self.rows - 1:
                        self.selected_row += 1
                elif event.key == pygame.K_BACKSPACE:
                    self.start_edit(clear=True)
                elif event.key == pygame.K_DELETE:
                    self.start_edit(clear=True)
        elif event.type == TEXTINPUT:
            if not self.editing:
                self.start_edit(clear=True)
            self.push_edit_undo()
            self._delete_selection_if_any()
            self.edit_buffer = (self.edit_buffer[:self.edit_cursor_pos] +
                                event.text +
                                self.edit_buffer[self.edit_cursor_pos:])
            self.edit_cursor_pos += len(event.text)
            self.edit_sel_start = None
            self.edit_sel_end = None

    def update_cursor(self):
        if self.editing:
            current_time = pygame.time.get_ticks()
            if current_time - self.last_cursor_toggle_time > 500:
                self.cursor_visible = not self.cursor_visible
                self.last_cursor_toggle_time = current_time
        else:
            self.cursor_visible = False

    # --- Formula Evaluation ---
    def get_cell_numeric_value(self, row: int, col: int) -> float:
        try:
            cell_text = self.cells[row][col]
            if cell_text.startswith("=") and not (self.selected_row == row and self.selected_col == col and self.editing):
                value = self.evaluate_formula(cell_text)
            else:
                value = cell_text
            return float(value) if value != "" else 0.0
        except Exception:
            return 0.0

    def evaluate_formula(self, formula: str) -> str:
        expr = formula[1:]
        try:
            if expr.upper().startswith("SUM(") and expr.endswith(")"):
                inner = expr[4:-1]
                args = inner.split(',')
                total = 0.0
                for arg in args:
                    arg = arg.strip()
                    if ":" in arg:
                        start_ref, end_ref = arg.split(":")
                        start_ref = start_ref.strip().upper()
                        end_ref = end_ref.strip().upper()
                        start_col = ord(start_ref[0]) - 65
                        start_row = int(start_ref[1:]) - 1
                        end_col = ord(end_ref[0]) - 65
                        end_row = int(end_ref[1:]) - 1
                        for r in range(start_row, end_row + 1):
                            for c in range(start_col, end_col + 1):
                                total += self.get_cell_numeric_value(r, c)
                    else:
                        if arg and arg[0].isalpha():
                            col = ord(arg[0].upper()) - 65
                            row = int(arg[1:]) - 1
                            total += self.get_cell_numeric_value(row, col)
                        else:
                            total += float(arg)
                return str(total)
            else:
                def replace_ref(match):
                    ref = match.group(0)
                    col = ord(ref[0].upper()) - 65
                    row = int(ref[1:]) - 1
                    return str(self.get_cell_numeric_value(row, col))
                expr = re.sub(r'\b[A-J][0-9]+\b', replace_ref, expr)
                result = eval(expr, {"__builtins__": None}, {})
                return str(result)
        except Exception:
            return "#ERR"

    def get_display_value(self, row: int, col: int) -> str:
        if row == self.selected_row and col == self.selected_col and self.editing:
            return self.edit_buffer
        cell_text = self.cells[row][col]
        if cell_text.startswith("=") and not (row == self.selected_row and col == self.selected_col and self.editing):
            return self.evaluate_formula(cell_text)
        return cell_text

    # --- Drawing ---
    def draw(self, surface: pygame.Surface):
        surface.fill(BACKGROUND_COLOR)
        # Draw Column Headers
        for col in range(self.cols):
            x = HEADER_WIDTH + col * CELL_WIDTH
            rect = pygame.Rect(x, 0, CELL_WIDTH, HEADER_HEIGHT)
            pygame.draw.rect(surface, BACKGROUND_COLOR, rect)
            pygame.draw.rect(surface, GRID_COLOR, rect, 1)
            label_text = chr(65 + col)
            label = self.font.render(label_text, True, TEXT_COLOR)
            label_rect = label.get_rect(center=rect.center)
            surface.blit(label, label_rect)
        # Draw Row Headers
        for row in range(self.rows):
            y = HEADER_HEIGHT + row * CELL_HEIGHT
            rect = pygame.Rect(0, y, HEADER_WIDTH, CELL_HEIGHT)
            pygame.draw.rect(surface, BACKGROUND_COLOR, rect)
            pygame.draw.rect(surface, GRID_COLOR, rect, 1)
            label = self.font.render(str(row + 1), True, TEXT_COLOR)
            label_rect = label.get_rect(center=rect.center)
            surface.blit(label, label_rect)
        # Draw Cells
        for row in range(self.rows):
            for col in range(self.cols):
                x = HEADER_WIDTH + col * CELL_WIDTH
                y = HEADER_HEIGHT + row * CELL_HEIGHT
                rect = pygame.Rect(x, y, CELL_WIDTH, CELL_HEIGHT)
                pygame.draw.rect(surface, BACKGROUND_COLOR, rect)
                pygame.draw.rect(surface, GRID_COLOR, rect, 1)
                display_text = self.get_display_value(row, col)
                text_surface = self.font.render(display_text, True, TEXT_COLOR)
                surface.blit(text_surface, (x + 5, y + 5))
        # Highlight Selected Cell
        sel_x = HEADER_WIDTH + self.selected_col * CELL_WIDTH
        sel_y = HEADER_HEIGHT + self.selected_row * CELL_HEIGHT
        sel_rect = pygame.Rect(sel_x, sel_y, CELL_WIDTH, CELL_HEIGHT)
        pygame.draw.rect(surface, GRID_COLOR, sel_rect, 3)
        # If editing, draw selection and blinking cursor.
        if self.editing and self.selected_row < self.rows and self.selected_col < self.cols:
            cell_x = sel_x + 5
            cell_y = sel_y + 5
            if (self.edit_sel_start is not None and self.edit_sel_end is not None and
                    self.edit_sel_start != self.edit_sel_end):
                start = min(self.edit_sel_start, self.edit_sel_end)
                end = max(self.edit_sel_start, self.edit_sel_end)
                text_before_sel = self.edit_buffer[:start]
                text_sel = self.edit_buffer[start:end]
                sel_start_x = cell_x + self.font.size(text_before_sel)[0]
                sel_width = self.font.size(text_sel)[0]
                selection_rect = pygame.Rect(sel_start_x, cell_y, sel_width, self.font.get_height())
                pygame.draw.rect(surface, (100, 100, 255), selection_rect)
            text_before_cursor = self.edit_buffer[:self.edit_cursor_pos]
            cursor_x = cell_x + self.font.size(text_before_cursor)[0]
            if self.cursor_visible:
                cursor_rect = pygame.Rect(cursor_x, cell_y, 2, self.font.get_height())
                pygame.draw.rect(surface, CURSOR_COLOR, cursor_rect)

    # Note: Do not duplicate get_cell_numeric_value; the one above is used.


# --------------------
# Main Application Loop
# --------------------
def main() -> None:
    pygame.init()
    pygame.key.set_repeat(300, 50)
    screen = pygame.display.set_mode((INITIAL_WIDTH, INITIAL_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("Merged App: Code Wizard & Spreadsheet")
    font = pygame.font.SysFont("monospace", FONT_SIZE)
    ss_font = pygame.font.SysFont("monospace", SPREADSHEET_FONT_SIZE)

    current_width, current_height = INITIAL_WIDTH, INITIAL_HEIGHT
    # Reserve space for the footer bar.
    main_area_height = current_height - FOOTER_HEIGHT

    # If a file is provided as a command-line argument, load it in the text editor.
    file_path = sys.argv[1] if len(sys.argv) > 1 else None
    if file_path:
        print(f"Loading file: {file_path}")

    editor = TextEditor(font, current_width, main_area_height, file_path)
    spreadsheet = Spreadsheet(ss_font)

    # Start in text editor mode.
    current_mode = "text"

    clock = pygame.time.Clock()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            elif event.type == VIDEORESIZE:
                current_width, current_height = event.w, event.h
                screen = pygame.display.set_mode((current_width, current_height), pygame.RESIZABLE)
                main_area_height = current_height - FOOTER_HEIGHT
                editor.resize(current_width, main_area_height)
            elif event.type in (MOUSEBUTTONDOWN, MOUSEBUTTONUP, MOUSEMOTION):
                # Check if event is in the footer area.
                if event.pos[1] >= current_height - FOOTER_HEIGHT:
                    if event.type == MOUSEBUTTONDOWN:
                        if event.pos[0] < current_width // 2:
                            current_mode = "text"
                        else:
                            current_mode = "spreadsheet"
                    continue  # Do not pass footer events to the active app.
                else:
                    if current_mode == "text":
                        editor.handle_event(event)
                    elif current_mode == "spreadsheet":
                        spreadsheet.handle_event(event)
            else:
                if current_mode == "text":
                    editor.handle_event(event)
                elif current_mode == "spreadsheet":
                    spreadsheet.handle_event(event)

        if current_mode == "text":
            editor.toggle_cursor()
        elif current_mode == "spreadsheet":
            spreadsheet.update_cursor()

        # Draw the main area.
        main_area_rect = pygame.Rect(0, 0, current_width, main_area_height)
        main_area_surface = screen.subsurface(main_area_rect)
        if current_mode == "text":
            editor.draw(main_area_surface)
        elif current_mode == "spreadsheet":
            spreadsheet.draw(main_area_surface)

        # Draw the footer bar.
        footer_rect = pygame.Rect(0, current_height - FOOTER_HEIGHT, current_width, FOOTER_HEIGHT)
        pygame.draw.rect(screen, FOOTER_BG_COLOR, footer_rect)
        button_width = current_width // 2

        # Prepare button texts.
        text_btn = font.render("Text", True, TEXT_COLOR)
        spread_btn = font.render("Spreadsheet", True, TEXT_COLOR)

        # Left button (Text)
        text_button_rect = pygame.Rect(0, current_height - FOOTER_HEIGHT, button_width, FOOTER_HEIGHT)
        btn_color = FOOTER_ACTIVE_COLOR if current_mode == "text" else FOOTER_INACTIVE_COLOR
        pygame.draw.rect(screen, btn_color, text_button_rect)
        pygame.draw.rect(screen, GRID_COLOR, text_button_rect, 1)
        text_btn_rect = text_btn.get_rect(center=text_button_rect.center)
        screen.blit(text_btn, text_btn_rect)

        # Right button (Spreadsheet)
        spread_button_rect = pygame.Rect(button_width, current_height - FOOTER_HEIGHT, button_width, FOOTER_HEIGHT)
        btn_color = FOOTER_ACTIVE_COLOR if current_mode == "spreadsheet" else FOOTER_INACTIVE_COLOR
        pygame.draw.rect(screen, btn_color, spread_button_rect)
        pygame.draw.rect(screen, GRID_COLOR, spread_button_rect, 1)
        spread_btn_rect = spread_btn.get_rect(center=spread_button_rect.center)
        screen.blit(spread_btn, spread_btn_rect)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
