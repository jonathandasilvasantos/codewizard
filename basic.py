import sys
import re
import pygame
import pyperclip
import subprocess
from typing import List, Optional, Tuple
from pygame.locals import (
    K_BACKSPACE, K_DELETE, K_RETURN, K_LEFT, K_RIGHT, K_UP, K_DOWN,
    K_HOME, K_END, K_PAGEUP, K_PAGEDOWN,
    K_c, K_v, K_x, K_z, K_s, K_ESCAPE,
    KMOD_LCTRL, KMOD_RCTRL, KMOD_LMETA, KMOD_RMETA, KMOD_SHIFT, KMOD_ALT,
    KEYDOWN, QUIT, MOUSEBUTTONDOWN, MOUSEBUTTONUP, MOUSEMOTION, MOUSEWHEEL, TEXTINPUT,
    VIDEORESIZE
)

# --------------------
# Configuration Constants
# --------------------
INITIAL_WIDTH, INITIAL_HEIGHT = 800, 600

# Colors used in all modes
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

# Constants for Footer Bar
FOOTER_HEIGHT = 40
FOOTER_BG_COLOR = (50, 50, 50)
FOOTER_ACTIVE_COLOR = (100, 100, 100)
FOOTER_INACTIVE_COLOR = (50, 50, 50)


