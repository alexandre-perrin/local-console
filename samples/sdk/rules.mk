WASI_SDK_PATH ?= /opt/wasi-sdk
CC = $(WASI_SDK_PATH)/bin/clang
CXX = $(WASI_SDK_PATH)/bin/clang++

# References about WASM linear memory handling by WAMR:
# - https://bytecodealliance.github.io/wamr.dev/blog/the-wamr-memory-model/
# - https://bytecodealliance.github.io/wamr.dev/blog/understand-the-wamr-stacks/
# - https://github.com/bytecodealliance/wasm-micro-runtime/blob/main/doc/build_wasm_app.md#1-wasi-sdk-options
# - https://github.com/bytecodealliance/wasm-micro-runtime/blob/main/doc/memory_tune.md
MODULE_MAX_LINEAR_MEM_KB = 128
MODULE_AUX_STACK_KB = 32

PROJ_LDFLAGS = \
	-Wl,-allow-undefined \
	-z stack-size=$$(( $(MODULE_AUX_STACK_KB) * 1024 )) \
	-Wl,--max-memory=$$(( $(MODULE_MAX_LINEAR_MEM_KB) * 1024 )) \
	-Wl,--export=malloc -Wl,--export=free \
	-Wl,--export=__data_end -Wl,--export=__heap_base

BINDIR = ../bin

CFLAGS ?=
CINCLUDES += \
	-I$(PROJECTDIR)/sdk/include
PROJ_CFLAGS = \
	$(CFLAGS) \
	$(CINCLUDES)

CXXFLAGS = \
	$(CFLAGS)
CXXINCLUDES = \
	$(CINCLUDES)
PROJ_CXXFLAGS = \
	$(CXXFLAGS) \
	$(CXXINCLUDES)

all:

FORCE:

.SUFFIXES: .c .o .cpp

.c.o:
	$(CC) $(PROJ_CFLAGS) -c $<

.cpp.o:
	$(CXX) $(PROJ_CXXFLAGS) -c $<

$(DIRS): FORCE
	+@cd $@ && $(MAKE)

clean: clean-dirs

clean-dirs:
	@+set -e;\
	for i in $(DIRS);\
	do\
		cd $$i;\
		$(MAKE) clean;\
		cd -;\
	done
