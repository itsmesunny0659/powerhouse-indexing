cmake_minimum_required(VERSION 3.15)
project(ApexSearchEngine VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include_directories(include)

add_executable(apex_engine
    src/main.cpp
)

if (MSVC)
    target_compile_options(apex_engine PRIVATE /W4 /O2)
else()
    target_compile_options(apex_engine PRIVATE -Wall -Wextra -O3 -pthread)
endif()

