from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen
from PyQt6.QtCore import Qt, QPointF

class BallVisualizerWidget(QWidget):
    """
    A widget that provides a 2D visualization of 3D ball positions.
    The Z-axis (depth) is represented by the size and opacity of the balls.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.balls = []
        self.setMinimumSize(640, 480)
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor('black'))
        self.setPalette(palette)

        # World to screen mapping parameters (in meters)
        self.world_x_range = (-0.5, 0.5) # Left/Right
        self.world_y_range = (-0.5, 0.5) # Up/Down
        self.world_z_range = (0.5, 2.0)  # Near/Far

    def update_balls(self, tracked_balls):
        """Receives new ball data and schedules a repaint."""
        self.balls = tracked_balls
        self.update() # Trigger a repaint

    def paintEvent(self, event):
        """Draws all the balls on the widget."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if not self.balls:
            painter.setPen(QColor('white'))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Waiting for ball data...")
            return

        # Sort balls by depth so closer balls are drawn on top
        sorted_balls = sorted(self.balls, key=lambda b: b.get('position_3d_kf', [0,0,0])[2], reverse=True)

        for ball in sorted_balls: