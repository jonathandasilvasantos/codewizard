import pygame
import sys
import re
import pyperclip  # for clipboard copy/paste

# --------------------
# Configuration Constants
# --------------------
INITIAL_WIDTH, INITIAL_HEIGHT = 800, 600
NUM_ROWS, NUM_COLS = 20, 10

CELL_WIDTH = 100
CELL_HEIGHT = 30

HEADER_WIDTH = 50     # For row numbers
HEADER_HEIGHT = 30    # For column headers

# Colors
BACKGROUND_COLOR = (0, 0, 0)
HEADER_BG_COLOR = (0, 0, 0)
GRID_COLOR = (255, 255, 255)
# Use a bright color for the selection rectangle in editing mode.
SELECTED_COLOR = (255, 255, 255)
TEXT_COLOR = (255, 255, 255)
CURSOR_COLOR = (255, 255, 255)

FONT_SIZE = 20

# --------------------
# Spreadsheet Class
# --------------------
class Spreadsheet:
    def __init__(self, font, rows=NUM_ROWS, cols=NUM_COLS):
        self.font = font
        self.rows = rows
        self.cols = cols

        # 2D list (rows x cols) to store cell values (as strings).
        self.cells = [['' for _ in range(cols)] for _ in range(rows)]

        # Track the currently selected cell (row, col)
        self.selected_row = 0
        self.selected_col = 0

        # ---- Advanced Cell Editing State ----
        # When editing is True, the selected cell is being edited.
        self.editing = False
        self.edit_buffer = ""          # The text being edited
        self.edit_cursor_pos = 0       # Cursor position within the edit_buffer (index)
        self.edit_sel_start = None     # If not None, marks one end of a text selection
        self.edit_sel_end = None       # If not None, marks the other end
        self.edit_undo_stack = []      # List of past edit states for undo
        self.edit_redo_stack = []      # List of undone states for redo
        self.cursor_visible = True     # For blinking effect
        self.last_cursor_toggle_time = pygame.time.get_ticks()

    # ------ Editing Helper Methods ------
    def start_edit(self, clear=False):
        """
        Begin editing the selected cell.
        If clear is True, the cell is cleared first.
        Otherwise, the current cell text is loaded.
        """
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
        """Commit the current edit (save changes to the cell) and exit editing mode."""
        if self.editing:
            self.cells[self.selected_row][self.selected_col] = self.edit_buffer
        self.editing = False

    def push_edit_undo(self):
        """Push the current editing state onto the undo stack and clear the redo stack."""
        state = (self.edit_buffer, self.edit_cursor_pos, self.edit_sel_start, self.edit_sel_end)
        self.edit_undo_stack.append(state)
        self.edit_redo_stack.clear()

    def undo_edit(self):
        """Undo the last edit operation."""
        if len(self.edit_undo_stack) > 1:
            # Save current state in redo stack.
            current_state = (self.edit_buffer, self.edit_cursor_pos, self.edit_sel_start, self.edit_sel_end)
            self.edit_redo_stack.append(current_state)
            # Remove current state and restore previous one.
            self.edit_undo_stack.pop()
            prev_state = self.edit_undo_stack[-1]
            self.edit_buffer, self.edit_cursor_pos, self.edit_sel_start, self.edit_sel_end = prev_state

    def redo_edit(self):
        """Redo an undone edit operation."""
        if self.edit_redo_stack:
            state = self.edit_redo_stack.pop()
            self.push_edit_undo()  # Save current state before redoing.
            self.edit_buffer, self.edit_cursor_pos, self.edit_sel_start, self.edit_sel_end = state

    def _delete_selection_if_any(self):
        """If text is selected in the editing cell, delete it and update the cursor."""
        if (self.edit_sel_start is not None and self.edit_sel_end is not None and
                self.edit_sel_start != self.edit_sel_end):
            start = min(self.edit_sel_start, self.edit_sel_end)
            end = max(self.edit_sel_start, self.edit_sel_end)
            self.edit_buffer = self.edit_buffer[:start] + self.edit_buffer[end:]
            self.edit_cursor_pos = start
            self.edit_sel_start = None
            self.edit_sel_end = None

    # ------ Event Handling ------
    def handle_event(self, event: pygame.event.Event):
        # --- Mouse Input ---
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # left-click
                x, y = event.pos
                # Check if click is inside grid area (beyond headers)
                if x >= HEADER_WIDTH and y >= HEADER_HEIGHT:
                    # If a cell is currently being edited, commit its changes.
                    self.commit_edit()
                    col = (x - HEADER_WIDTH) // CELL_WIDTH
                    row = (y - HEADER_HEIGHT) // CELL_HEIGHT
                    if row < self.rows and col < self.cols:
                        self.selected_row = row
                        self.selected_col = col
                        self.editing = False  # New cell starts not in edit mode.
        # --- Keyboard Input ---
        elif event.type == pygame.KEYDOWN:
            mod = event.mod
            ctrl_pressed = mod & pygame.KMOD_CTRL
            shift_pressed = mod & pygame.KMOD_SHIFT
            if self.editing:
                # ======= Editing Mode =======
                if ctrl_pressed:
                    if event.key == pygame.K_z:
                        self.undo_edit()
                    elif event.key == pygame.K_y:
                        self.redo_edit()
                    elif event.key == pygame.K_c:
                        # Copy selected text if any.
                        if (self.edit_sel_start is not None and self.edit_sel_end is not None and
                                self.edit_sel_start != self.edit_sel_end):
                            start = min(self.edit_sel_start, self.edit_sel_end)
                            end = max(self.edit_sel_start, self.edit_sel_end)
                            pyperclip.copy(self.edit_buffer[start:end])
                    elif event.key == pygame.K_v:
                        # Paste text from clipboard.
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
                        # Cut: copy then delete selection.
                        if (self.edit_sel_start is not None and self.edit_sel_end is not None and
                                self.edit_sel_start != self.edit_sel_end):
                            start = min(self.edit_sel_start, self.edit_sel_end)
                            end = max(self.edit_sel_start, self.edit_sel_end)
                            pyperclip.copy(self.edit_buffer[start:end])
                            self.push_edit_undo()
                            self._delete_selection_if_any()
                else:
                    if event.key == pygame.K_RETURN:
                        # Pressing Enter commits the edit.
                        self.commit_edit()
                    elif event.key == pygame.K_ESCAPE:
                        # Pressing Escape cancels editing.
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
                    # (Other keys such as Home/End could be added similarly.)
            else:
                # ======= Navigation (Not Editing) =======
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
                    # Start editing and clear the cell.
                    self.start_edit(clear=True)
                elif event.key == pygame.K_DELETE:
                    self.start_edit(clear=True)
                else:
                    # For any other key, do nothing here.
                    pass
        elif event.type == pygame.TEXTINPUT:
            # TEXTINPUT is fired for regular character input.
            if not self.editing:
                # When not yet editing, start editing and clear the cell.
                self.start_edit(clear=True)
            self.push_edit_undo()
            self._delete_selection_if_any()
            self.edit_buffer = (self.edit_buffer[:self.edit_cursor_pos] +
                                event.text +
                                self.edit_buffer[self.edit_cursor_pos:])
            self.edit_cursor_pos += len(event.text)
            self.edit_sel_start = None
            self.edit_sel_end = None

    # ------ Cursor Blinking ------
    def update_cursor(self):
        """Toggle the blinking cursor (only when editing)."""
        if self.editing:
            current_time = pygame.time.get_ticks()
            if current_time - self.last_cursor_toggle_time > 500:
                self.cursor_visible = not self.cursor_visible
                self.last_cursor_toggle_time = current_time
        else:
            self.cursor_visible = False

    # ------ Formula Evaluation (for cells starting with '=') ------
    def get_cell_numeric_value(self, row: int, col: int) -> float:
        """Return the numeric value of a cell (evaluating formulas if needed)."""
        try:
            cell_text = self.cells[row][col]
            # If the cell contains a formula (starts with "=") and is not currently being edited,
            # evaluate it; otherwise, use the raw text.
            if cell_text.startswith("=") and not (self.selected_row == row and self.selected_col == col and self.editing):
                value = self.evaluate_formula(cell_text)
            else:
                value = cell_text
            return float(value) if value != "" else 0.0
        except Exception:
            return 0.0

    def evaluate_formula(self, formula: str) -> str:
        """
        Evaluate a formula string (which starts with '='). Supports SUM and basic math.
        For example:
          =1+2*3
          =A1+B2
          =SUM(A1, B2, 3, A1:B3)
        Returns the result as a string, or "#ERR" if an error occurs.
        """
        # Remove the initial '='
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
                # Replace cell references (e.g., A1) with their numeric values.
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
        """
        Return the value to display in a cell.
        If the cell contains a formula (starts with '=') and is not being edited, show its evaluated result;
        otherwise, show the raw text.
        When the cell is being edited, display the edit_buffer.
        """
        if row == self.selected_row and col == self.selected_col and self.editing:
            return self.edit_buffer
        cell_text = self.cells[row][col]
        if cell_text.startswith("=") and not (row == self.selected_row and col == self.selected_col and self.editing):
            return self.evaluate_formula(cell_text)
        return cell_text

    # ------ Drawing ------
    def draw(self, surface: pygame.Surface):
        """Draw the spreadsheet grid, headers, cell values, and selection/cursor (when editing)."""
        # Fill background.
        surface.fill(BACKGROUND_COLOR)

        # --- Draw Column Headers ---
        for col in range(self.cols):
            x = HEADER_WIDTH + col * CELL_WIDTH
            rect = pygame.Rect(x, 0, CELL_WIDTH, HEADER_HEIGHT)
            pygame.draw.rect(surface, HEADER_BG_COLOR, rect)
            pygame.draw.rect(surface, GRID_COLOR, rect, 1)
            label_text = chr(65 + col)  # A, B, C, etc.
            label = self.font.render(label_text, True, TEXT_COLOR)
            label_rect = label.get_rect(center=rect.center)
            surface.blit(label, label_rect)

        # --- Draw Row Headers ---
        for row in range(self.rows):
            y = HEADER_HEIGHT + row * CELL_HEIGHT
            rect = pygame.Rect(0, y, HEADER_WIDTH, CELL_HEIGHT)
            pygame.draw.rect(surface, HEADER_BG_COLOR, rect)
            pygame.draw.rect(surface, GRID_COLOR, rect, 1)
            label = self.font.render(str(row + 1), True, TEXT_COLOR)
            label_rect = label.get_rect(center=rect.center)
            surface.blit(label, label_rect)

        # --- Draw Cells ---
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

        # --- Highlight Selected Cell ---
        sel_x = HEADER_WIDTH + self.selected_col * CELL_WIDTH
        sel_y = HEADER_HEIGHT + self.selected_row * CELL_HEIGHT
        sel_rect = pygame.Rect(sel_x, sel_y, CELL_WIDTH, CELL_HEIGHT)
        pygame.draw.rect(surface, SELECTED_COLOR, sel_rect, 3)

        # --- If Editing, draw text selection and blinking cursor in the selected cell ---
        if self.editing and self.selected_row < self.rows and self.selected_col < self.cols:
            cell_x = sel_x + 5
            cell_y = sel_y + 5
            # Draw selection highlight if any
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
            # Draw blinking cursor.
            text_before_cursor = self.edit_buffer[:self.edit_cursor_pos]
            cursor_x = cell_x + self.font.size(text_before_cursor)[0]
            if self.cursor_visible:
                cursor_rect = pygame.Rect(cursor_x, cell_y, 2, self.font.get_height())
                pygame.draw.rect(surface, CURSOR_COLOR, cursor_rect)

    def get_cell_numeric_value(self, row: int, col: int) -> float:
        """
        (Duplicate method – needed for formula evaluation.)
        Return the numeric value of a cell (evaluating formulas if needed).
        """
        try:
            cell_text = self.cells[row][col]
            if cell_text.startswith("=") and not (self.selected_row == row and self.selected_col == col and self.editing):
                value = self.evaluate_formula(cell_text)
            else:
                value = cell_text
            return float(value) if value != "" else 0.0
        except Exception:
            return 0.0

# --------------------
# Main Program
# --------------------
def main():
    pygame.init()
    pygame.key.set_repeat(300, 50)
    screen = pygame.display.set_mode((INITIAL_WIDTH, INITIAL_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("Improved Excel-like App with Advanced Cell Editing")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("monospace", FONT_SIZE)

    # Create our spreadsheet instance.
    spreadsheet = Spreadsheet(font)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
            else:
                spreadsheet.handle_event(event)

        spreadsheet.update_cursor()
        spreadsheet.draw(screen)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
