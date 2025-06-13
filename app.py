import os
import sqlite3
from ultralytics import YOLO
import json
import sys
import shutil
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout,
    QPushButton, QLineEdit, QLabel,
    QTableWidget, QTableWidgetItem,
    QFileDialog, QGraphicsScene,
    QGraphicsView, QGraphicsPixmapItem,
    QInputDialog, QDialog, QFormLayout,
    QMessageBox, QGraphicsRectItem, QGraphicsTextItem,
    QHBoxLayout, QDateEdit, QDialogButtonBox, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPen, QBrush, QColor, QFont, QFontMetrics, QPainter, QPixmap

CLASS_NAMES = {
    0: "Impacted",
    1: "Caries",
    2: "Peri Lesion",
    3: "Deep Caries"
}

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "patients.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
      CREATE TABLE IF NOT EXISTS patients (
        id    INTEGER PRIMARY KEY,
        name  TEXT NOT NULL,
        dob   TEXT,
        email TEXT,
        user_id INTEGER
      )
    """)
    c.execute("""
      CREATE TABLE IF NOT EXISTS xrays (
        id         INTEGER PRIMARY KEY,
        patient_id INTEGER NOT NULL,
        filepath   TEXT NOT NULL,
        prediction TEXT,
        FOREIGN KEY(patient_id) REFERENCES patients(id)
      )
    """)
    c.execute("""
      CREATE TABLE IF NOT EXISTS users (
        id       INTEGER PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
      )
    """)
    conn.commit()
    conn.close()
    
    # load your model weights
MODEL_PATH = os.path.join(os.path.dirname(__file__), "model", "best.pt")
yolo = YOLO(MODEL_PATH)

def predict(image_path):
    """
    Run YOLO inference on image_path at conf threshold 0.4.
    Returns a JSON string of results (class, x1,y1,x2,y2,conf).
    """
    results = yolo(image_path, conf=0.4)[0]  
    boxes = []
    for *box, conf, cls in results.boxes.data.tolist():
        x1,y1,x2,y2 = box
        boxes.append({
            "class": int(cls),
            "conf": float(conf),
            "x1": x1, "y1": y1, "x2": x2, "y2": y2
        })
    return json.dumps(boxes)

class RegisterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Register")
        self.conn = sqlite3.connect(DB_PATH)
        layout = QFormLayout(self)

        self.user_in = QLineEdit()
        self.pw_in   = QLineEdit(); self.pw_in.setEchoMode(QLineEdit.Password)
        self.btn     = QPushButton("Create Account")
        layout.addRow("Username:", self.user_in)
        layout.addRow("Password:", self.pw_in)
        layout.addRow(self.btn)

        self.btn.clicked.connect(self.register)

    def register(self):
        u = self.user_in.text().strip()
        p = self.pw_in.text().strip()
        if not u or not p:
            QMessageBox.warning(self, "Error", "Please fill both fields.")
            return
        try:
            cur = self.conn.cursor()
            cur.execute("INSERT INTO users(username,password) VALUES(?,?)", (u, p))
            self.conn.commit()
            QMessageBox.information(self, "Success", "Account created!")
            self.accept()
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "Error", "Username already taken.")
            
class ZoomableGraphicsView(QGraphicsView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # smooth rendering
        self.setRenderHint(QPainter.Antialiasing)
        # enable drag-to-pan
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        # track current zoom level
        self._zoom = 0

    def wheelEvent(self, event):
        """Zoom in/out with Ctrl+wheel, otherwise pass through."""
        if event.modifiers() & Qt.ControlModifier:
            # angleDelta.y() is positive when scrolling up
            zoom_in = event.angleDelta().y() > 0
            factor = 1.25 if zoom_in else 0.8

            # limit zoom levels
            if (self._zoom < 10 and zoom_in) or (self._zoom > -10 and not zoom_in):
                self._zoom += 1 if zoom_in else -1
                self.scale(factor, factor)
        else:
            # no Ctrl: scroll normally
            super().wheelEvent(event)

    def reset_zoom(self):
        """Reset zoom to default (fitInView)."""
        self._zoom = 0
        self.resetTransform()
        
class DeselectableTableWidget(QTableWidget):
    def mousePressEvent(self, event):
        click_point = event.position().toPoint()
        idx = self.indexAt(click_point)
        if not idx.isValid():
            self.clearSelection()
            self.setCurrentCell(-1, -1)
        super().mousePressEvent(event)

class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login")
        self.conn = sqlite3.connect(DB_PATH)
        self.resize(400, 250)
        layout = QVBoxLayout(self)
        # App name label
        app_label = QLabel("X-ray Management App")
        app_label.setAlignment(Qt.AlignCenter)
        font = app_label.font()
        font.setPointSize(18)
        font.setBold(True)
        app_label.setFont(font)
        layout.addWidget(app_label)

        self.user = QLineEdit(); self.user.setPlaceholderText("Username")
        self.pw   = QLineEdit(); self.pw.setEchoMode(QLineEdit.Password)
        self.btn_login = QPushButton("Log In")
        self.btn_reg   = QPushButton("Register")

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.btn_login)
        btn_layout.addWidget(self.btn_reg)

        layout.addWidget(QLabel("Please log in or register"))
        layout.addWidget(self.user)
        layout.addWidget(self.pw)
        layout.addLayout(btn_layout)

        self.btn_login.clicked.connect(self.check)
        self.btn_reg.clicked.connect(self.open_register)

    def open_register(self):
        rd = RegisterDialog(self)
        rd.exec()

    def check(self):
        u = self.user.text().strip()
        p = self.pw.text().strip()
        cur = self.conn.cursor()
        cur.execute("SELECT id FROM users WHERE username=? AND password=?", (u,p))
        row = cur.fetchone()
        if row:
            self.close()
            user_id = row[0]
            self.main = MainWindow(user_id)
            self.main.showMaximized()
        else:
            QMessageBox.warning(self, "Error", "Invalid credentials")
            
class MainWindow(QWidget):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
        self.setWindowTitle("X-ray Management App")
        self.conn = sqlite3.connect(DB_PATH)
        self.setWindowFlags(Qt.Window)  # Ensure standard window frame
        main_layout = QVBoxLayout(self)
        # Top bar with logout button and patient list title
        top_bar = QHBoxLayout()
        lbl_patient_list = QLabel("Patient List")
        font = lbl_patient_list.font()
        font.setPointSize(14)
        font.setBold(True)
        lbl_patient_list.setFont(font)
        lbl_patient_list.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        top_bar.addWidget(lbl_patient_list)
        top_bar.addStretch()
        self.btn_logout = QPushButton("Logout")
        top_bar.addWidget(self.btn_logout)
        self.btn_logout.clicked.connect(self.logout)
        main_layout.addLayout(top_bar)
        layout = QVBoxLayout()
        main_layout.addLayout(layout)
        # Patient list
        self.table = DeselectableTableWidget(0, 3)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setHorizontalHeaderLabels(["Name", "Date of Birth", "Email"])
        self.load_patients()
        layout.addWidget(self.table)
        # Patient controls
        patient_btns = QHBoxLayout()
        btn_new = QPushButton("New Patient")
        btn_remove = QPushButton("Remove Patient")
        btn_lookup = QPushButton("Look Up Patient")
        btn_show_all = QPushButton("Show All Patients")
        patient_btns.addWidget(btn_new)
        patient_btns.addWidget(btn_remove)
        patient_btns.addWidget(btn_lookup)
        patient_btns.addWidget(btn_show_all)
        layout.addLayout(patient_btns)
        btn_new.clicked.connect(self.new_patient)
        btn_remove.clicked.connect(self.remove_patient)
        btn_lookup.clicked.connect(self.lookup_patient)
        btn_show_all.clicked.connect(self.load_patients)
        
        # X-ray section
        xray_btns = QHBoxLayout()
        self.btn_add_xray = QPushButton("Add X-ray for Selected Patient")
        self.btn_add_xray.setMinimumWidth(0)
        self.btn_add_xray.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.btn_add_xray.clicked.connect(self.add_xray)
        xray_btns.addWidget(self.btn_add_xray)
        self.btn_immediate_xray = QPushButton("Immediate X-ray Test")
        self.btn_immediate_xray.setMinimumWidth(0)
        self.btn_immediate_xray.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.btn_immediate_xray.clicked.connect(self.immediate_xray_test)
        xray_btns.addWidget(self.btn_immediate_xray)
        layout.addLayout(xray_btns)
        layout.addWidget(self.btn_add_xray)
        
        # View X-ray history button
        self.btn_xray_history = QPushButton("View X-ray History")
        layout.addWidget(self.btn_xray_history)
        self.btn_xray_history.clicked.connect(self.view_xray_history)
        
        # Image viewers
        orig_label = QLabel("Original")
        pred_label = QLabel("Prediction")
        font = orig_label.font()
        font.setBold(True)
        font.setPointSize(12)
        orig_label.setFont(font); pred_label.setFont(font)
        self.viewer_orig = ZoomableGraphicsView(); self.viewer_pred = ZoomableGraphicsView()
        layout.addWidget(orig_label); layout.addWidget(self.viewer_orig)
        layout.addWidget(pred_label); layout.addWidget(self.viewer_pred)

        # Zoom controls
        zoom_layout = QHBoxLayout()
        self.btn_zoom_in = QPushButton("Zoom In")
        self.btn_zoom_out = QPushButton("Zoom Out")
        self.btn_zoom_reset = QPushButton("Reset Zoom")
        zoom_layout.addWidget(self.btn_zoom_in)
        zoom_layout.addWidget(self.btn_zoom_out)
        zoom_layout.addWidget(self.btn_zoom_reset)
        layout.addLayout(zoom_layout)
        self.btn_zoom_in.clicked.connect(self.zoom_in)
        self.btn_zoom_out.clicked.connect(self.zoom_out)
        self.btn_zoom_reset.clicked.connect(self.zoom_reset)

    
    def load_patients(self):
        cur = self.conn.cursor()
        rows = cur.execute("SELECT name, dob, email FROM patients WHERE user_id=?", (self.user_id,)).fetchall()
        self.table.setRowCount(len(rows))
        for i, (name, dob, email) in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(name if name else "no data"))
            self.table.setItem(i, 1, QTableWidgetItem(dob if dob else "no data"))
            self.table.setItem(i, 2, QTableWidgetItem(email if email else "no data"))
    
    def new_patient(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Add New Patient")
        layout = QFormLayout(dialog)
        name_edit = QLineEdit()
        dob_edit = QDateEdit()
        dob_edit.setCalendarPopup(True)
        dob_edit.setDisplayFormat("dd-MM-yyyy")
        email_edit = QLineEdit()
        layout.addRow("Name:", name_edit)
        layout.addRow("Date of Birth:", dob_edit)
        layout.addRow("Email:", email_edit)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addRow(btns)
        def on_accept():
            name = name_edit.text().strip()
            dob = dob_edit.date().toString("dd-MM-yyyy")
            email = email_edit.text().strip()
            if not name or not email:
                QMessageBox.warning(dialog, "Error", "Name and email are required.")
                return
            cur = self.conn.cursor()
            cur.execute("INSERT INTO patients (name, dob, email, user_id) VALUES (?, ?, ?, ?)", (name, dob, email, self.user_id))
            self.conn.commit()
            self.load_patients()
            dialog.accept()
        btns.accepted.connect(on_accept)
        btns.rejected.connect(dialog.reject)
        dialog.exec()
    
    def add_xray(self):
        idx = self.table.currentRow()
        if idx < 0:
            QMessageBox.warning(self, "No Patient Selected", "Please select a patient.")
            return
        # Get patient name from table, then fetch id from DB
        name = self.table.item(idx, 0).text()
        cur = self.conn.cursor()
        row = cur.execute("SELECT id FROM patients WHERE name=?", (name,)).fetchone()
        if not row:
            QMessageBox.warning(self, "Error", "Patient not found in database.")
            return
        pid = row[0]
        file, _ = QFileDialog.getOpenFileName(self, "Select X-ray", "", "Images (*.png *.jpg *.jpeg)")
        if not file: return
        # copy into data/xrays/
        dest_dir = os.path.join("data","xrays",str(pid))
        os.makedirs(dest_dir, exist_ok=True)
        fname = os.path.basename(file)
        dest = os.path.join(dest_dir, fname)
        shutil.copy(file, dest)
        # run prediction
        pred_json = predict(dest)
        cur = self.conn.cursor()
        cur.execute(
          "INSERT INTO xrays(patient_id,filepath,prediction) VALUES(?,?,?)",
          (pid, dest, pred_json)
        )
        self.conn.commit()
        self.show_xray(dest, pred_json)
    
    def show_xray(self, img_path, pred_json):
        # load prediction data
        boxes = json.loads(pred_json)

        # --- ORIGINAL IMAGE (unchanged) ---
        scene1 = QGraphicsScene()
        pix1 = QPixmap(img_path)
        scene1.addItem(QGraphicsPixmapItem(pix1))
        self.viewer_orig.setScene(scene1)
        self.viewer_orig.resetTransform()
        self.viewer_orig.setRenderHint(QPainter.Antialiasing)
        self.viewer_orig.setDragMode(QGraphicsView.ScrollHandDrag)
        self.viewer_orig.fitInView(scene1.sceneRect(), Qt.KeepAspectRatio)

        # --- PREDICTION IMAGE WITH COLORED BOXES + LABELS ---
        scene2 = QGraphicsScene()
        pix2 = QPixmap(img_path)
        scene2.addItem(QGraphicsPixmapItem(pix2))

        # configure pen/brush/font
        pen = QPen(QColor(0, 255, 255), 2)             # cyan, width 2
        font = QFont(); font.setPointSize(10); font.setBold(True)

        for b in boxes:
            x1, y1 = b["x1"], b["y1"]
            w, h   = b["x2"] - x1, b["y2"] - y1
            cls, conf = b["class"], b["conf"]
            label = f"{CLASS_NAMES.get(cls, cls)} {conf:.2f}"

            # 1) box
            rect_item = QGraphicsRectItem(x1, y1, w, h)
            rect_item.setPen(pen)
            scene2.addItem(rect_item)

            # 2) text background
            # measure text size crudely
            metrics = QFontMetrics(font)
            tw = metrics.horizontalAdvance(label) + 4
            th = metrics.height() + 2

            bg = QGraphicsRectItem(x1, y1 - th, tw, th)
            bg.setBrush(QBrush(QColor(0, 0, 0, 160)))   # semi-transparent black
            bg.setPen(QPen(Qt.NoPen))
            scene2.addItem(bg)

            # 3) text
            text_item = QGraphicsTextItem(label)
            text_item.setDefaultTextColor(QColor(0, 255, 255))
            text_item.setFont(font)
            text_item.setPos(x1 + 2, y1 - th + 1)
            scene2.addItem(text_item)

        # set up the view
        self.viewer_pred.setScene(scene2)
        self.viewer_pred.resetTransform()
        self.viewer_pred.setRenderHint(QPainter.Antialiasing)
        self.viewer_pred.setDragMode(QGraphicsView.ScrollHandDrag)
        self.viewer_pred.fitInView(scene2.sceneRect(), Qt.KeepAspectRatio)


    def zoom_in(self):
        self.viewer_pred.scale(1.25, 1.25)
        self.viewer_orig.scale(1.25, 1.25)
    def zoom_out(self):
        self.viewer_pred.scale(0.8, 0.8)
        self.viewer_orig.scale(0.8, 0.8)
    def zoom_reset(self):
        self.viewer_pred.reset_zoom()
        self.viewer_orig.reset_zoom()

    def view_xray_history(self):
        idx = self.table.currentRow()
        if idx < 0:
            QMessageBox.warning(self, "Error", "Please select a patient.")
            return
        # Get patient name from table, then fetch id from DB
        name = self.table.item(idx, 0).text()
        cur = self.conn.cursor()
        row = cur.execute("SELECT id FROM patients WHERE name=?", (name,)).fetchone()
        if not row:
            QMessageBox.warning(self, "Error", "Patient not found in database.")
            return
        pid = row[0]
        rows = cur.execute("SELECT id, filepath, prediction FROM xrays WHERE patient_id=? ORDER BY id DESC", (pid,)).fetchall()
        if not rows:
            QMessageBox.information(self, "No X-rays", "No X-rays found for this patient.")
            return
        # Show dialog with list of X-rays
        dlg = QDialog(self)
        dlg.setWindowTitle("X-ray History")
        vbox = QVBoxLayout(dlg)
        list_widget = QTableWidget(len(rows), 2)
        list_widget.setHorizontalHeaderLabels(["ID", "Filepath"])
        for i, (xid, fpath, _) in enumerate(rows):
            list_widget.setItem(i, 0, QTableWidgetItem(str(xid)))
            list_widget.setItem(i, 1, QTableWidgetItem(fpath))
        vbox.addWidget(list_widget)
        btn_view = QPushButton("View Selected X-ray")
        vbox.addWidget(btn_view)
        def show_selected():
            sel = list_widget.currentRow()
            if sel < 0:
                QMessageBox.warning(dlg, "Error", "Please select an X-ray.")
                return
            fpath = list_widget.item(sel, 1).text()
            pred = rows[sel][2]
            self.show_xray(fpath, pred)
            dlg.accept()
        btn_view.clicked.connect(show_selected)
        dlg.exec()
    

    def remove_patient(self):
        idx = self.table.currentRow()
        if idx < 0:
            QMessageBox.warning(self, "Error", "Please select a patient to remove.")
            return
        # Need to get patient name from table, then fetch id from DB
        name = self.table.item(idx, 0).text()
        cur = self.conn.cursor()
        row = cur.execute("SELECT id FROM patients WHERE name=?", (name,)).fetchone()
        if not row:
            QMessageBox.warning(self, "Error", "Patient not found in database.")
            return
        pid = row[0]
        reply = QMessageBox.question(self, "Confirm", f"Remove patient '{name}'? This will delete all their X-rays.", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            cur.execute("DELETE FROM xrays WHERE patient_id=?", (pid,))
            cur.execute("DELETE FROM patients WHERE id=?", (pid,))
            self.conn.commit()
            self.load_patients()

    def lookup_patient(self):
        name, ok = QInputDialog.getText(self, "Look Up Patient", "Enter patient name:")
        if not ok or not name.strip():
            return
        cur = self.conn.cursor()
        rows = cur.execute("SELECT name, dob, email FROM patients WHERE name LIKE ? AND user_id=?", (f"%{name.strip()}%", self.user_id)).fetchall()
        if not rows:
            QMessageBox.information(self, "No Results", "No patients found.")
            return
        self.table.setRowCount(len(rows))
        for i, (name, dob, email) in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(name if name else "no data"))
            self.table.setItem(i, 1, QTableWidgetItem(dob if dob else "no data"))
            self.table.setItem(i, 2, QTableWidgetItem(email if email else "no data"))
        # Ensure the X-ray History button is visible and in the correct layout
        if hasattr(self, 'btn_xray_history'):
            parent_layout = self.table.parentWidget().layout() if self.table.parentWidget() else None
            if parent_layout and not parent_layout.indexOf(self.btn_xray_history) >= 0:
                parent_layout.addWidget(self.btn_xray_history)
        self.btn_xray_history.clicked.connect(self.view_xray_history)
        
    def immediate_xray_test(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select X-ray for Immediate Test", "", "Images (*.png *.jpg *.jpeg)")
        if not file:
            return
        pred_json = predict(file)
        self.show_xray(file, pred_json)
    
    def logout(self):
        self.close()
        self.login = LoginWindow()
        self.login.show()
    
if __name__ == "__main__":
    init_db()
    app = QApplication(sys.argv)
    login = LoginWindow()
    login.show()
    sys.exit(app.exec())