# --------------------
# Text Editor Class
# --------------------
class TextEditor:
    """A simple text editor that supports code editing and drawing.
    (The drawing parts remain unchanged.)"""
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
            # Provide sample BASIC code (a Pong–game) if no file is provided.
            self.lines = [
                'SCREEN 13 \' Set 320x200 resolution with 256 colors',
                'CLS',
                '',
                '\' Constants for game',
                'CONST PADDLE_HEIGHT = 40',
                'CONST PADDLE_WIDTH = 10',
                'CONST BALL_SIZE = 4',
                'CONST SCREEN_WIDTH = 320',
                'CONST SCREEN_HEIGHT = 200',
                'CONST PADDLE_SPEED = 5',
                'CONST BALL_SPEED = 3',
                '',
                '\' Initial positions',
                'leftPaddleY = (SCREEN_HEIGHT - PADDLE_HEIGHT) / 2',
                'rightPaddleY = (SCREEN_HEIGHT - PADDLE_HEIGHT) / 2',
                'ballX = SCREEN_WIDTH / 2',
                'ballY = SCREEN_HEIGHT / 2',
                'ballDX = BALL_SPEED',
                'ballDY = BALL_SPEED',
                '',
                '\' Score variables',
                'leftScore = 0',
                'rightScore = 0',
                '',
                '\' Main game loop',
                'DO',
                '    CLS',
                '    ',
                '    \' Draw scores',
                '    LOCATE 1, 10',
                '    PRINT leftScore',
                '    LOCATE 1, 30',
                '    PRINT rightScore',
                '    ',
                '    \' Draw paddles',
                '    LINE (0, leftPaddleY)-(PADDLE_WIDTH, leftPaddleY + PADDLE_HEIGHT), 15, BF',
                '    LINE (SCREEN_WIDTH - PADDLE_WIDTH, rightPaddleY)-(SCREEN_WIDTH, rightPaddleY + PADDLE_HEIGHT), 15, BF',
                '    ',
                '    \' Draw ball',
                '    CIRCLE (ballX, ballY), BALL_SIZE, 15',
                '    PAINT (ballX, ballY), 15',
                '    ',
                '    \' Move left paddle (W and S keys)',
                '    k$ = INKEY$',
                '    IF k$ = "w" OR k$ = "W" THEN',
                '        leftPaddleY = leftPaddleY - PADDLE_SPEED',
                '        IF leftPaddleY < 0 THEN leftPaddleY = 0',
                '    END IF',
                '    IF k$ = "s" OR k$ = "S" THEN',
                '        leftPaddleY = leftPaddleY + PADDLE_SPEED',
                '        IF leftPaddleY > SCREEN_HEIGHT - PADDLE_HEIGHT THEN leftPaddleY = SCREEN_HEIGHT - PADDLE_HEIGHT',
                '    END IF',
                '    ',
                '    \' Move right paddle (Up and Down arrow keys)',
                '    IF k$ = CHR$(0) + "H" THEN',
                '        rightPaddleY = rightPaddleY - PADDLE_SPEED',
                '        IF rightPaddleY < 0 THEN rightPaddleY = 0',
                '    END IF',
                '    IF k$ = CHR$(0) + "P" THEN',
                '        rightPaddleY = rightPaddleY + PADDLE_SPEED',
                '        IF rightPaddleY > SCREEN_HEIGHT - PADDLE_HEIGHT THEN rightPaddleY = SCREEN_HEIGHT - PADDLE_HEIGHT',
                '    END IF',
                '    ',
                '    \' Move ball',
                '    ballX = ballX + ballDX',
                '    ballY = ballY + ballDY',
                '    ',
                '    \' Ball collision with top and bottom',
                '    IF ballY <= 0 OR ballY >= SCREEN_HEIGHT THEN',
                '        ballDY = -ballDY',
                '    END IF',
                '    ',
                '    \' Ball collision with paddles',
                '    IF ballX <= PADDLE_WIDTH AND ballY >= leftPaddleY AND ballY <= leftPaddleY + PADDLE_HEIGHT THEN',
                '        ballDX = -ballDX',
                '        ballDX = ballDX * 1.1',
                '    END IF',
                '    ',
                '    IF ballX >= SCREEN_WIDTH - PADDLE_WIDTH AND ballY >= rightPaddleY AND ballY <= rightPaddleY + PADDLE_HEIGHT THEN',
                '        ballDX = -ballDX',
                '        ballDX = ballDX * 1.1',
                '    END IF',
                '    ',
                '    \' Score points',
                '    IF ballX <= 0 THEN',
                '        rightScore = rightScore + 1',
                '        ballX = SCREEN_WIDTH / 2',
                '        ballY = SCREEN_HEIGHT / 2',
                '        ballDX = BALL_SPEED',
                '    END IF',
                '    ',
                '    IF ballX >= SCREEN_WIDTH THEN',
                '        leftScore = leftScore + 1',
                '        ballX = SCREEN_WIDTH / 2',
                '        ballY = SCREEN_HEIGHT / 2',
                '        ballDX = -BALL_SPEED',
                '    END IF',
                '    ',
                '    \' Game speed control',
                '    _DELAY 0.016',
                '    ',
                '    \' Check for quit',
                '    IF k$ = CHR$(27) THEN EXIT DO',
                'LOOP',
                '',
                'CLS',
                'PRINT "Game Over!"',
                'PRINT "Final Score:"',
                'PRINT "Left Player: "; leftScore',
                'PRINT "Right Player: "; rightScore',
                'END'
            ]
        self.current_line = 0
        self.cursor_pos = 0
        self.scroll_offset = 0
        self.horizontal_scroll_offset = 0  # in pixels
        self.selection_start: Optional[Tuple[int, int]] = None
        self.selection_end: Optional[Tuple[int, int]] = None
        self.undo_stack: List[Tuple[List[str], int, int, pygame.Surface]] = []
        self.redo_stack: List[Tuple[List[str], int, int, pygame.Surface]] = []
        self.cursor_visible: bool = True
        self.last_cursor_toggle_time: int = pygame.time.get_ticks()

        # Persistent drawing canvas (for the text editor’s drawing layer)
        self.canvas_width = max(2000, width)
        self.canvas_height = max(2000, height)
        self.drawing_surface = pygame.Surface((self.canvas_width, self.canvas_height), pygame.SRCALPHA).convert_alpha()
        self.drawing_surface.fill((0, 0, 0, 0))
        self.drawing_scroll_offset: int = 0

        self.left_button_down = False
        self.right_button_down = False
        self.last_pos: Optional[Tuple[int, int]] = None
        self.drawing_in_progress = False

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
        if self.selection_start is not None and self.selection_end is not None:
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
        if self.selection_start is not None and self.selection_end is not None:
            self.delete_selection()
        elif self.cursor_pos < len(self.lines[self.current_line]):
            line = self.lines[self.current_line]
            self.lines[self.current_line] = line[:self.cursor_pos] + line[self.cursor_pos + 1:]
        elif self.current_line < len(self.lines) - 1:
            self.lines[self.current_line] += self.lines[self.current_line + 1]
            del self.lines[self.current_line + 1]
        self.update_scroll()

    def handle_return(self) -> None:
        if self.selection_start is not None and self.selection_end is not None:
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
        if self.selection_start is not None and self.selection_end is not None:
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
        if self.selection_start is not None and self.selection_end is not None:
            start, end = self.get_selection_range()
            text = self.get_selected_text(start, end)
            pyperclip.copy(text)

    def cut_text(self) -> None:
        if self.selection_start is not None and self.selection_end is not None:
            self.copy_text()
            self.delete_selection()

    def paste_text(self) -> None:
        text = pyperclip.paste()
        if self.selection_start is not None and self.selection_end is not None:
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
        if self.selection_start is not None and self.selection_end is not None:
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
        if self.selection_start is not None and self.selection_end is not None:
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
# Console Class (Terminal Emulator)
# --------------------
class Console:
    def __init__(self, font: pygame.font.Font, width: int, height: int):
        self.font = font
        self.width = width
        self.height = height
        self.prompt = ">>> "
        self.input_buffer = ""
        self.cursor_pos = 0
        self.output_lines: List[str] = []
        self.command_history: List[str] = []
        self.history_index: Optional[int] = None
        self.cursor_visible = True
        self.last_cursor_toggle_time = pygame.time.get_ticks()

    def handle_event(self, event: pygame.event.Event):
        if event.type == TEXTINPUT:
            self.input_buffer = self.input_buffer[:self.cursor_pos] + event.text + self.input_buffer[self.cursor_pos:]
            self.cursor_pos += len(event.text)
        elif event.type == KEYDOWN:
            if event.key == K_BACKSPACE:
                if self.cursor_pos > 0:
                    self.input_buffer = self.input_buffer[:self.cursor_pos - 1] + self.input_buffer[self.cursor_pos:]
                    self.cursor_pos -= 1
            elif event.key == K_DELETE:
                if self.cursor_pos < len(self.input_buffer):
                    self.input_buffer = self.input_buffer[:self.cursor_pos] + self.input_buffer[self.cursor_pos + 1:]
            elif event.key == K_LEFT:
                if self.cursor_pos > 0:
                    self.cursor_pos -= 1
            elif event.key == K_RIGHT:
                if self.cursor_pos < len(self.input_buffer):
                    self.cursor_pos += 1
            elif event.key == K_HOME:
                self.cursor_pos = 0
            elif event.key == K_END:
                self.cursor_pos = len(self.input_buffer)
            elif event.key == K_UP:
                if self.command_history:
                    if self.history_index is None:
                        self.history_index = len(self.command_history) - 1
                    elif self.history_index > 0:
                        self.history_index -= 1
                    self.input_buffer = self.command_history[self.history_index]
                    self.cursor_pos = len(self.input_buffer)
            elif event.key == K_DOWN:
                if self.command_history and self.history_index is not None:
                    if self.history_index < len(self.command_history) - 1:
                        self.history_index += 1
                        self.input_buffer = self.command_history[self.history_index]
                    else:
                        self.history_index = None
                        self.input_buffer = ""
                    self.cursor_pos = len(self.input_buffer)
            elif event.key == K_RETURN:
                self.process_command()

    def process_command(self):
        command = self.input_buffer.strip()
        self.output_lines.append(self.prompt + self.input_buffer)
        if command:
            self.command_history.append(self.input_buffer)
        self.history_index = None
        if command.lower() in ["clear", "cls"]:
            self.output_lines.clear()
        else:
            try:
                result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=5)
                if result.stdout:
                    for line in result.stdout.splitlines():
                        self.output_lines.append(line)
                if result.stderr:
                    for line in result.stderr.splitlines():
                        self.output_lines.append(line)
                if not result.stdout and not result.stderr:
                    self.output_lines.append("")
            except Exception as e:
                self.output_lines.append("Error: " + str(e))
        self.input_buffer = ""
        self.cursor_pos = 0

    def update_cursor(self):
        current_time = pygame.time.get_ticks()
        if current_time - self.last_cursor_toggle_time > 500:
            self.cursor_visible = not self.cursor_visible
            self.last_cursor_toggle_time = current_time

    def draw(self, surface: pygame.Surface):
        surface.fill(BACKGROUND_COLOR)
        line_height = self.font.get_height()
        max_lines = self.height // line_height - 1
        lines_to_draw = self.output_lines[-max_lines:]
        y = 0
        for line in lines_to_draw:
            text_surface = self.font.render(line, True, TEXT_COLOR)
            surface.blit(text_surface, (0, y))
            y += line_height
        prompt_line = self.prompt + self.input_buffer
        prompt_y = self.height - line_height
        text_surface = self.font.render(prompt_line, True, TEXT_COLOR)
        surface.blit(text_surface, (0, prompt_y))
        if self.cursor_visible:
            cursor_x = self.font.size(self.prompt + self.input_buffer[:self.cursor_pos])[0]
            cursor_rect = pygame.Rect(cursor_x, prompt_y, 2, line_height)
            pygame.draw.rect(surface, CURSOR_COLOR, cursor_rect)


