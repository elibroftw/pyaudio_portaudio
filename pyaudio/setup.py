"""
PyAudio v0.2.11: Python Bindings for PortAudio.

Copyright (c) 2006 Hubert Pham

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY
OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT
LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS
OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE
USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import os
import platform
import sys
import sysconfig
from pathlib import Path
import logging

from setuptools import setup, Extension


__version__ = "0.2.14"

# setup.py/setuptools will try to locate and link dynamically against portaudio,
# except on Windows. On Windows, setup.py will attempt to statically link in
# portaudio, since most users will install PyAudio from pre-compiled wheels.
# Optionally specify the environment variable PORTAUDIO_PATH with the build tree of PortAudio.

STATIC_LINKING = sys.platform == 'win32'

portaudio_path = Path(os.environ.get('PORTAUDIO_PATH', 'portaudio-v19'))
mac_sysroot_path = os.environ.get('SYSROOT_PATH', None)

pyaudio_module_sources = ['src/_portaudiomodule.c']
include_dirs = ['portaudio-v19/include']
external_libraries = []
extra_compile_args = []
extra_link_args = []
scripts = []
defines = []
data_files = []  # for dynamic libraries
is_64bit = sys.maxsize > 2**32

if sys.platform == 'win32':
    if is_64bit:
        defines.append(('MS_WIN64', '1'))
elif sys.platform == 'darwin':  # mac
    defines += [('MACOSX', '1')]
    if mac_sysroot_path:
        extra_compile_args += ['-isysroot', mac_sysroot_path]
        extra_link_args += ['-isysroot', mac_sysroot_path]


WIN_ARCH_DIRS = {
    'win32': 'Win32',
    'win-amd64': 'x64',
    'win-arm64': 'ARM64',
}

# check if we are running in a cygwin environment. if not we assume a native windows library in the msvc release path
arch_dir = WIN_ARCH_DIRS.get(sysconfig.get_platform())
if 'ORIGINAL_PATH' in os.environ and 'cygdrive' in os.environ['ORIGINAL_PATH']:
    portaudio_shared = portaudio_path.joinpath('lib/.libs/libportaudio.a')
else:
    if arch_dir is None:
        raise RuntimeError(
            f"Unsupported Windows target platform {sysconfig.get_platform()!r}; "
            f"expected one of {sorted(WIN_ARCH_DIRS)}."
        )
    portaudio_shared = portaudio_path.joinpath(
        f'build/msvc/{arch_dir}/ReleaseDLL/portaudio.lib')

if STATIC_LINKING and not portaudio_shared.exists():
    raise FileNotFoundError(
        f"PortAudio library not found at {portaudio_shared}. "
        f"Build PortAudio for this architecture first "
        f"(msbuild ... /p:Platform={arch_dir} /p:Configuration=ReleaseDLL).")
extra_link_args.append(str(portaudio_shared))

external_libraries.append('portaudio')
library_dirs = []
lib_path = os.path.join(portaudio_path, f'build/msvc/{arch_dir}/ReleaseDLL')
if not STATIC_LINKING:
    data_files.append(('', [os.path.join(lib_path, 'portaudio.dll')]))
else:
    library_dirs.append(lib_path)
    include_dirs = [os.path.join(portaudio_path, 'include/')]
    data_files.append((r'Lib\site-packages', [os.path.join(lib_path, 'portaudio.dll')]))
    # platform specific configuration
    if sys.platform == 'win32':
        # i.e., Win32 Python with mingw32
        # run: python setup.py build -cmingw32
        if 'ORIGINAL_PATH' in os.environ and 'cygdrive' in os.environ['ORIGINAL_PATH']:
            external_libraries += ['winmm', 'ole32', 'uuid']
            extra_link_args += ['-lwinmm', '-lole32', '-luuid']
        else:
            # MSVC
            # TODO: external_libraries += ["user32", "Advapi32"]?
            external_libraries += ['winmm', 'ole32', 'uuid', 'advapi32', 'user32']
            # extra_link_args.append('/NODEFAULTLIB:MSVCRT')
            # disable Buffer Security Checks
            extra_link_args.append('/GS-')
            # extra_link_args.append('/MT')
    elif sys.platform == 'darwin':
        extra_link_args += ['-framework', 'CoreAudio',
                            '-framework', 'AudioToolbox',
                            '-framework', 'AudioUnit',
                            '-framework', 'Carbon']
    elif sys.platform == 'cygwin':
        external_libraries += ["winmm", "ole32", "uuid"]
        extra_link_args += ["-lwinmm", "-lole32", "-luuid"]
    elif sys.platform == 'linux2':
        extra_link_args += ['-lrt', '-lm', '-lpthread']
        # GNU/Linux has several audio systems (backends) available; be
        # sure to specify the desired ones here.  Start with ALSA and
        # JACK, since that's common today.
        extra_link_args += ['-lasound', '-ljack']
setup(name='PyAudio',
      version=__version__,
      author='Hubert Pham',
      url='http://people.csail.mit.edu/hubert/pyaudio/',
      description='Cross-platform audio I/O with PortAudio',
      long_description=__doc__.lstrip(),
      license='MIT',
      scripts=scripts,
      py_modules=['pyaudio'],
      package_dir={'': 'src'},
      ext_modules=[
          Extension('_portaudio',
                    sources=pyaudio_module_sources,
                    include_dirs=include_dirs,
                    define_macros=defines,
                    libraries=external_libraries,
                    library_dirs=library_dirs,
                    extra_compile_args=extra_compile_args,
                    extra_link_args=extra_link_args)
      ], data_files=data_files)
