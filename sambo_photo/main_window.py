from __future__ import annotations

from pathlib import Path

from PIL.ImageQt import ImageQt
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QPixmap
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from .image_engine import (
    SUPPORTED_SUFFIXES,
    ensure_extension,
    export_image,
    load_image,
    render_image,
    suggested_filename,
    target_size,
    unique_destination,
)
from .models import OutputSettings, PhotoTask
from .presets import PresetManager


APP_TITLE = "삼보사진관"
CATEGORY_LABELS = {
    "ratio": "비율",
    "id_photo": "증명/여권형",
    "print": "인화",
    "frame": "액자",
}


class MainWindow(QMainWindow):
    def __init__(self, preset_dir: Path):
        super().__init__()
        self.setWindowTitle(f"{APP_TITLE} 0.1")
        self.resize(1500, 900)
        self.setAcceptDrops(True)

        self.tasks: list[PhotoTask] = []
        self.current_index = -1
        self.preset_manager = PresetManager(preset_dir)
        self._loading_ui = False

        self._build_ui()
        self._apply_dark_style()

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)

        header = QHBoxLayout()
        title = QLabel("삼보사진관")
        title.setObjectName("title")
        subtitle = QLabel("사진은 그대로, 규격은 정확하게.")
        subtitle.setObjectName("subtitle")
        head_text = QVBoxLayout()
        head_text.addWidget(title)
        head_text.addWidget(subtitle)
        header.addLayout(head_text)
        header.addStretch()
        add_files = QPushButton("사진 추가")
        add_files.clicked.connect(self.add_files)
        add_folder = QPushButton("폴더 추가")
        add_folder.clicked.connect(self.add_folder)
        header.addWidget(add_files)
        header.addWidget(add_folder)
        outer.addLayout(header)

        splitter = QSplitter(Qt.Horizontal)
        outer.addWidget(splitter, 1)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        self.list_widget = QListWidget()
        self.list_widget.currentRowChanged.connect(self.select_task)
        left_layout.addWidget(QLabel("사진 목록"))
        left_layout.addWidget(self.list_widget, 1)
        remove_btn = QPushButton("선택 사진 제거")
        remove_btn.clicked.connect(self.remove_selected)
        left_layout.addWidget(remove_btn)
        splitter.addWidget(left)

        center = QWidget()
        center_layout = QVBoxLayout(center)
        self.preview = QLabel("사진을 추가하세요")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumSize(QSize(600, 600))
        self.preview.setObjectName("preview")
        center_layout.addWidget(self.preview, 1)
        self.info_label = QLabel("")
        self.info_label.setAlignment(Qt.AlignCenter)
        center_layout.addWidget(self.info_label)
        splitter.addWidget(center)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(self._build_output_box())
        right_layout.addWidget(self._build_crop_box())
        right_layout.addStretch()

        apply_row = QHBoxLayout()
        apply_current = QPushButton("현재 사진에 적용")
        apply_current.clicked.connect(self.apply_current)
        apply_all = QPushButton("모든 사진에 적용")
        apply_all.clicked.connect(self.apply_all)
        apply_row.addWidget(apply_current)
        apply_row.addWidget(apply_all)
        right_layout.addLayout(apply_row)

        save_current = QPushButton("현재 사진 저장")
        save_current.clicked.connect(self.export_current)
        save_all = QPushButton("전부 저장")
        save_all.clicked.connect(self.export_all)
        save_all.setObjectName("primary")
        right_layout.addWidget(save_current)
        right_layout.addWidget(save_all)
        splitter.addWidget(right)

        splitter.setSizes([280, 820, 400])

        reset_action = QAction("현재 설정 초기화", self)
        reset_action.triggered.connect(self.reset_current)
        self.menuBar().addAction(reset_action)

    def _build_output_box(self) -> QGroupBox:
        box = QGroupBox("출력 규격")
        form = QFormLayout(box)

        self.category_combo = QComboBox()
        for category in self.preset_manager.categories:
            self.category_combo.addItem(CATEGORY_LABELS.get(category, category), category)
        self.category_combo.currentIndexChanged.connect(self.reload_presets)
        form.addRow("종류", self.category_combo)

        self.preset_combo = QComboBox()
        self.preset_combo.currentIndexChanged.connect(self.load_selected_preset)
        form.addRow("프리셋", self.preset_combo)

        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(0.1, 20000)
        self.width_spin.setDecimals(2)
        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(0.1, 20000)
        self.height_spin.setDecimals(2)
        self.unit_combo = QComboBox()
        self.unit_combo.addItems(["px", "mm", "cm", "inch"])
        size_row = QHBoxLayout()
        size_row.addWidget(self.width_spin)
        size_row.addWidget(QLabel("×"))
        size_row.addWidget(self.height_spin)
        size_row.addWidget(self.unit_combo)
        form.addRow("크기", size_row)

        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(30, 1200)
        self.dpi_spin.setValue(300)
        form.addRow("DPI", self.dpi_spin)

        self.format_combo = QComboBox()
        self.format_combo.addItems(["JPEG", "PNG", "WEBP"])
        form.addRow("파일형식", self.format_combo)

        self.quality_spin = QSpinBox()
        self.quality_spin.setRange(50, 100)
        self.quality_spin.setValue(95)
        form.addRow("품질", self.quality_spin)

        self.pixel_info = QLabel("")
        form.addRow("실제 출력", self.pixel_info)

        for widget in [
            self.width_spin,
            self.height_spin,
            self.unit_combo,
            self.dpi_spin,
            self.format_combo,
            self.quality_spin,
        ]:
            if isinstance(widget, QComboBox):
                widget.currentIndexChanged.connect(self.preview_from_ui)
            else:
                widget.valueChanged.connect(self.preview_from_ui)

        self.reload_presets()
        return box

    def _build_crop_box(self) -> QGroupBox:
        box = QGroupBox("재단 방식")
        form = QFormLayout(box)

        self.crop_combo = QComboBox()
        self.crop_combo.addItem("꽉 채우기", "fill")
        self.crop_combo.addItem("전체 유지", "fit")
        self.crop_combo.addItem("직접 재단", "custom")
        self.crop_combo.currentIndexChanged.connect(self.crop_mode_changed)
        form.addRow("방식", self.crop_combo)

        self.bg_btn = QPushButton("#FFFFFF")
        self.bg_btn.clicked.connect(self.choose_background)
        form.addRow("여백색", self.bg_btn)

        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(100, 800)
        self.zoom_slider.setValue(100)
        self.pan_x_slider = QSlider(Qt.Horizontal)
        self.pan_x_slider.setRange(-100, 100)
        self.pan_x_slider.setValue(0)
        self.pan_y_slider = QSlider(Qt.Horizontal)
        self.pan_y_slider.setRange(-100, 100)
        self.pan_y_slider.setValue(0)

        form.addRow("확대", self.zoom_slider)
        form.addRow("좌우 이동", self.pan_x_slider)
        form.addRow("상하 이동", self.pan_y_slider)

        for slider in (self.zoom_slider, self.pan_x_slider, self.pan_y_slider):
            slider.valueChanged.connect(self.preview_from_ui)

        rotate_row = QHBoxLayout()
        left = QPushButton("↶ 90°")
        right = QPushButton("↷ 90°")
        left.clicked.connect(lambda: self.rotate_current(-90))
        right.clicked.connect(lambda: self.rotate_current(90))
        rotate_row.addWidget(left)
        rotate_row.addWidget(right)
        form.addRow("회전", rotate_row)

        self.crop_mode_changed()
        return box

    def _apply_dark_style(self):
        self.setStyleSheet("""
            QMainWindow, QWidget { background:#111317; color:#e8eaed; font-size:13px; }
            QLabel#title { font-size:28px; font-weight:800; }
            QLabel#subtitle { color:#8b929e; }
            QLabel#preview { background:#090a0d; border:1px solid #2b2f36; border-radius:12px; }
            QGroupBox { border:1px solid #2b2f36; border-radius:10px; margin-top:10px; padding:12px; font-weight:700; }
            QGroupBox::title { subcontrol-origin: margin; left:10px; padding:0 5px; }
            QPushButton { background:#232833; border:1px solid #343b48; border-radius:8px; padding:9px 12px; }
            QPushButton:hover { background:#2d3442; }
            QPushButton#primary { background:#b3261e; border-color:#d03a30; font-weight:800; padding:13px; }
            QListWidget, QComboBox, QSpinBox, QDoubleSpinBox { background:#181b21; border:1px solid #303641; border-radius:7px; padding:6px; }
        """)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = [Path(url.toLocalFile()) for url in event.mimeData().urls()]
        self._add_paths(paths)

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "사진 추가",
            "",
            "Images (*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff)",
        )
        self._add_paths([Path(path) for path in files])

    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "사진 폴더 선택")
        if not folder:
            return
        paths = [
            path
            for path in Path(folder).iterdir()
            if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
        ]
        self._add_paths(sorted(paths))

    def _add_paths(self, paths: list[Path]):
        existing = {task.source_path.resolve() for task in self.tasks}
        for path in paths:
            if path.suffix.lower() not in SUPPORTED_SUFFIXES or not path.exists():
                continue
            if path.resolve() in existing:
                continue
            self.tasks.append(PhotoTask(path))
            self.list_widget.addItem(QListWidgetItem(path.name))
            existing.add(path.resolve())
        if self.tasks and self.current_index < 0:
            self.list_widget.setCurrentRow(0)

    def remove_selected(self):
        row = self.list_widget.currentRow()
        if row < 0:
            return
        self.tasks.pop(row)
        self.list_widget.takeItem(row)
        if self.tasks:
            self.list_widget.setCurrentRow(min(row, len(self.tasks) - 1))
        else:
            self.current_index = -1
            self.preview.setPixmap(QPixmap())
            self.preview.setText("사진을 추가하세요")

    def select_task(self, row: int):
        if not (0 <= row < len(self.tasks)):
            return
        self.current_index = row
        self.load_task_to_ui(self.tasks[row])
        self.refresh_preview()

    def reload_presets(self):
        category = self.category_combo.currentData()
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        for preset in self.preset_manager.presets(category):
            self.preset_combo.addItem(preset.name)
        self.preset_combo.blockSignals(False)
        if self.preset_combo.count():
            self.preset_combo.setCurrentIndex(0)
            self.load_selected_preset()

    def load_selected_preset(self):
        category = self.category_combo.currentData()
        preset = self.preset_manager.find(category, self.preset_combo.currentText())
        if not preset:
            return
        self._loading_ui = True
        self.width_spin.setValue(preset.width)
        self.height_spin.setValue(preset.height)
        self.unit_combo.setCurrentText(preset.unit)
        self.dpi_spin.setValue(preset.dpi)
        self._loading_ui = False
        self.preview_from_ui()

    def crop_mode_changed(self):
        custom = self.crop_combo.currentData() == "custom"
        fit = self.crop_combo.currentData() == "fit"
        self.zoom_slider.setEnabled(custom)
        self.pan_x_slider.setEnabled(custom)
        self.pan_y_slider.setEnabled(custom)
        self.bg_btn.setEnabled(fit)
        self.preview_from_ui()

    def choose_background(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.bg_btn.setText(color.name().upper())
            self.preview_from_ui()

    def ui_settings(self) -> OutputSettings:
        return OutputSettings(
            name=self.preset_combo.currentText() or "custom",
            width=self.width_spin.value(),
            height=self.height_spin.value(),
            unit=self.unit_combo.currentText(),
            dpi=self.dpi_spin.value(),
            crop_mode=self.crop_combo.currentData(),
            background=self.bg_btn.text(),
            output_format=self.format_combo.currentText(),
            quality=self.quality_spin.value(),
            zoom=self.zoom_slider.value() / 100.0,
            pan_x=self.pan_x_slider.value() / 100.0,
            pan_y=self.pan_y_slider.value() / 100.0,
        )

    def load_task_to_ui(self, task: PhotoTask):
        settings = task.settings
        self._loading_ui = True
        self.width_spin.setValue(settings.width)
        self.height_spin.setValue(settings.height)
        self.unit_combo.setCurrentText(settings.unit)
        self.dpi_spin.setValue(settings.dpi)
        self.format_combo.setCurrentText(settings.output_format)
        self.quality_spin.setValue(settings.quality)
        index = self.crop_combo.findData(settings.crop_mode)
        if index >= 0:
            self.crop_combo.setCurrentIndex(index)
        self.bg_btn.setText(settings.background)
        self.zoom_slider.setValue(round(settings.zoom * 100))
        self.pan_x_slider.setValue(round(settings.pan_x * 100))
        self.pan_y_slider.setValue(round(settings.pan_y * 100))
        self._loading_ui = False

    def preview_from_ui(self):
        if self._loading_ui:
            return
        if 0 <= self.current_index < len(self.tasks):
            self.refresh_preview(self.ui_settings())
        else:
            try:
                width, height = target_size(self.ui_settings())
                self.pixel_info.setText(f"{width} × {height} px")
            except Exception:
                pass

    def refresh_preview(self, settings: OutputSettings | None = None):
        if not (0 <= self.current_index < len(self.tasks)):
            return

        task = self.tasks[self.current_index]
        settings = settings or task.settings

        try:
            image = load_image(task.source_path, task.rotation)
            rendered = render_image(image, settings)
            preview = rendered.copy()
            preview.thumbnail((820, 700))
            qimage = ImageQt(preview.convert("RGBA"))
            pixmap = QPixmap.fromImage(qimage)
            self.preview.setText("")
            self.preview.setPixmap(pixmap)

            width, height = target_size(settings)
            self.pixel_info.setText(f"{width} × {height} px")
            self.info_label.setText(
                f"원본 {image.width}×{image.height}px  →  출력 {width}×{height}px"
            )
        except Exception as exc:
            self.preview.setPixmap(QPixmap())
            self.preview.setText(f"미리보기 오류\n{exc}")

    def apply_current(self):
        if 0 <= self.current_index < len(self.tasks):
            self.tasks[self.current_index].settings = self.ui_settings()
            self.refresh_preview()

    def apply_all(self):
        settings = self.ui_settings()
        for task in self.tasks:
            task.settings = settings.clone()
        self.refresh_preview()

    def rotate_current(self, delta: int):
        if 0 <= self.current_index < len(self.tasks):
            self.tasks[self.current_index].rotation = (
                self.tasks[self.current_index].rotation + delta
            ) % 360
            self.refresh_preview(self.ui_settings())

    def reset_current(self):
        if 0 <= self.current_index < len(self.tasks):
            self.tasks[self.current_index].settings = OutputSettings()
            self.tasks[self.current_index].rotation = 0
            self.load_task_to_ui(self.tasks[self.current_index])
            self.refresh_preview()

    def export_current(self):
        if not (0 <= self.current_index < len(self.tasks)):
            return

        task = self.tasks[self.current_index]
        task.settings = self.ui_settings()
        suggested = suggested_filename(task.source_path, task.settings)
        path, _ = QFileDialog.getSaveFileName(self, "현재 사진 저장", suggested)
        if not path:
            return

        try:
            image = load_image(task.source_path, task.rotation)
            rendered = render_image(image, task.settings)
            destination = ensure_extension(Path(path), task.settings.output_format)
            export_image(rendered, task.settings, destination)
        except Exception as exc:
            QMessageBox.critical(self, "저장 실패", str(exc))

    def export_all(self):
        if not self.tasks:
            return

        folder = QFileDialog.getExistingDirectory(self, "전체 저장 폴더 선택")
        if not folder:
            return

        if 0 <= self.current_index < len(self.tasks):
            self.tasks[self.current_index].settings = self.ui_settings()

        failures = []
        for task in self.tasks:
            try:
                image = load_image(task.source_path, task.rotation)
                rendered = render_image(image, task.settings)
                destination = unique_destination(
                    Path(folder),
                    suggested_filename(task.source_path, task.settings),
                )
                export_image(rendered, task.settings, destination)
            except Exception as exc:
                failures.append(f"{task.display_name}: {exc}")

        if failures:
            QMessageBox.warning(self, "일부 저장 실패", "\n".join(failures[:10]))
        else:
            QMessageBox.information(self, "완료", f"{len(self.tasks)}장 저장 완료")