# --------------------
# BASIC Interpreter Class
# --------------------
def convert_basic_expr(expr: str) -> str:
    """
    Convert a BASIC expression (with OR, AND and single '=' for equality)
    into a valid Python expression.
    This version always removes the trailing '$' from variable names.
    """
    expr = expr.replace(" OR ", " or ")
    expr = expr.replace(" AND ", " and ")
    # Replace any '=' not part of a larger operator with '=='
    expr = re.sub(r'(?<![<>!])=(?![=<>])', '==', expr)
    # Remove trailing '$' from variable names (e.g. k$ becomes k, CHR$ becomes CHR, INKEY$ becomes INKEY)
    expr = re.sub(r'([A-Za-z]+)\$', r'\1', expr)
    return expr

class BasicInterpreter:
    """
    A very simple BASIC interpreter that supports a subset of QBasic commands.
    It interprets commands like SCREEN, CLS, CONST/assignment, LOCATE/PRINT, LINE, CIRCLE, PAINT,
    IF/THEN/END IF, DO/LOOP (with EXIT DO) and _DELAY.
    """
    def __init__(self, font: pygame.font.Font, width: int, height: int) -> None:
        self.font = font
        self.width = width
        self.height = height
        self.program_lines: List[str] = []
        self.pc: int = 0  # program counter (line index)
        self.variables: dict = {}
        self.loop_stack: List[int] = []
        self.exit_loop: bool = False
        self.running: bool = True
        # For text output commands (LOCATE/PRINT)
        self.text_cursor: Tuple[int, int] = (0, 1)  # (col, row); row 1 is top
        # The “graphics screen” (set via SCREEN) – default to None
        self.surface: Optional[pygame.Surface] = None
        self.screen_width: int = 320
        self.screen_height: int = 200
        # Last key pressed (for INKEY)
        self.last_key: str = ""
        # Set up a basic color mapping (for QBasic colors 0–15)
        self.colors = {
            0: (0, 0, 0),
            1: (0, 0, 170),
            2: (0, 170, 0),
            3: (0, 170, 170),
            4: (170, 0, 0),
            5: (170, 0, 170),
            6: (170, 85, 0),
            7: (170, 170, 170),
            8: (85, 85, 85),
            9: (85, 85, 255),
            10: (85, 255, 85),
            11: (85, 255, 255),
            12: (255, 85, 85),
            13: (255, 85, 255),
            14: (255, 255, 85),
            15: (255, 255, 255)
        }

    def reset(self, program_lines: List[str]) -> None:
        self.program_lines = program_lines
        self.pc = 0
        self.variables = {}
        self.loop_stack = []
        self.exit_loop = False
        self.running = True
        self.text_cursor = (0, 1)
        # Default screen: if no SCREEN command is executed, create a default surface.
        if self.surface is None:
            self.surface = pygame.Surface((self.screen_width, self.screen_height))
            self.surface.fill((0, 0, 0))

    def basic_color(self, c: int) -> Tuple[int, int, int]:
        return self.colors.get(c, (255, 255, 255))

    def inkey(self):
        # Return the last key pressed (if any) then clear it.
        k = self.last_key
        self.last_key = ""
        return k

    def eval_expr(self, expr: str):
        # Convert the BASIC expression into Python syntax.
        conv_expr = convert_basic_expr(expr)
        env = dict(self.variables)
        # Add built-in functions with valid names:
        env["CHR"] = lambda x: chr(int(x))
        env["INKEY"] = self.inkey
        # If the expression is exactly "INKEY", then return the key value.
        if conv_expr.strip() == "INKEY":
            return self.inkey()
        try:
            return eval(conv_expr, {}, env)
        except Exception as e:
            print(f"Error evaluating expression '{expr}': {e}")
            return 0

    def handle_event(self, event: pygame.event.Event) -> None:
        # In run mode, only key events are needed (for INKEY)
        if event.type == KEYDOWN:
            if event.key == K_UP:
                self.last_key = chr(0) + "H"
            elif event.key == K_DOWN:
                self.last_key = chr(0) + "P"
            elif event.key == K_ESCAPE:
                self.last_key = chr(27)
            else:
                self.last_key = event.unicode

    def step(self) -> None:
        """Execute commands until a _DELAY command is encountered or end-of-program."""
        while self.running and self.pc < len(self.program_lines):
            line = self.program_lines[self.pc].strip()
            self.pc += 1
            # Remove comments (anything after a single quote)
            if "'" in line:
                line = line.split("'", 1)[0].strip()
            if not line:
                continue
            delay_hit = self.execute_line(line)
            if delay_hit:
                break

    def execute_line(self, line: str) -> bool:
        up_line = line.upper()
        # --- IF ... THEN ---
        if up_line.startswith("IF"):
            if "THEN" in up_line:
                parts = line.split("THEN", 1)
                condition_part = parts[0][2:].strip()
                then_part = parts[1].strip()
                cond = self.eval_expr(condition_part)
                if cond:
                    if then_part.upper() == "EXIT DO":
                        self.exit_loop = True
                    elif then_part:
                        self.execute_line(then_part)
                else:
                    if not then_part:
                        while self.pc < len(self.program_lines):
                            next_line = self.program_lines[self.pc].strip().upper()
                            self.pc += 1
                            if next_line == "END IF":
                                break
            return False

        if up_line == "END IF":
            return False

        # --- DO loop ---
        if up_line == "DO":
            self.loop_stack.append(self.pc)
            return False
        if up_line == "LOOP":
            if self.exit_loop:
                if self.loop_stack:
                    self.pc = self.loop_stack.pop()
                self.exit_loop = False
            else:
                if self.loop_stack:
                    self.pc = self.loop_stack[-1]
            return False

        # --- SCREEN ---
        if up_line.startswith("SCREEN"):
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "13":
                self.screen_width = 320
                self.screen_height = 200
                self.surface = pygame.Surface((self.screen_width, self.screen_height))
                self.surface.fill((0, 0, 0))
            return False

        # --- CLS ---
        if up_line == "CLS":
            if self.surface:
                self.surface.fill((0, 0, 0))
            return False

        # --- CONST ---
        if up_line.startswith("CONST"):
            content = line[5:].strip()
            if "=" in content:
                var, expr = content.split("=", 1)
                var_name = var.strip().replace("$", "")
                self.variables[var_name] = self.eval_expr(expr.strip())
            return False

        # --- Assignment (variable = expression) ---
        if "=" in line:
            var, expr = line.split("=", 1)
            var_name = var.strip().replace("$", "")
            self.variables[var_name] = self.eval_expr(expr.strip())
            return False

        # --- LOCATE ---
        if up_line.startswith("LOCATE"):
            params = line[6:].strip()
            if "," in params:
                parts = params.split(",")
                row = int(self.eval_expr(parts[0].strip()))
                col = int(self.eval_expr(parts[1].strip()))
                self.text_cursor = (col, row)
            return False

        # --- PRINT ---
        if up_line.startswith("PRINT"):
            content = line[5:].strip()
            parts = content.split(";")
            out_text = ""
            for part in parts:
                part = part.strip()
                if part:
                    out_text += str(self.eval_expr(part))
            if self.surface:
                txt_surf = self.font.render(out_text, True, (255, 255, 255))
                cell_w = self.font.size("A")[0]
                x = self.text_cursor[0] * cell_w
                y = (self.text_cursor[1]-1) * self.font.get_height()
                self.surface.blit(txt_surf, (x, y))
                self.text_cursor = (0, self.text_cursor[1] + 1)
            return False

        # --- LINE ---
        if up_line.startswith("LINE"):
            m = re.search(r"\(([^,]+),([^)]+)\)-\(([^,]+),([^)]+)\),([^,]+)(?:,\s*(BF))?", line, re.IGNORECASE)
            if m and self.surface:
                x1 = self.eval_expr(m.group(1).strip())
                y1 = self.eval_expr(m.group(2).strip())
                x2 = self.eval_expr(m.group(3).strip())
                y2 = self.eval_expr(m.group(4).strip())
                color = int(self.eval_expr(m.group(5).strip()))
                fill = m.group(6)
                rect = pygame.Rect(int(x1), int(y1), int(x2 - x1), int(y2 - y1))
                if fill and fill.upper() == "BF":
                    pygame.draw.rect(self.surface, self.basic_color(color), rect, 0)
                else:
                    pygame.draw.rect(self.surface, self.basic_color(color), rect, 1)
            return False

        # --- CIRCLE ---
        if up_line.startswith("CIRCLE"):
            m = re.search(r"\(([^,]+),([^)]+)\),([^,]+),(.+)", line)
            if m and self.surface:
                x = self.eval_expr(m.group(1).strip())
                y = self.eval_expr(m.group(2).strip())
                radius = self.eval_expr(m.group(3).strip())
                color = int(self.eval_expr(m.group(4).strip()))
                pygame.draw.circle(self.surface, self.basic_color(color), (int(x), int(y)), int(radius), 1)
            return False

        # --- PAINT ---
        if up_line.startswith("PAINT"):
            m = re.search(r"\(([^,]+),([^)]+)\),(.+)", line)
            if m and self.surface:
                x = self.eval_expr(m.group(1).strip())
                y = self.eval_expr(m.group(2).strip())
                color = int(self.eval_expr(m.group(3).strip()))
                pygame.draw.circle(self.surface, self.basic_color(color), (int(x), int(y)), 3, 0)
            return False

        # --- _DELAY ---
        if up_line.startswith("_DELAY"):
            expr = line[6:].strip()
            delay_val = float(self.eval_expr(expr))
            pygame.time.delay(int(delay_val * 1000))
            return True

        # --- END ---
        if up_line == "END":
            self.running = False
            return False

        return False

    def draw(self, target_surface: pygame.Surface) -> None:
        if self.surface:
            scaled = pygame.transform.scale(self.surface, (self.width, self.height))
            target_surface.blit(scaled, (0, 0))


