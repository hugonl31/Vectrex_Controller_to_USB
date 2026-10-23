/* Host model validates the actual reader against all native DAC codes. */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#define VIA_port_a 1
#define VIA_port_b 0
static int currentPortA, currentYSH, dac, enabled, selected, reads;
static double input;
static void put(int address, unsigned int value)
{
    if (address==VIA_port_a) dac=(int8_t)value;
    else { selected=value&6; enabled=!(value&1); }
}
static int get(int address)
{
    assert(address==VIA_port_b && !enabled);
    ++reads;
    return dac<=input ? 0x20 : 0;
}
#define I_SET(a,v) put(a,v)
#define I_GET(a) get(a)
#define ADD_DELAY_CYCLES(c) ((void)(c))
#define DELAY_PORT_B_BEFORE_PORT_A() ((void)0)
#include "native_adc.h"
int main(void)
{
    for (unsigned int mux=0; mux<=2; mux+=2) {
        for (int value=-128; value<=127; ++value) {
            input=value+0.25;
            reads=0;
            assert(read_axis(mux)==value);
            assert(reads==8 && selected==(int)mux);
            assert(currentPortA==0x100 && currentYSH==0x100);
        }
    }
    input=-200; assert(read_axis(0)==-128);
    input=200; assert(read_axis(2)==127);
    puts("PASS: 512 DAC-code cases, both mux channels, rail saturation, cache invalidation");
}
