# -*- mode: python ; coding: utf-8 -*-
# Echelon PyInstaller spec — rebuilt from scratch
# Key design decisions:
#   - VC++ runtime DLLs are EXCLUDED (installed separately via vc_redist.x64.exe)
#   - Full collection of insightface, onnxruntime, albumentations, cv2
#   - console=False (no terminal window)
#   - All assets, data dirs, model dirs included at correct relative paths

import sys
from pathlib import Path

# ── VC++ Runtime DLLs to EXCLUDE from bundle ──────────────────────────────
# These are installed by the official vc_redist.x64.exe in the NSIS installer.
# Bundling them causes conflicts with Windows system copies.
VC_RUNTIME_DLLS = [
    'VCRUNTIME140.dll', 'vcruntime140.dll',
    'VCRUNTIME140_1.dll', 'vcruntime140_1.dll',
    'MSVCP140.dll', 'msvcp140.dll',
    'MSVCP140_1.dll', 'msvcp140_1.dll',
    'MSVCP140_2.dll', 'msvcp140_2.dll',
    'VCOMP140.dll', 'vcomp140.dll',
    'CONCRT140.dll', 'concrt140.dll',
    'VCCORLIB140.dll', 'vccorlib140.dll',
]


def filter_binaries(binaries):
    """Remove VC++ runtime DLLs from the binary list."""
    filtered = []
    for name, dest, kind in binaries:
        dll_name = Path(name).name
        if dll_name.upper() in [d.upper() for d in VC_RUNTIME_DLLS]:
            continue
        filtered.append((name, dest, kind))
    return filtered


a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        # UI assets
        ('assets/styles/theme.qss', 'assets/styles'),
        ('assets/icons',            'assets/icons'),
        # Data dirs (empty but must exist at runtime)
        ('data',                    'data'),
    ],
    hiddenimports=[
        # PyQt6
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.sip',
        # OpenCV
        'cv2',
        'cv2.dnn',
        # NumPy
        'numpy',
        'numpy.core._multiarray_umath',
        'numpy.testing',
        'numpy.testing._private',
        # ONNX Runtime
        'onnxruntime',
        'onnxruntime.capi._pybind_state',
        # ONNX (model loading)
        'onnx',
        'onnx.numpy_helper',
        # InsightFace
        'insightface',
        'insightface.app',
        'insightface.app.face_analysis',
        'insightface.app.mask_renderer',
        'insightface.model_zoo',
        'insightface.model_zoo.model_zoo',
        'insightface.thirdparty',
        'insightface.thirdparty.face3d',
        'insightface.thirdparty.face3d.mesh',
        'insightface.thirdparty.face3d.mesh.vis',
        'insightface.utils',
        'insightface.utils.face_align',
        # Albumentations
        'albumentations',
        'albumentations.augmentations',
        # Matplotlib (headless — MPLBACKEND=Agg)
        'matplotlib',
        'matplotlib.pyplot',
        'matplotlib.colors',
        'matplotlib.cm',
        'matplotlib.patches',
        'matplotlib.backends',
        'matplotlib.backends.backend_agg',
        # PIL / Pillow
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        'PIL.ImageFont',
        # Scipy
        'scipy',
        'scipy.spatial',
        'scipy.spatial.distance',
        'scipy.special',
        'scipy._lib',
        # Scikit-learn
        'sklearn',
        'sklearn.metrics',
        'sklearn.metrics.pairwise',
        # System libs
        'psutil',
        'requests',
        'requests.adapters',
        'requests.packages',
        'tqdm',
        'pyvirtualcam',
        'sounddevice',
        'socketio',
        'engineio',
        'websocket',
        # Unittest (pulled in by numpy/scipy internals)
        'unittest',
        'unittest.mock',
        'unittest.case',
        # Windows registry (for hardware detection on Windows)
        'winreg' if sys.platform == 'win32' else 'posixpath',
    ],
    # Collect full packages that have C extensions or data files scattered around
    collect_all=[
        'insightface',
        'onnxruntime',
        'albumentations',
        'cv2',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        # No GUI toolkit other than Qt
        'tkinter',
        '_tkinter',
        # Heavy unused onnxruntime components
        'onnxruntime.quantization',
        'onnxruntime.transformers',
        'onnxruntime.training',
        'onnx.reference',
        # Jupyter / IPython bloat
        'IPython',
        'jupyter',
        'notebook',
        # Compilation tools not needed at runtime
        'Cython',
        'sympy',
        'pytest',
        'setuptools',
    ],
    noarchive=False,
)

# ── Filter out VC++ runtime DLLs after analysis ──────────────────────────
a.binaries = filter_binaries(a.binaries)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DarkArmy',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,           # No terminal window in release build
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icons/darkarmy.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='DarkArmy',
)
