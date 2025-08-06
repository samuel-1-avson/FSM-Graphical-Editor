# bsm_designer.spec
# -*- mode: python ; coding: utf-8 -*-

import os
import sys

block_cipher = None

# --- Platform-specific binary for the C++ Core Engine ---
# NOTE: This assumes you have compiled the C++ core engine.
# It looks for the compiled shared library (.dll, .so, .dylib) in the build directory.
core_engine_binary = []
core_engine_build_dir = os.path.join('fsm_designer_project', 'core_engine', 'build')

if sys.platform.startswith('win'):
    lib_name = 'fsm_core.dll'
elif sys.platform.startswith('darwin'):
    lib_name = 'libfsm_core.dylib'
else: # Linux
    lib_name = 'libfsm_core.so'

binary_path = os.path.join(core_engine_build_dir, lib_name)
if os.path.exists(binary_path):
    # The second part of the tuple is the destination directory in the bundle.
    # '.' places it in the root, next to the executable.
    core_engine_binary = [(binary_path, '.')]
else:
    print(f"WARNING: Compiled core engine binary not found at '{binary_path}'. C Simulation will fail.")


a = Analysis(['fsm_designer_project/main.py'],
             pathex=['.'], # Look for imports in the project root
             binaries=core_engine_binary, # Add the compiled C++ library
             datas=[
                 # Essential application assets (JSON data and Jinja templates)
                 ('fsm_designer_project/assets/data', 'fsm_designer_project/assets/data'),
                 ('fsm_designer_project/assets/templates', 'fsm_designer_project/assets/templates'),
                 # Documentation, examples, and icons
                 ('fsm_designer_project/docs', 'bsm_designer_project/docs'),
                 ('fsm_designer_project/examples', 'bsm_designer_project/examples'),
                 ('fsm_designer_project/dependencies/icons', 'bsm_designer_project/dependencies/icons')
             ],
             hiddenimports=[
                 'pygraphviz',
                 'pyqtgraph',
                 # AI Provider libraries are loaded dynamically, so PyInstaller needs to be told about them
                 'google.generativeai',
                 'openai',
                 'anthropic',
                 'groq',
                 'httpx'
             ],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='BSM_Designer',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False, # Set to False for a GUI application
          icon='fsm_designer_project/dependencies/icons/app_icon.ico'
          )# bsm_designer.spec
# -*- mode: python ; coding: utf-8 -*-

import os
import sys

block_cipher = None

# --- Platform-specific binary for the C++ Core Engine ---
# NOTE: This assumes you have compiled the C++ core engine.
# It looks for the compiled shared library (.dll, .so, .dylib) in the build directory.
core_engine_binary = []
core_engine_build_dir = os.path.join('fsm_designer_project', 'core_engine', 'build')

if sys.platform.startswith('win'):
    lib_name = 'fsm_core.dll'
elif sys.platform.startswith('darwin'):
    lib_name = 'libfsm_core.dylib'
else: # Linux
    lib_name = 'libfsm_core.so'

binary_path = os.path.join(core_engine_build_dir, lib_name)
if os.path.exists(binary_path):
    # The second part of the tuple is the destination directory in the bundle.
    # '.' places it in the root, next to the executable.
    core_engine_binary = [(binary_path, '.')]
else:
    print(f"WARNING: Compiled core engine binary not found at '{binary_path}'. C Simulation will fail.")


a = Analysis(['fsm_designer_project/main.py'],
             pathex=['.'], # Look for imports in the project root
             binaries=core_engine_binary, # Add the compiled C++ library
             datas=[
                 # Essential application assets (JSON data and Jinja templates)
                 ('fsm_designer_project/assets/data', 'fsm_designer_project/assets/data'),
                 ('fsm_designer_project/assets/templates', 'fsm_designer_project/assets/templates'),
                 # Documentation, examples, and icons
                 ('fsm_designer_project/docs', 'bsm_designer_project/docs'),
                 ('fsm_designer_project/examples', 'bsm_designer_project/examples'),
                 ('fsm_designer_project/dependencies/icons', 'bsm_designer_project/dependencies/icons')
             ],
             hiddenimports=[
                 'pygraphviz',
                 'pyqtgraph',
                 # AI Provider libraries are loaded dynamically, so PyInstaller needs to be told about them
                 'google.generativeai',
                 'openai',
                 'anthropic',
                 'groq',
                 'httpx'
             ],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='BSM_Designer',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False, # Set to False for a GUI application
          icon='fsm_designer_project/dependencies/icons/app_icon.ico'
          )