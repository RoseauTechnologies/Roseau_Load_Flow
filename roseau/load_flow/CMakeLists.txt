file(GLOB_RECURSE src "*.hpp" "*.cpp")
list(FILTER src EXCLUDE REGEX ".*/cy_.*$")

add_library(lib_thunders ${src})
