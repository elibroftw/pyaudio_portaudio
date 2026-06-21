"""PyAudio: Cross-platform audio I/O with PortAudio.

PyAudio provides Python bindings for PortAudio, the cross-platform audio I/O
library. With PyAudio, you can easily use Python to play and record audio on a
variety of platforms, such as GNU/Linux, Microsoft Windows, and Apple macOS.

PyAudio is distributed under the MIT License:

Copyright (c) 2006 Hubert Pham

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import os
import logging
import sysconfig
import platform
from pathlib import Path
from setuptools import setup, Extension
import sys

__version__ = '0.2.12'

# setup.py/setuptools will try to locate and link dynamically against portaudio,
# except on Windows. On Windows, setup.py will attempt to statically link in
# portaudio, since most users will install PyAudio from pre-compiled wheels.
# Optionally specify the environment variable PORTAUDIO_PATH with the build tree of PortAudio.

# not using VCPKG because we forked portaudio to support loopback
portaudio_path = Path(os.environ.get('PORTAUDIO_PATH', 'portaudio-v19'))
MAC_SYSROOT_PATH = os.environ.get('SYSROOT_PATH', None)
WIN_VCPKG_PATH = os.environ.get('VCPKG_PATH', None)

data_files = []  # for dynamic libraries


def setup_extension():
    pyaudio_module_sources = [
        'src/pyaudio/_portaudiomodule.c',
        'src/pyaudio/device_api.c',
        'src/pyaudio/host_api.c',
        'src/pyaudio/mac_core_stream_info.c',
    ]
    include_dirs = ['portaudio-v19/include']
    external_libraries = ['portaudio']
    external_libraries_path = []
    extra_compile_args = []
    extra_link_args = []
    defines = []

    if sys.platform == 'darwin':
        # Support only dynamic linking with portaudio, since the supported path
        # is to install portaudio using a package manager (e.g., Homebrew).
        # TODO: let users pass in location of portaudio library on command line.
        defines += [('MACOSX', '1')]

        include_dirs += ['/usr/local/include', '/usr/include', '/opt/homebrew/include']
        external_libraries_path += [
            path
            for path in ('/usr/local/lib', '/usr/lib', '/opt/homebrew/lib')
            if os.path.exists(path)
        ]

        if MAC_SYSROOT_PATH:
            extra_compile_args += ['-isysroot', MAC_SYSROOT_PATH]
            extra_link_args += ['-isysroot', MAC_SYSROOT_PATH]
    elif sys.platform == 'win32':
        # Only supports statically linking with portaudio, since the typical
        # way users install PyAudio on win32 is through pre-compiled wheels.
        bits = platform.architecture()[0]
        if '64' in bits:
            defines.append(('MS_WIN64', '1'))

        if WIN_VCPKG_PATH:
            include_dirs += [os.path.join(WIN_VCPKG_PATH, 'include')]
            external_libraries_path = [os.path.join(WIN_VCPKG_PATH, 'lib')]
        else:
            # portaudio fork MSVC build
            portaudio_shared = get_portaudio_lib()
            extra_link_args.append(str(portaudio_shared))
            lib_path = os.path.dirname(portaudio_shared)
            external_libraries_path = [lib_path]
            include_dirs = [os.path.join(portaudio_path, 'include/')]
            data_files.append(
                (r'Lib\site-packages', [os.path.join(lib_path, 'portaudio.dll')])
            )
            external_libraries += ['winmm', 'ole32', 'uuid']
            # disable Buffer Security Checks
            extra_link_args.append('/GS-')
        # For static linking, use MT flag to match both vcpkg's portaudio and
        # the standard portaudio cmake settings. For details, see:
        # https://devblogs.microsoft.com/cppblog/vcpkg-updates-static-linking-is-now-available/
        extra_compile_args += ['/MT']

        # The static portaudio lib does not include user32 and advapi32, so
        # those need to be linked manually.
        external_libraries += ['user32', 'Advapi32']
    else:
        # GNU/Linux and other posix-like OSes will dynamically link to
        # portaudio, installed by the package manager.
        include_dirs += ['/usr/local/include', '/usr/include']
        external_libraries_path += ['/usr/local/lib', '/usr/lib']

    return Extension(
        'pyaudio._portaudio',
        sources=pyaudio_module_sources,
        include_dirs=include_dirs,
        define_macros=defines,
        libraries=external_libraries,
        extra_compile_args=extra_compile_args,
        extra_link_args=extra_link_args,
        library_dirs=external_libraries_path,
    )


def get_portaudio_lib():
    WIN_ARCH_DIRS = {
        'win32': 'Win32',
        'win-amd64': 'x64',
        'win-arm64': 'ARM64',
    }
    arch_dir = WIN_ARCH_DIRS.get(sysconfig.get_platform())
    if arch_dir is None:
        raise RuntimeError(
            f'Unsupported Windows target platform {sysconfig.get_platform()!r}; '
            f'expected one of {sorted(WIN_ARCH_DIRS)}.'
        )
    path_to_lib = portaudio_path / 'build/msvc' / arch_dir / 'ReleaseDLL/portaudio.lib'
    assert path_to_lib.is_file(), (
        f'[{arch_dir}] Expected portaudio.lib at {path_to_lib} does not exist.'
    )
    return path_to_lib


with open('README.md', 'r') as fh:
    long_description = fh.read()


setup(
    name='PyAudio',
    version=__version__,
    author='Hubert Pham',
    url='https://people.csail.mit.edu/hubert/pyaudio/',
    description='Cross-platform audio I/O with PortAudio',
    long_description=long_description,
    long_description_content_type='text/markdown',
    license='MIT',
    scripts=[],
    packages=['pyaudio'],
    package_dir={'': 'src'},
    ext_modules=[setup_extension()],
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Topic :: Multimedia :: Sound/Audio',
    ],
    data_files=data_files,
)
