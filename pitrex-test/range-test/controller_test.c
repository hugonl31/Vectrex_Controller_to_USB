/* Physical Vectrex input test. No joystick calibration, filter or rescaling.
 * The successive-approximation sequence follows PiTrex inputDevice.c, but
 * deliberately bypasses its smoothing and all USB/controller remapping.
 */
#include <stdio.h>
#include <stdint.h>
#include <vectrex/vectrexInterface.h>
#include <baremetal/pitrexio-gpio.h>
#include <baremetal/ff.h>

#include "native_adc.h"

/* Small startup breadcrumb file helps locate a hardware hang. No controller
 * samples are written. SD IO finishes before continuous measurement begins. */
static void status(char *message, int reset)
{
    FIL file;
    UINT written;
    if (f_open(&file, "joytest-status.txt", FA_WRITE | (reset ? FA_CREATE_ALWAYS : FA_OPEN_ALWAYS)) != FR_OK) return;
    if (!reset) f_lseek(&file, f_size(&file));
    f_write(&file, message, strlen(message), &written);
    f_close(&file);
}

static void text(int y, char *line)
{
    v_printString(-110, y, line, 5, 65);
}

static void marker(int x, int y, int brightness)
{
    v_directDraw32(x-450, y, x+450, y, brightness);
    v_directDraw32(x, y-450, x, y+450, brightness);
}

int main(int argc, char **argv)
{
    (void)argc; (void)argv;
    /* Preserve loader memory so the menu/reset return path remains valid. */
    status("MAIN ENTERED\r\n", 1);
    int hardware = vectrexinit(1);
    status(hardware == 1 ? "GPIO/VIA INITIALIZED\r\n" : "GPIO/HALT ERROR\r\n", 0);
    v_init();
    status("V_INIT COMPLETE\r\n", 0);
    v_setRefresh(50);
    v_enableJoystickAnalog(0, 0, 0, 0);
    v_enableJoystickDigital(0, 0, 0, 0);
    irqJoyAnalog = irqJoyDigital = 0;
    swapPorts = 0;
    useUSB = 0;
    logOutput = 0;
    /* Use the same synchronous pipeline path as the upstream hello example.
     * Show a startup screen before any custom analog read is attempted. */
    bufferType = 0;
    usePipeline = 1;
    for (int frame=0; frame<100; ++frame) {
        v_WaitRecal();
        v_directDraw32(-10000,-10000,-10000,10000,64);
        v_directDraw32(-10000,10000,10000,10000,64);
        v_directDraw32(10000,10000,10000,-10000,64);
        v_directDraw32(10000,-10000,-10000,-10000,64);
        v_printString(-75,20,"CONTROLLER TEST",5,64);
        v_printString(-65,-10,"STARTING",5,64);
    }
    status("DISPLAY LOOP COMPLETE - STARTING RAW READS\r\n", 0);
    int xmin=127, xmax=-128, ymin=127, ymax=-128;
    int cx=0, cy=0, frozen=0, previous=0;
    int left=0, right=0, up=0, down=0;
    char line[64];
    for (;;) {
        v_WaitRecal();
        int buttons = v_directReadButtons() & 15;
        int x = read_axis(0), y = read_axis(2);
        static int first_read = 1;
        if (first_read) { status("RAW X/Y READS COMPLETE\r\n", 0); first_read=0; }
        int pressed = buttons & ~previous;
        previous = buttons;
        if (pressed & 1) {
            xmin=xmax=x; ymin=ymax=y;
            left=right=up=down=0;
        }
        if (pressed & 2) { cx=x; cy=y; }
        if (pressed & 8) frozen = !frozen;
        if (!frozen) {
            if (x<xmin) xmin=x;
            if (x>xmax) xmax=x;
            if (y<ymin) ymin=y;
            if (y>ymax) ymax=y;
            /* Require ten consecutive rail samples (0.2 s), not a spike. */
            left  = x==-128 ? left+1  : left>=10 ? left : 0;
            right = x==127  ? right+1 : right>=10 ? right : 0;
            down  = y==-128 ? down+1  : down>=10 ? down : 0;
            up    = y==127  ? up+1   : up>=10 ? up : 0;
        }
        text(112, "NATIVE CONTROLLER TEST");
        text(99, "PORT 1 - RAW DAC UNITS");
        snprintf(line,sizeof line,"LIVE X %4d  Y %4d",x,y); text(85,line);
        snprintf(line,sizeof line,"X MIN %4d MAX %4d",xmin,xmax); text(71,line);
        snprintf(line,sizeof line,"Y MIN %4d MAX %4d",ymin,ymax); text(57,line);
        text(43, "TARGET MIN -128 MAX 127");
        snprintf(line,sizeof line,"RAILS L%c R%c U%c D%c",left>=10?'*':'-',right>=10?'*':'-',up>=10?'*':'-',down>=10?'*':'-'); text(29,line);
        /* Shared fixed full-scale frame. Never fit the plot to observed travel. */
        int top=2200, bottom=-10000, lo=-9000, hi=9000;
        v_directDraw32(lo,bottom,hi,bottom,45);
        v_directDraw32(hi,bottom,hi,top,45);
        v_directDraw32(hi,top,lo,top,45);
        v_directDraw32(lo,top,lo,bottom,45);
        int px=lo+(x+128)*(hi-lo)/255;
        int py=bottom+(y+128)*(top-bottom)/255;
        v_directDraw32(0,bottom,0,top,25);
        v_directDraw32(lo,(bottom+top)/2,hi,(bottom+top)/2,25);
        marker(px,py,75);
        snprintf(line,sizeof line,"CENTER X %4d Y %4d",cx,cy); text(-90,line);
        text(-103,"1 RESET   2 SET CENTER");
        text(-116,frozen?"4 RESUME - PEAKS FROZEN":"4 FREEZE - PEAKS RUNNING");
    }
}
