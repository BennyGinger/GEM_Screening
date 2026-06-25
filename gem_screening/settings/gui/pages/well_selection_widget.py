from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtCore import Qt, QRect, pyqtSignal, QPoint
from PyQt6.QtGui import QPainter, QPen, QColor, QFont

class WellSelectionWidget(QWidget):
    selectionChanged = pyqtSignal(list)
    def _reset_drag(self) -> None:
        self._drag_active: bool = False
        self._drag_mode: str | None = None
        self._drag_start: QPoint | None = None
        self._drag_end: QPoint | None = None

    def mousePressEvent(self, a0):
        if self.dish_type == "35mm":
            return
        if a0 is None:
            return
        pos = a0.pos()
        self._drag_start = pos
        self._drag_end = pos
        self._drag_active = True
        if a0.button() == Qt.MouseButton.LeftButton:
            self._drag_mode = 'select'
        elif a0.button() == Qt.MouseButton.RightButton:
            self._drag_mode = 'deselect'
        else:
            self._drag_mode = None
        self.update()

    def mouseMoveEvent(self, a0):
        if not getattr(self, '_drag_active', False) or self.dish_type == "35mm":
            return
        if a0 is not None:
            self._drag_end = a0.pos()
            self.update()

    def mouseReleaseEvent(self, a0):
        if not getattr(self, '_drag_active', False) or self.dish_type == "35mm":
            return
        if a0 is not None:
            self._drag_end = a0.position().toPoint()
        self._apply_drag_selection()
        self._reset_drag()
        self.update()
        self.selectionChanged.emit(self.selected_wells)

    def _get_cell_geometry(self):
        w, h = self.width(), self.height()
        if self.dish_type == "ibidi-8well":
            cell_w, cell_h = 80, 60
        elif self.dish_type == "96well":
            cell_w = cell_h = 34  # Increased from 28 to 34
        elif self.dish_type == "384well":
            cell_w = cell_h = 17  
        else:
            cell_w, cell_h = 40, 32
        table_w = self.cols * cell_w
        table_h = self.rows * cell_h
        x0 = (w - table_w) // 2
        y0 = (h - table_h) // 2
        return cell_w, cell_h, x0, y0

    def _rect_cells(self, start, end):
        # Return all (r, c) in the rectangle from start to end
        cell_w, cell_h, x0, y0 = self._get_cell_geometry()
        rect = QRect(start, end).normalized()
        cells = []
        for r in range(self.rows):
            for c in range(self.cols):
                cell_rect = QRect(x0 + c*cell_w, y0 + r*cell_h, cell_w, cell_h)
                if rect.intersects(cell_rect):
                    cells.append((r, c))
        return cells

    def _apply_drag_selection(self):
        if self._drag_start is None or self._drag_end is None:
            return
        cells = self._rect_cells(self._drag_start, self._drag_end)
        for r, c in cells:
            well = f"{self.row_labels[r]}{self.col_labels[c]}"
            if self._drag_mode == 'select':
                if well not in self.selected_wells:
                    self.selected_wells.append(well)
            elif self._drag_mode == 'deselect':
                if well in self.selected_wells:
                    self.selected_wells.remove(well)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.dish_type: str = "35mm"
        self.selected_wells: list[str] = ["A1"]
        self.rows: int = 1
        self.cols: int = 1
        self.row_labels: list[str] = ["A"]
        self.col_labels: list[str] = ["1"]
        self._drag_active: bool = False
        self._drag_mode: str | None = None
        self._drag_start = None
        self._drag_end = None
        self.setMinimumSize(200, 320)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def set_dish(self, dish_type: str) -> None:
        self.dish_type = dish_type
        if dish_type == "35mm":
            self.rows, self.cols = 1, 1
            self.row_labels = ["A"]
            self.col_labels = ["1"]
            self.selected_wells = ["A1"]
        elif dish_type == "ibidi-8well":
            self.rows, self.cols = 2, 4
            self.row_labels = ["A", "B"]
            self.col_labels = [str(i+1) for i in range(4)]
            self.selected_wells = []
        elif dish_type == "96well":
            self.rows, self.cols = 8, 12
            self.row_labels = [chr(ord('A')+i) for i in range(8)]
            self.col_labels = [str(i+1) for i in range(12)]
            self.selected_wells = []
        elif dish_type == "384well":
            self.rows, self.cols = 16,24
            self.row_labels = [chr(ord('A')+i) for i in range(16)]
            self.col_labels = [str(i+1) for i in range(24)]
            self.selected_wells = []
        self.update()

    def paintEvent(self, a0):
        painter = QPainter(self)
        w, h = self.width(), self.height()
        if self.dish_type == "35mm":
            # Draw centered circle with A1
            radius = min(w, h) // 3
            center = w//2, h//2
            painter.setPen(QPen(Qt.GlobalColor.black, 2))
            painter.setBrush(QColor(220, 220, 220))
            painter.drawEllipse(center[0]-radius, center[1]-radius, 2*radius, 2*radius)
            painter.setPen(Qt.GlobalColor.black)
            font = QFont()
            font.setPointSize(24)
            painter.setFont(font)
            painter.drawText(QRect(center[0]-radius, center[1]-30, 2*radius, 60), Qt.AlignmentFlag.AlignCenter, "A1")
        elif self.dish_type == "ibidi-8well":
            # Make ibidi cells larger
            cell_w = 80
            cell_h = 60
            table_w = self.cols * cell_w
            table_h = self.rows * cell_h
            x0 = (w - table_w) // 2
            y0 = (h - table_h) // 2
            font = QFont()
            font.setPointSize(12)
            painter.setFont(font)
            for r in range(self.rows):
                for c in range(self.cols):
                    well = f"{self.row_labels[r]}{self.col_labels[c]}"
                    rect = QRect(x0 + c*cell_w, y0 + r*cell_h, cell_w, cell_h)
                    if well in self.selected_wells:
                        painter.setBrush(QColor(200, 220, 255, 180))
                    else:
                        painter.setBrush(QColor(255, 255, 255, 0))
                    painter.setPen(QPen(Qt.GlobalColor.black, 1))
                    painter.drawRect(rect)
                    painter.setPen(Qt.GlobalColor.black)
                    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, well)
        elif self.dish_type == "384well":
            # Draw square wells for 384-well plate
            cell_w = cell_h = 18
            table_w = self.cols * cell_w
            table_h = self.rows * cell_h
            x0 = (w - table_w) // 2
            y0 = (h - table_h) // 2
            font = QFont()
            font.setPointSize(7)  # Smaller font needed to fit labels inside 18px box
            painter.setFont(font)
            for r in range(self.rows):
                for c in range(self.cols):
                    well = f"{self.row_labels[r]}{self.col_labels[c]}"
                    rect = QRect(x0 + c*cell_w, y0 + r*cell_h, cell_w, cell_h)
                    if well in self.selected_wells:
                        painter.setBrush(QColor(200, 220, 255, 180))
                    else:
                        painter.setBrush(QColor(255, 255, 255, 0))
                    painter.setPen(QPen(Qt.GlobalColor.black, 1))
                    painter.drawRect(rect)  # Draws square wells instead of circles
                    painter.setPen(Qt.GlobalColor.black)
                    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, well)
        elif self.dish_type == "96well":
            # Draw round wells for 96well
            cell_d = 34  # Increased from 28 to 34
            cell_w = cell_h = cell_d
            table_w = self.cols * cell_w
            table_h = self.rows * cell_h
            x0 = (w - table_w) // 2
            y0 = (h - table_h) // 2
            font = QFont()
            font.setPointSize(9)
            painter.setFont(font)
            for r in range(self.rows):
                for c in range(self.cols):
                    well = f"{self.row_labels[r]}{self.col_labels[c]}"
                    cx = x0 + c*cell_w + cell_w//2
                    cy = y0 + r*cell_h + cell_h//2
                    if well in self.selected_wells:
                        painter.setBrush(QColor(200, 220, 255, 180))
                    else:
                        painter.setBrush(QColor(255, 255, 255, 0))
                    painter.setPen(QPen(Qt.GlobalColor.black, 1))
                    painter.drawEllipse(cx-cell_d//2, cy-cell_d//2, cell_d, cell_d)
                    painter.setPen(Qt.GlobalColor.black)
                    painter.drawText(QRect(cx-cell_d//2, cy-12, cell_d, 24), Qt.AlignmentFlag.AlignCenter, well)
        # Draw rubber-band rectangle if dragging
        if getattr(self, '_drag_active', False) and self._drag_start is not None and self._drag_end is not None:
            if getattr(self, '_drag_mode', None) == 'deselect':
                pen = QPen(QColor(220, 50, 50, 180), 2, Qt.PenStyle.DashLine)
            else:
                pen = QPen(QColor(50, 120, 220, 180), 2, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            drag_rect = QRect(self._drag_start, self._drag_end).normalized()
            painter.drawRect(drag_rect)
        # Mouse event logic for selection is handled in mousePressEvent, not here.

    def set_selection(self, wells: list[str]) -> None:
        self.selected_wells = wells if wells is not None else []
        self.update()
    
    def _cell_at(self, pos):
        cell_w, cell_h, x0, y0 = self._get_cell_geometry()
        table_w = self.cols * cell_w
        table_h = self.rows * cell_h
        if not (x0 <= pos.x() < x0 + table_w and y0 <= pos.y() < y0 + table_h):
            return None
        c = (pos.x() - x0) // cell_w
        r = (pos.y() - y0) // cell_h
        if 0 <= r < self.rows and 0 <= c < self.cols:
            return (r, c)
        return None
