# Flutter hardcodes CC/CXX to Clang, so select the SDK's GCC before compiler detection.
set(CMAKE_C_COMPILER /usr/bin/gcc)
set(CMAKE_CXX_COMPILER /usr/bin/g++)
