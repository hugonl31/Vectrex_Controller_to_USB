; Standard 6809 cartridge. On a real cartridge, BIOS Joy_Analog reads
; the console DAC/comparator directly. PiTrex interception is conditional.
        org $0000
        fcc "g GCE 2026"
        fcb $80
        fdb QuietTune
        fcb $F1,$60,$30,$A0
        fcc "CONTROLLER TEST"
        fcb $80,0
        jmp Start
QuietTune:
        fdb $FEE8,$FEB6
        fcb $00,$80

LiveX   equ $C880
LiveY   equ $C881
MinX    equ $C882
MaxX    equ $C883
MinY    equ $C884
MaxY    equ $C885
CenterX equ $C886
CenterY equ $C887
Frozen  equ $C888
Armed   equ $C889
Buffer  equ $C890
WaitRecal equ $F192
Buttons equ $F1BA
Analog  equ $F1F5
Intensity equ $F2AB
Print   equ $F37A

Start:
        lds #$CBEA
        lda #$D0
        tfr a,dp
        setdp $D0
        ldx #LiveX
        ldb #10
Clear:  clr ,x+
        decb
        bne Clear
        clr >$C81A
        lda #1
        sta >$C81F
        lda #3
        sta >$C820
        clr >$C821
        clr >$C822
        lda #-8
        sta >$C82A
        lda #$45
        sta >$C82B
Loop:
        jsr WaitRecal
        jsr Analog
        lda >$C81B
        sta >LiveX
        lda >$C81C
        sta >LiveY
        jsr Buttons
        tst >Armed
        bne Handle
        tst >$C80F
        bne Capture
        inc >Armed
Handle:
        lda >$C811
        bita #1
        beq NoReset
        lda >LiveX
        sta >MinX
        sta >MaxX
        lda >LiveY
        sta >MinY
        sta >MaxY
NoReset:
        lda >$C811
        bita #2
        beq NoCenter
        lda >LiveX
        sta >CenterX
        lda >LiveY
        sta >CenterY
NoCenter:
        lda >$C811
        bita #8
        beq Capture
        lda >Frozen
        eora #1
        sta >Frozen
Capture:
        tst >Frozen
        bne Display
        lda >LiveX
        cmpa >MinX
        bge NoMinX
        sta >MinX
NoMinX:
        cmpa >MaxX
        ble NoMaxX
        sta >MaxX
NoMaxX:
        lda >LiveY
        cmpa >MinY
        bge NoMinY
        sta >MinY
NoMinY:
        cmpa >MaxY
        ble Display
        sta >MaxY
Display:
        jsr $F354               ; zero after joystick/button IO before first text
        lda #$60
        jsr Intensity
        ldu #Title
        ldd #$60A0
        jsr Print
        ldu #Port
        ldd #$4AA0
        jsr Print

        ldx #Buffer
        ldu #XPrefix
        jsr Append
        lda >LiveX
        jsr Number
        ldu #MinLabel
        jsr Append
        lda >MinX
        jsr Number
        ldu #MaxLabel
        jsr Append
        lda >MaxX
        jsr Number
        lda #$80
        sta ,x
        ldu #Buffer
        ldd #$2DA0
        jsr Print

        ldx #Buffer
        ldu #YPrefix
        jsr Append
        lda >LiveY
        jsr Number
        ldu #MinLabel
        jsr Append
        lda >MinY
        jsr Number
        ldu #MaxLabel
        jsr Append
        lda >MaxY
        jsr Number
        lda #$80
        sta ,x
        ldu #Buffer
        ldd #$10A0
        jsr Print

        ldu #Target
        ldd #$F3A0
        jsr Print
        ldu #PiLimit
        ldd #$DDA0
        jsr Print

        ldx #Buffer
        ldu #CenterLabel
        jsr Append
        lda >CenterX
        jsr Number
        lda #' '
        sta ,x+
        lda >CenterY
        jsr Number
        lda #$80
        sta ,x
        ldu #Buffer
        ldd #$C0A0
        jsr Print
        ldu #Controls
        ldd #$A9A0
        jsr Print
        ldu #Running
        tst >Frozen
        beq ShowState
        ldu #Stopped
ShowState:
        ldd #$92A0
        jsr Print
        lbra Loop

; Append high-bit-terminated ASCII, excluding terminator; X advances.
Append:
        lda ,u+
        bmi DoneAppend
        sta ,x+
        bra Append
DoneAppend:
        rts
; Signed byte A to exactly four ASCII characters (+000 through -128).
Number:
        pshs b
        tsta
        bpl Positive
        ldb #'-'
        nega
        bra Sign
Positive:
        ldb #'+'
Sign:   stb ,x+
        clrb
Hundreds:
        cmpa #100
        blo HundredDone
        suba #100
        incb
        bra Hundreds
HundredDone:
        addb #'0'
        stb ,x+
        clrb
Tens:   cmpa #10
        blo TenDone
        suba #10
        incb
        bra Tens
TenDone:
        addb #'0'
        stb ,x+
        adda #'0'
        sta ,x+
        puls b,pc

Title:  fcc "CONTROLLER RANGE TEST"
        fcb $80
Port:   fcc "AXIS LIVE / MIN / MAX"
        fcb $80
XPrefix:fcc "X "
        fcb $80
YPrefix:fcc "Y "
        fcb $80
MinLabel:fcc " "
        fcb $80
MaxLabel:fcc " "
        fcb $80
Target: fcc "NATIVE -128 TO +127"
        fcb $80
PiLimit:
        ifdef REAL_CART
        fcc "REAL CART - PORT ONE"
        else
        fcc "PITREX +126 IS NORMAL"
        endc
        fcb $80
CenterLabel:fcc "CENTER X/Y "
        fcb $80
Controls:fcc "1 RESET  2 CENTER"
        fcb $80
Running:fcc "4 FREEZE - RECORDING"
        fcb $80
Stopped:fcc "4 RESUME - FROZEN"
        fcb $80
        fill $FF,$8000-*
