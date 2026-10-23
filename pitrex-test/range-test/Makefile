BUILD_FOR ?= zero1
BASE_DIR = ../upstream
TARGET = controller-test.img
LOADER = yes
include ../upstream/Rules.mk

$(BUILD_DIR)controller_test.o: controller_test.c native_adc.h
	$(CC) $(CFLAGS) -Wall -Wextra -c $< -o $@

controller-test.img: $(BUILD_DIR)controller_test.o $(LIBS_CHECK)
	$(CC) $(CFLAGS) -Wl,-N,-Map,$(BUILD_DIR)controller-test.map -o $(BUILD_DIR)controller-test.elf $(BUILD_DIR)controller_test.o $(LIBS)
	arm-none-eabi-objcopy $(BUILD_DIR)controller-test.elf -O binary $@
