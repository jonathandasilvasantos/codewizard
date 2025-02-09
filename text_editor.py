import pygame
import pyperclip
from pygame.locals import *
from constants import *

class ClipboardManager:
    @staticmethod
    def copy_text(lines, selection_start, selection_end):
        if selection_start and selection_end:
            start_line, start_pos = selection_start
            end_line, end_pos = selection_end
            if start_line == end_line:
                pyperclip.copy(lines[start_line][start_pos:end_pos])
            else:
                copied_text = lines[start_line][start_pos:] + '\n'
                for line_num in range(start_line + 1, end_line):
                    copied_text += lines[line_num] + '\n'
                copied_text += lines[end_line][:end_pos]
                pyperclip.copy(copied_text)

    @staticmethod
    def paste_text(lines, cursor_pos, current_line):
        clipboard_content = pyperclip.paste().split('\n')
        for idx, content in enumerate(clipboard_content):
            if idx == 0:
                lines[current_line] = lines[current_line][:cursor_pos] + content + lines[current_line][cursor_pos:]
                cursor_pos += len(content)
            else:
                lines.insert(current_line + idx, content)
                current_line += 1
                cursor_pos = len(content)
        return lines, cursor_pos, current_line


class TextEditor:
    def __init__(self, font_path, font_size):
        self.font_path = font_path
        self.font_size = font_size
        self.font = pygame.font.Font(font_path, font_size)
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
        self.last_cursor_toggle_time = pygame.time.get_ticks()
        self.drawing = False
        self.draw_color = (255, 255, 255)
        self.drawings = []  # Store drawing coordinates

    def zoom_in(self):
        self.font_size += 2
        self.font = pygame.font.Font(self.font_path, self.font_size)
        self.update_scroll_offsets()

    def zoom_out(self):
        if self.font_size > 6:  # Minimum font size to avoid too small text
            self.font_size -= 2
            self.font = pygame.font.Font(self.font_path, self.font_size)
            self.update_scroll_offsets()

    def update_scroll_offsets(self):
        self.update_vertical_scroll()
        self.update_horizontal_scroll()

    def copy_text(self):
        ClipboardManager.copy_text(self.lines, self.selection_start, self.selection_end)

    def paste_text(self):
        self.push_undo()
        if self.selection_start and self.selection_end:
            self.delete_selection()
        self.lines, self.cursor_pos, self.current_line = ClipboardManager.paste_text(self.lines, self.cursor_pos, self.current_line)

    def cut_text(self):
        self.push_undo()
        self.copy_text()
        self.delete_selection()

    def delete_selection(self):
        if not self.selection_start or not self.selection_end:
            return

        start_line, start_pos = self.selection_start
        end_line, end_pos = self.selection_end

        if start_line > end_line or (start_line == end_line and start_pos > end_pos):
            start_line, start_pos, end_line, end_pos = end_line, end_pos, start_line, start_pos

        # Ensure start_pos and end_pos are within valid ranges
        start_pos = min(start_pos, len(self.lines[start_line]))
        end_pos = min(end_pos, len(self.lines[end_line]))

        if start_line == end_line:
            self.lines[start_line] = self.lines[start_line][:start_pos] + self.lines[start_line][end_pos:]
            self.cursor_pos = start_pos
        else:
            start_line_content = self.lines[start_line][:start_pos]
            end_line_content = self.lines[end_line][end_pos:]

            self.lines[start_line] = start_line_content + end_line_content
            del self.lines[start_line + 1:end_line + 1]

            self.cursor_pos = start_pos
            self.current_line = start_line

        self.selection_start = None
        self.selection_end = None

    def input(self, event):
        CMD_PRESSED = event.mod & (KMOD_LMETA | KMOD_RMETA) or event.mod & (KMOD_LCTRL | KMOD_RCTRL)
        SHIFT_PRESSED = event.mod & KMOD_SHIFT
        
        if CMD_PRESSED:
            if event.key == K_c:
                self.copy_text()
            elif event.key == K_v:
                self.paste_text()
            elif event.key == K_x:
                self.cut_text()
            elif event.key == K_PLUS or event.key == K_EQUALS:  # Command+ and Command= for zoom in
                self.zoom_in()
            elif event.key == K_MINUS:  # Command- for zoom out
                self.zoom_out()
            elif event.key == K_LEFT:
                self.horizontal_scroll(-1)
                self.jump_to_start_of_line()
            elif event.key == K_RIGHT:
                self.horizontal_scroll(1)
                self.jump_to_end_of_line()
            elif event.key == K_z:
                if SHIFT_PRESSED:
                    self.redo()
                else:
                    self.undo()
            return

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
            
        if SHIFT_PRESSED:
            if not self.selection_start:
                self.selection_start = (self.current_line, self.cursor_pos)
            self.selection_end = (self.current_line, self.cursor_pos)
        else:
            self.selection_start = None
            self.selection_end = None

    def horizontal_scroll(self, amount):
        max_offset = max(0, len(max(self.lines, key=len)) - LARGURA // 8)
        self.horizontal_scroll_offset = min(max(0, self.horizontal_scroll_offset + amount), max_offset)

    def handle_backspace(self):
        self.push_undo()
        if self.selection_start and self.selection_end:
            self.delete_selection()
        elif self.cursor_pos > 0:
            self.remove_char_at_cursor()
        elif self.current_line > 0:
            self.merge_with_previous_line()

    def handle_return(self):
        self.push_undo()
        self.split_line_at_cursor()
        self.update_vertical_scroll()
        self.update_horizontal_scroll()

    def handle_delete(self):
        self.push_undo()
        if self.selection_start and self.selection_end:
            self.delete_selection()
        elif self.cursor_pos < len(self.lines[self.current_line]):
            self.lines[self.current_line] = (self.lines[self.current_line][:self.cursor_pos] + 
                                             self.lines[self.current_line][self.cursor_pos + 1:])
        elif self.current_line < len(self.lines) - 1:
            self.lines[self.current_line] += self.lines[self.current_line + 1]
            del self.lines[self.current_line + 1]

    def handle_up(self):
        if self.current_line > 0:
            self.current_line -= 1
            self.cursor_pos = min(self.cursor_pos, len(self.lines[self.current_line]))
        self.update_vertical_scroll()

    def handle_down(self):
        if self.current_line < len(self.lines) - 1:
            self.current_line += 1
            self.cursor_pos = min(self.cursor_pos, len(self.lines[self.current_line]))
        self.update_vertical_scroll()
        self.update_horizontal_scroll()

    def handle_left(self):
        if self.cursor_pos > 0:
            self.cursor_pos -= 1
            self.update_horizontal_scroll()
        elif self.current_line > 0:
            self.jump_to_end_of_previous_line()

    def handle_right(self):
        if self.cursor_pos < len(self.lines[self.current_line]):
            self.cursor_pos += 1
            self.update_horizontal_scroll()
        elif self.current_line < len(self.lines) - 1:
            self.jump_to_start_of_next_line()

    def jump_to_end_of_previous_line(self):
        self.current_line -= 1
        self.cursor_pos = len(self.lines[self.current_line])
        self.update_vertical_scroll()
        self.update_horizontal_scroll()

    def jump_to_start_of_next_line(self):
        self.current_line += 1
        self.cursor_pos = 0
        self.update_vertical_scroll()
        self.update_horizontal_scroll()

    def update_vertical_scroll(self):
        visible_lines = ALTURA // self.font.get_height()
        if self.current_line < self.scroll_offset:
            self.scroll_offset = self.current_line
        elif self.current_line >= self.scroll_offset + visible_lines:
            self.scroll_offset = self.current_line - visible_lines + 1

    def update_horizontal_scroll(self):
        char_width = self.font.size(' ')[0]
        visible_chars = LARGURA // char_width
        cursor_x = self.font.size(self.lines[self.current_line][:self.cursor_pos])[0]

        if cursor_x - self.horizontal_scroll_offset > LARGURA - char_width * 10:
            self.horizontal_scroll_offset = min(cursor_x - LARGURA + char_width * 10, 
                                                max(0, len(self.lines[self.current_line]) * char_width - LARGURA))
        elif cursor_x < self.horizontal_scroll_offset + char_width * 10:
            self.horizontal_scroll_offset = max(0, cursor_x - char_width * 10)

    def handle_character_input(self, char):
        if char:
            self.push_undo()
            if self.selection_start and self.selection_end:
                self.delete_selection()
            self.insert_char_at_cursor(char)
            
            current_line_rendered_width = self.font.size(self.lines[self.current_line][:self.cursor_pos])[0]
            if current_line_rendered_width > LARGURA - 20:
                self.horizontal_scroll_offset += 1

    def handle_pageup(self):
        visible_lines = ALTURA // self.font.get_height()
        self.current_line = max(0, self.current_line - visible_lines)
        self.update_vertical_scroll()
        self.update_horizontal_scroll()

    def handle_pagedown(self):
        visible_lines = ALTURA // self.font.get_height()
        self.current_line = min(len(self.lines) - 1, self.current_line + visible_lines)
        self.update_vertical_scroll()
        self.update_horizontal_scroll()

    def jump_to_start_of_line(self):
        self.cursor_pos = 0
        self.horizontal_scroll_offset = 0

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

    def insert_char_at_cursor(self, char):
        self.lines[self.current_line] = self.lines[self.current_line][:self.cursor_pos] + char + self.lines[self.current_line][self.cursor_pos:]
        self.cursor_pos += 1

    def draw_line_number(self, surface, index, line_number):
        text_surface = self.font.render(str(line_number), True, LINE_NUMBER_TEXT_COLOR)
        surface.blit(text_surface, (10, index * 30))

    def draw(self, surface):
        surface.fill(FUNDODARK)
        pygame.draw.rect(surface, LINE_NUMBER_COLOR, (0, 0, LINE_NUMBER_WIDTH, ALTURA))

        for index, line in enumerate(self.lines[self.scroll_offset:]):
            if index * 30 > ALTURA:
                break
            line_number = index + self.scroll_offset + 1
            self.draw_line_number(surface, index, line_number)
            self.draw_line(surface, index, line)

        self.draw_drawings(surface)

    def draw_line(self, surface, index, line):
        line = line[self.horizontal_scroll_offset:]

        SELECTION_COLOR = SELECAOBRIGHT
        x_pos = 10 + self.font.size('XXX')[0]

        if self.selection_start and self.selection_end:
            start_line, start_pos = self.selection_start
            end_line, end_pos = self.selection_end

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
                
                before_text = self.font.render(line[:start_pos], True, TEXTOBRIGHT)
                surface.blit(before_text, (x_pos, index * 30))
                x_pos += self.font.size(line[:start_pos])[0]

                selected_text = self.font.render(line[start_pos:end_pos], True, BRANCO)
                surface.blit(selected_text, (x_pos, index * 30))
                x_pos += self.font.size(line[start_pos:end_pos])[0]

                after_text = self.font.render(line[end_pos:], True, TEXTOBRIGHT)
                surface.blit(after_text, (x_pos, index * 30))

                return

        rendered_text = self.font.render(line, True, TEXTOBRIGHT)
        surface.blit(rendered_text, (x_pos, index * 30))

        if index == self.current_line - self.scroll_offset:
            self.draw_cursor(surface, index)

    def draw_cursor(self, surface, index):
        current_time = pygame.time.get_ticks()
        if current_time - self.last_cursor_toggle_time > 500:
            self.cursor_visible = not self.cursor_visible
            self.last_cursor_toggle_time = current_time
        
        if not self.cursor_visible:
            return
        
        three_char_width = self.font.size('XXX')[0]
        cursor_offset = self.font.size(self.lines[self.current_line][:self.cursor_pos - self.horizontal_scroll_offset])[0]
        
        pygame.draw.line(surface, TEXTOBRIGHT, 
                        (10 + three_char_width + cursor_offset, index * 30), 
                        (10 + three_char_width + cursor_offset, index * 30 + 24), 
                        2)

    def push_undo(self):
        self.undo_stack.append(self.lines.copy())
        self.redo_stack.clear()

    def undo(self):
        if self.undo_stack:
            self.redo_stack.append(self.lines.copy())
            self.lines = self.undo_stack.pop()

    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(self.lines.copy())
            self.lines = self.redo_stack.pop()

    def load_file(self, filename):
        try:
            with open(filename, 'r') as f:
                self.lines = f.readlines()
            self.lines = [line.rstrip() for line in self.lines]
        except Exception as e:
            print(f"Error loading file: {e}")

    def handle_mouse_event(self, event):
        if event.type == MOUSEBUTTONDOWN:
            if event.button == 1:  # Left mouse button
                self.drawing = True
                self.add_drawing_point(event.pos)
        elif event.type == MOUSEBUTTONUP:
            if event.button == 1:  # Left mouse button
                self.drawing = False
        elif event.type == MOUSEMOTION:
            if self.drawing:
                self.add_drawing_point(event.pos)

    def add_drawing_point(self, pos):
        self.drawings.append((pos[0] + self.horizontal_scroll_offset, pos[1] + self.scroll_offset * 30))

    def draw_drawings(self, surface):
        for point in self.drawings:
            adjusted_x = point[0] - self.horizontal_scroll_offset
            adjusted_y = point[1] - self.scroll_offset * 30
            if 0 <= adjusted_y < ALTURA:
                pygame.draw.circle(surface, self.draw_color, (adjusted_x, adjusted_y), 2)
