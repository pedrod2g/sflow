from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QComboBox, QCheckBox, 
    QTextEdit, QPushButton, QHBoxLayout
)
from core.settings import app_settings

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración de Refinamiento IA")
        self.setFixedWidth(400)

        layout = QVBoxLayout()

        # Enable/Disable Checkbox
        self.enable_cb = QCheckBox("Activar refinamiento automático")
        self.enable_cb.setChecked(app_settings.refinement_enabled)
        layout.addWidget(self.enable_cb)

        # Format Dropdown
        layout.addWidget(QLabel("Formato de salida:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["Prompt", "Correo electrónico", "Informe", "Novela", "Otro"])
        self.format_combo.setEditable(True)
        self.format_combo.setCurrentText(app_settings.refinement_format)
            
        layout.addWidget(self.format_combo)

        # Context TextEdit
        layout.addWidget(QLabel("Campo de contextualización (opcional):"))
        self.context_edit = QTextEdit()
        self.context_edit.setPlaceholderText("Ej: miniatura, viral, de un video de Cloud Code...")
        self.context_edit.setPlainText(app_settings.refinement_context)
        self.context_edit.setMaximumHeight(80)
        layout.addWidget(self.context_edit)

        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Guardar")
        save_btn.clicked.connect(self._save)
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def _save(self):
        app_settings.refinement_enabled = self.enable_cb.isChecked()
        app_settings.refinement_format = self.format_combo.currentText()
        app_settings.refinement_context = self.context_edit.toPlainText().strip()
        app_settings.save()
        self.accept()