# --------------------
# Main Application Loop
# --------------------
def main() -> None:
    pygame.init()
    pygame.key.set_repeat(300, 50)
    screen = pygame.display.set_mode((INITIAL_WIDTH, INITIAL_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("Merged App: Code Wizard, Run & Console")
    font = pygame.font.SysFont("monospace", FONT_SIZE)

    current_width, current_height = INITIAL_WIDTH, INITIAL_HEIGHT
    main_area_height = current_height - FOOTER_HEIGHT

    file_path = sys.argv[1] if len(sys.argv) > 1 else None
    if file_path:
        print(f"Loading file: {file_path}")

    editor = TextEditor(font, current_width, main_area_height, file_path)
    console = Console(font, current_width, main_area_height)
    interpreter = BasicInterpreter(font, current_width, main_area_height)

    current_mode = "text"  # Modes: "text", "run", "console"
    prev_mode = current_mode

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
                console.width = current_width
                console.height = main_area_height
                interpreter.width = current_width
                interpreter.height = main_area_height
            elif event.type in (MOUSEBUTTONDOWN, MOUSEBUTTONUP, MOUSEMOTION):
                if event.pos[1] >= current_height - FOOTER_HEIGHT:
                    if event.type == MOUSEBUTTONDOWN:
                        button_width = current_width // 3
                        if event.pos[0] < button_width:
                            current_mode = "text"
                        elif event.pos[0] < 2 * button_width:
                            current_mode = "run"
                        else:
                            current_mode = "console"
                    continue
                else:
                    if current_mode == "text":
                        editor.handle_event(event)
                    elif current_mode == "console":
                        console.handle_event(event)
            else:
                if current_mode == "text":
                    editor.handle_event(event)
                elif current_mode == "console":
                    console.handle_event(event)
                elif current_mode == "run":
                    interpreter.handle_event(event)

        if current_mode == "text":
            editor.toggle_cursor()
        elif current_mode == "console":
            console.update_cursor()

        if current_mode == "run" and prev_mode != "run":
            interpreter.reset(editor.lines)
            prev_mode = current_mode
        elif current_mode != "run":
            prev_mode = current_mode

        main_area_rect = pygame.Rect(0, 0, current_width, main_area_height)
        main_area_surface = screen.subsurface(main_area_rect)
        if current_mode == "text":
            editor.draw(main_area_surface)
        elif current_mode == "console":
            console.draw(main_area_surface)
        elif current_mode == "run":
            if interpreter.running:
                interpreter.step()
            interpreter.draw(main_area_surface)

        footer_rect = pygame.Rect(0, current_height - FOOTER_HEIGHT, current_width, FOOTER_HEIGHT)
        pygame.draw.rect(screen, FOOTER_BG_COLOR, footer_rect)
        button_width = current_width // 3

        text_btn = font.render("Text", True, TEXT_COLOR)
        run_btn = font.render("Run", True, TEXT_COLOR)
        console_btn = font.render("Console", True, TEXT_COLOR)

        text_button_rect = pygame.Rect(0, current_height - FOOTER_HEIGHT, button_width, FOOTER_HEIGHT)
        btn_color = FOOTER_ACTIVE_COLOR if current_mode == "text" else FOOTER_INACTIVE_COLOR
        pygame.draw.rect(screen, btn_color, text_button_rect)
        pygame.draw.rect(screen, GRID_COLOR, text_button_rect, 1)
        text_btn_rect = text_btn.get_rect(center=text_button_rect.center)
        screen.blit(text_btn, text_btn_rect)

        run_button_rect = pygame.Rect(button_width, current_height - FOOTER_HEIGHT, button_width, FOOTER_HEIGHT)
        btn_color = FOOTER_ACTIVE_COLOR if current_mode == "run" else FOOTER_INACTIVE_COLOR
        pygame.draw.rect(screen, btn_color, run_button_rect)
        pygame.draw.rect(screen, GRID_COLOR, run_button_rect, 1)
        run_btn_rect = run_btn.get_rect(center=run_button_rect.center)
        screen.blit(run_btn, run_btn_rect)

        console_button_rect = pygame.Rect(2 * button_width, current_height - FOOTER_HEIGHT, button_width, FOOTER_HEIGHT)
        btn_color = FOOTER_ACTIVE_COLOR if current_mode == "console" else FOOTER_INACTIVE_COLOR
        pygame.draw.rect(screen, btn_color, console_button_rect)
        pygame.draw.rect(screen, GRID_COLOR, console_button_rect, 1)
        console_btn_rect = console_btn.get_rect(center=console_button_rect.center)
        screen.blit(console_btn, console_btn_rect)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
