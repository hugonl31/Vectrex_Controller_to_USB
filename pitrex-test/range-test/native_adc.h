#ifndef NATIVE_ADC_H
#define NATIVE_ADC_H
/* Physical VIA multiplexer/DAC/comparator successive approximation.
 * Backend IO and timing macros come from vectrexInterface.h. */
static int read_axis(unsigned int mux)
{
    uint8_t code = 0, bit = 0x80;
    I_SET(VIA_port_a, 0);
    ADD_DELAY_CYCLES(4);
    I_SET(VIA_port_b, 0x80 | mux);
    ADD_DELAY_CYCLES(60);
    I_SET(VIA_port_b, 0x81 | mux);
    DELAY_PORT_B_BEFORE_PORT_A();
    do {
        I_SET(VIA_port_a, code);
        ADD_DELAY_CYCLES(4);
        if (!(I_GET(VIA_port_b) & 0x20)) code ^= bit;
        ADD_DELAY_CYCLES(4);
        bit >>= 1;
        code |= bit;
    } while (bit);
    currentPortA = currentYSH = 0x100;
    return (int8_t)code;
}
#endif
