// This file is part of www.nand2tetris.org
// and the book "The Elements of Computing Systems"
// by Nisan and Schocken, MIT Press.
// File name: projects/04/FillStatic.asm

// Blackens the screen, i.e. writes "black" in every pixel. 
// Key presses are ignored.
// This is an intermediate step added to help you out.

// Put your code here.

(LOOP)

    // Clear out R0, use this for current pixel
    @8192
    D=A
    @R0
    M=D

    // Clear R2 for screen location
    @SCREEN
    D=A
    @R2
    M=D

(FILL)
    // Grab color value and screen location to that value
    @R2
    A=M // Set address
    M=-1 // Write color to address

    // Increment address for Screen
    @R2
    M=M+1
    
    // Decrement pixel count
    @R0
    M=M-1
    D=M

    // Check if we have gone through all the pixels
    @FILL
    D;JGT

    // If we don't jump, then we are done and loop
    @LOOP
    0; JMP