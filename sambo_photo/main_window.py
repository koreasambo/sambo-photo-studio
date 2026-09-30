from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw
from PIL.ImageQt import ImageQt
from PySide6.QtCore import Qt, QSize, QThread, Signal
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
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .background_engine import create_auto_mask, mask_from_png, mask_to_png, review_mask
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
from .mask_editor import MaskEditor
from .models import OutputSettings, PhotoTask
from .presets import PresetManager


APP_TITLE = "삼보사진관"
CATEGORY_LABELS = {
    "ratio": "비율",
    "id_photo": "증명/여권형",
    "print": "인화",
    "frame": "액자",
}


class BackgroundRemovalThread(QThread):
    done = Signal(bytes, str, str)
    failed = Signal(str)

    def __init__(self, source_path: Path, rotation: int):
        super().__init__()
        self.source_path = source_path
        self.rotation = rotation

    def run(self):
        try:
            image = load_image(self.source_path, self.rotation)
            mask = create_auto_mask(image)
            status, reasons = review_mask(mask)
            self.done.emit(mask_to_png(mask), status, ", ".join(reasons))
        except Exception as exc:
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self, preset_dir: Path):
        super().__init__()
        self.setWindowTitle(f"{APP_TITLE} 0.2")
        self.resize(1540, 940)
        self.setAcceptDrops(True)

        self.tasks: list[PhotoTask] = []
        self.current_index = -1
        self.preset_manager = PresetManager(preset_dir)
        self._loading_ui = False
        self.bg_thread: BackgroundRemovalThread | None = None

        self._build_ui()
        self._apply_dark_style()

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)

        header = QHBoxLayout()
        title = QLabel("삼보사진관")
        title.setObjectName("title")
        subtitle = QLabel("사진은 그대로, 규격은 정확하게.  ·  V0.2 비파괴 누끼")
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
        self.tabs = QTabWidget()

        self.output_preview = QLabel("사진을 추가하세요")
        self.output_preview.setAlignment(Qt.AlignCenter)
        self.output_preview.setMinimumSize(QSize(620, 600))
        self.output_preview.setObjectName("preview")
        self.tabs.addTab(self.output_preview, "출력 미리보기")

        mask_page = QWidget()
        mask_layout = QVBoxLayout(mask_page)
        mask_toolbar = QHBoxLayout()
        mask_toolbar.addWidget(QLabel("누끼 보기"))
        self.mask_view_combo = QComboBox()
        self.mask_view_combo.addItem("결과", "result")
        self.mask_view_combo.addItem("원본", "original")
        self.mask_view_combo.addItem("마스크", "mask")
        self.mask_view_combo.currentIndexChanged.connect(lambda: self.refresh_mask_editor())
        mask_toolbar.addWidget(self.mask_view_combo)
        mask_toolbar.addStretch()
        mask_layout.addLayout(mask_toolbar)

        self.mask_editor = MaskEditor()
        self.mask_editor.maskChanged.connect(self.on_mask_edited)
        mask_layout.addWidget(self.mask_editor, 1)
        self.tabs.addTab(mask_page, "누끼 편집")

        center_layout.addWidget(self.tabs, 1)
        self.info_label = QLabel("")
        self.info_label.setAlignment(Qt.AlignCenter)
        center_layout.addWidget(self.info_label)
        splitter.addWidget(center)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(self._build_output_box())
        right_layout.addWidget(self._build_crop_box())
        right_layout.addWidget(self._build_background_box())
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

        splitter.setSizes([270, 850, 420])

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

    def _build_background_box(self) -> QGroupBox:
        box = QGroupBox("누끼 / 배경 · 비파괴")
        form = QFormLayout(box)

        self.auto_mask_btn = QPushButton("자동 누끼 초안 만들기")
        self.auto_mask_btn.clicked.connect(self.run_auto_mask)
        form.addRow(self.auto_mask_btn)

        self.mask_status = QLabel("미실행")
        self.mask_status.setWordWrap(True)
        form.addRow("상태", self.mask_status)

        self.background_mode_combo = QComboBox()
        self.background_mode_combo.addItem("원본 배경", "original")
        self.background_mode_combo.addItem("투명 배경", "transparent")
        self.background_mode_combo.addItem("색상 배경", "color")
        self.background_mode_combo.currentIndexChanged.connect(self.background_mode_changed)
        form.addRow("배경", self.background_mode_combo)

        self.background_color_btn = QPushButton("#FFFFFF")
        self.background_color_btn.clicked.connect(self.choose_subject_background)
        form.addRow("배경색", self.background_color_btn)

        self.brush_mode_combo = QComboBox()
        self.brush_mode_combo.addItem("복구 브러시", "restore")
        self.brush_mode_combo.addItem("제거 브러시", "erase")
        self.brush_mode_combo.currentIndexChanged.connect(self.update_brush)
        form.addRow("브러시", self.brush_mode_combo)

        self.brush_size_slider = QSlider(Qt.Horizontal)
        self.brush_size_slider.setRange(5, 180)
        self.brush_size_slider.setValue(40)
        self.brush_size_slider.valueChanged.connect(self.update_brush)
        form.addRow("브러시 크기", self.brush_size_slider)

        confirm = QPushButton("누끼 확정")
        confirm.clicked.connect(self.confirm_mask)
        reset = QPushButton("원본으로 되돌리기")
        reset.clicked.connect(self.reset_mask)
        row = QHBoxLayout()
        row.addWidget(confirm)
        row.addWidget(reset)
        form.addRow(row)

        note = QLabel("자동 결과는 초안입니다. 브러시 보정 후 ‘누끼 확정’을 눌러야 배경 제거 결과를 저장할 수 있습니다. 첫 자동 누끼 실행 때 소형 모델 다운로드가 필요할 수 있습니다.")
        note.setWordWrap(True)
        note.setObjectName("hint")
        form.addRow(note)

        self.update_brush()
        self.background_mode_changed()
        return box

    def _apply_dark_style(self):
        self.setStyleSheet("""
            QMainWindow, QWidget { background:#111317; color:#e8eaed; font-size:13px; }
            QLabel#title { font-size:28px; font-weight:800; }
            QLabel#subtitle, QLabel#hint { color:#8b929e; }
            QLabel#preview { background:#090a0d; border:1px solid #2b2f36; border-radius:12px; }
            QGroupBox { border:1px solid #2b2f36; border-radius:10px; margin-top:10px; padding:12px; font-weight:700; }
            QGroupBox::title { subcontrol-origin: margin; left:10px; padding:0 5px; }
            QPushButton { background:#232833; border:1px solid #343b48; border-radius:8px; padding:9px 12px; }
            QPushButton:hover { background:#2d3442; }
            QPushButton#primary { background:#b3261e; border-color:#d03a30; font-weight:800; padding:13px; }
            QListWidget, QComboBox, QSpinBox, QDoubleSpinBox, QTabWidget::pane {
                background:#181b21; border:1px solid #303641; border-radius:7px; padding:6px;
            }
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
            self.output_preview.setPixmap(QPixmap())
            self.output_preview.setText("사진을 추가하세요")
            self.mask_editor.set_document(None, None)

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

    def choose_subject_background(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.background_color_btn.setText(color.name().upper())
            if 0 <= self.current_index < len(self.tasks):
                self.tasks[self.current_index].background_color = self.background_color_btn.text()
            self.refresh_preview()

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
        bg_index = self.background_mode_combo.findData(task.background_mode)
        if bg_index >= 0:
            self.background_mode_combo.setCurrentIndex(bg_index)
        self.background_color_btn.setText(task.background_color)
        self.mask_status.setText(task.mask_status)
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

    def _screen_preview(self, image: Image.Image) -> QPixmap:
        rgba = image.convert("RGBA")
        if rgba.getextrema()[3] != (255, 255):
            bg = Image.new("RGBA", rgba.size, (225, 225, 225, 255))
            draw = ImageDraw.Draw(bg)
            tile = max(8, min(rgba.size) // 30)
            for y in range(0, rgba.height, tile):
                for x in range(0, rgba.width, tile):
                    if ((x // tile) + (y // tile)) % 2:
                        draw.rectangle((x, y, x + tile, y + tile), fill=(195, 195, 195, 255))
            bg.alpha_composite(rgba)
            rgba = bg

        preview = rgba.copy()
        preview.thumbnail((830, 700), Image.Resampling.LANCZOS)
        return QPixmap.fromImage(ImageQt(preview))

    def refresh_preview(self, settings: OutputSettings | None = None):
        if not (0 <= self.current_index < len(self.tasks)):
            return
        task = self.tasks[self.current_index]
        settings = settings or task.settings

        try:
            image = load_image(task.source_path, task.rotation)
            mask = mask_from_png(task.mask_png)
            rendered = render_image(
                image,
                settings,
                mask=mask,
                background_mode=task.background_mode,
                background_color=task.background_color,
            )
            self.output_preview.setText("")
            self.output_preview.setPixmap(self._screen_preview(rendered))

            width, height = target_size(settings)
            self.pixel_info.setText(f"{width} × {height} px")
            self.info_label.setText(
                f"원본 {image.width}×{image.height}px  →  출력 {width}×{height}px  ·  누끼 {task.mask_status}"
            )
            self.refresh_mask_editor(image, mask)
        except Exception as exc:
            self.output_preview.setPixmap(QPixmap())
            self.output_preview.setText(f"미리보기 오류\n{exc}")

    def refresh_mask_editor(self, image=None, mask=None):
        if not (0 <= self.current_index < len(self.tasks)):
            return
        task = self.tasks[self.current_index]
        try:
            image = image or load_image(task.source_path, task.rotation)
            mask = mask if mask is not None else mask_from_png(task.mask_png)
            self.mask_editor.set_document(
                image,
                mask,
                view_mode=self.mask_view_combo.currentData() or "result",
                background_mode=task.background_mode,
                background_color=task.background_color,
            )
        except Exception:
            pass

    def update_brush(self):
        if not hasattr(self, "mask_editor"):
            return
        mode = self.brush_mode_combo.currentData() if hasattr(self, "brush_mode_combo") else "restore"
        size = self.brush_size_slider.value() if hasattr(self, "brush_size_slider") else 40
        self.mask_editor.set_brush(mode or "restore", size)

    def background_mode_changed(self):
        if not hasattr(self, "background_mode_combo"):
            return
        mode = self.background_mode_combo.currentData()
        if hasattr(self, "background_color_btn"):
            self.background_color_btn.setEnabled(mode == "color")
        if self._loading_ui:
            return
        if 0 <= self.current_index < len(self.tasks):
            task = self.tasks[self.current_index]
            task.background_mode = mode
            task.background_color = self.background_color_btn.text()
            if mode == "transparent" and hasattr(self, "format_combo"):
                self.format_combo.setCurrentText("PNG")
            self.refresh_preview()

    def run_auto_mask(self):
        if not (0 <= self.current_index < len(self.tasks)):
            return
        if self.bg_thread and self.bg_thread.isRunning():
            return

        task = self.tasks[self.current_index]
        self.auto_mask_btn.setEnabled(False)
        self.auto_mask_btn.setText("자동 누끼 분석 중…")
        self.mask_status.setText("분석 중")
        self.bg_thread = BackgroundRemovalThread(task.source_path, task.rotation)
        self.bg_thread.done.connect(self.auto_mask_done)
        self.bg_thread.failed.connect(self.auto_mask_failed)
        self.bg_thread.finished.connect(self.auto_mask_finished)
        self.bg_thread.start()

    def auto_mask_done(self, mask_png: bytes, status: str, reasons: str):
        if not (0 <= self.current_index < len(self.tasks)):
            return
        task = self.tasks[self.current_index]
        task.mask_png = mask_png
        task.mask_status = f"{status}" + (f" · {reasons}" if reasons else "")
        task.background_mode = "transparent"
        self.mask_status.setText(task.mask_status)
        self.background_mode_combo.setCurrentIndex(self.background_mode_combo.findData("transparent"))
        self.format_combo.setCurrentText("PNG")
        self.tabs.setCurrentIndex(1)
        self.refresh_preview()

    def auto_mask_failed(self, message: str):
        self.mask_status.setText("실패")
        QMessageBox.critical(self, "자동 누끼 실패", message)

    def auto_mask_finished(self):
        self.auto_mask_btn.setEnabled(True)
        self.auto_mask_btn.setText("자동 누끼 초안 만들기")

    def on_mask_edited(self, data: bytes):
        if not (0 <= self.current_index < len(self.tasks)):
            return
        task = self.tasks[self.current_index]
        task.mask_png = data
        task.mask_status = "수정됨 · 재확인 필요"
        self.mask_status.setText(task.mask_status)
        self.refresh_preview()

    def confirm_mask(self):
        if not (0 <= self.current_index < len(self.tasks)):
            return
        task = self.tasks[self.current_index]
        if not task.mask_png:
            QMessageBox.information(self, "누끼 없음", "먼저 자동 누끼 초안을 만들거나 마스크를 준비하세요.")
            return
        task.mask_status = "확정"
        self.mask_status.setText("확정")
        self.refresh_preview()

    def reset_mask(self):
        if not (0 <= self.current_index < len(self.tasks)):
            return
        task = self.tasks[self.current_index]
        task.mask_png = None
        task.mask_status = "미실행"
        task.background_mode = "original"
        self.mask_status.setText(task.mask_status)
        self.background_mode_combo.setCurrentIndex(self.background_mode_combo.findData("original"))
        self.refresh_preview()

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
            task = self.tasks[self.current_index]
            task.rotation = (task.rotation + delta) % 360
            if task.mask_png:
                task.mask_png = None
                task.mask_status = "회전으로 누끼 초기화됨"
                task.background_mode = "original"
                self.mask_status.setText(task.mask_status)
                self.background_mode_combo.setCurrentIndex(self.background_mode_combo.findData("original"))
            self.refresh_preview(self.ui_settings())

    def reset_current(self):
        if 0 <= self.current_index < len(self.tasks):
            task = self.tasks[self.current_index]
            task.settings = OutputSettings()
            task.rotation = 0
            task.mask_png = None
            task.mask_status = "미실행"
            task.background_mode = "original"
            task.background_color = "#FFFFFF"
            self.load_task_to_ui(task)
            self.refresh_preview()

    def _validate_mask_for_export(self, task: PhotoTask) -> bool:
        if task.background_mode == "original":
            return True
        if not task.mask_png:
            QMessageBox.warning(self, "누끼 필요", f"{task.display_name}: 배경제거 마스크가 없습니다.")
            return False
        if task.mask_status != "확정":
            QMessageBox.warning(
                self,
                "누끼 확인 필요",
                f"{task.display_name}: 자동/수정 누끼는 아직 확정되지 않았습니다.\n누끼 편집 탭에서 확인 후 ‘누끼 확정’을 눌러주세요.",
            )
            return False
        return True

    def _render_task(self, task: PhotoTask):
        image = load_image(task.source_path, task.rotation)
        mask = mask_from_png(task.mask_png)
        return render_image(
            image,
            task.settings,
            mask=mask,
            background_mode=task.background_mode,
            background_color=task.background_color,
        )

    def export_current(self):
        if not (0 <= self.current_index < len(self.tasks)):
            return
        task = self.tasks[self.current_index]
        task.settings = self.ui_settings()
        if not self._validate_mask_for_export(task):
            return

        suggested = suggested_filename(task.source_path, task.settings)
        path, _ = QFileDialog.getSaveFileName(self, "현재 사진 저장", suggested)
        if not path:
            return

        try:
            rendered = self._render_task(task)
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
            if task.background_mode != "original" and (not task.mask_png or task.mask_status != "확정"):
                failures.append(f"{task.display_name}: 누끼 미확정")
                continue
            try:
                rendered = self._render_task(task)
                destination = unique_destination(
                    Path(folder),
                    suggested_filename(task.source_path, task.settings),
                )
                export_image(rendered, task.settings, destination)
            except Exception as exc:
                failures.append(f"{task.display_name}: {exc}")

        if failures:
            QMessageBox.warning(self, "일부 저장 보류/실패", "\n".join(failures[:12]))
        else:
            QMessageBox.information(self, "완료", f"{len(self.tasks)}장 저장 완료")
