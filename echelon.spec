# -*- mode: python ; coding: utf-8 -*-

app_name = 'Echelon'

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('assets/styles/theme.qss', 'assets/styles'),
        ('assets/icons', 'assets/icons'),
    ],
    hiddenimports=[
        # PyQt6
        'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets', 'PyQt6.sip',
        # OpenCV
        'cv2', 'cv2.dnn',
        # NumPy
        'numpy', 'numpy.core._multiarray_umath',
        # ONNX Runtime
        'onnxruntime', 'onnxruntime.capi._pybind_state',
        # InsightFace
        'insightface', 'insightface.app', 'insightface.app.face_analysis',
        'insightface.app.mask_renderer',
        'insightface.model_zoo', 'insightface.model_zoo.model_zoo',
        'insightface.thirdparty', 'insightface.thirdparty.face3d',
        'insightface.thirdparty.face3d.mesh',
        'insightface.thirdparty.face3d.mesh.vis',
        'insightface.utils', 'insightface.utils.face_align',
        # Albumentations (pulled in by insightface)
        'albumentations', 'albumentations.augmentations',
        # Matplotlib (headless)
        'matplotlib', 'matplotlib.pyplot', 'matplotlib.colors',
        'matplotlib.cm', 'matplotlib.patches',
        'matplotlib.backends', 'matplotlib.backends.backend_agg',
        # PIL
        'PIL', 'PIL.Image', 'PIL.ImageDraw', 'PIL.ImageFont',
        # Scipy
        'scipy', 'scipy.spatial', 'scipy.spatial.distance',
        'scipy.special', 'scipy._lib', 'scipy._lib._array_api',
        'scipy._lib.array_api_compat',
        'scipy._lib.array_api_compat.numpy',
        'scipy._lib.array_api_compat._internal',
        # Unittest (needed by numpy/scipy internals)
        'unittest', 'unittest.mock', 'unittest.case',
        'numpy.testing', 'numpy.testing._private',
        # System
        'psutil', 'requests', 'tqdm', 'pyvirtualcam',
        'sklearn', 'sklearn.metrics', 'sklearn.metrics.pairwise',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=['tkinter', '_tkinter'],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name=app_name,
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon='assets/icons/echelon.ico',
)

coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=False,
    name=app_name,
)
