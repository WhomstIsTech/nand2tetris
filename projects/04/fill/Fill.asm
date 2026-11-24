// This file is part of www.nand2tetris.org
// and the book "The Elements of Computing Systems"
// by Nisan and Schocken, MIT Press.
// File name: projects/4/Fill.asm

// Runs an infinite loop that listens to the keyboard input. 
// When a key is pressed (any key), the program blackens the screen,
// i.e. writes "black" in every pixel. When no key is pressed, 
// the screen should be cleared.

//// Replace this comment with your code.


    // Clear out R0, use this for current pixel
    @8192
    D=A
    @R0
    M=D

    // Set R1 to color value
    @R1
    M=0

    // Clear R2 for screen location
    @SCREEN
    D=A
    @R2
    M=D

(LOOP)
    // Check if keyboard is presssed. If not, jump to White
    @KBD
    D = M
    @WHITE
    D; JEQ

(BLACK)
    // Set the color we want to change to black
    @R1
    M=-1

    @SETUP
    0; JMP

(WHITE)
    // Set the color we want to change to white
    @R1
    M=0

(SETUP)
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
    @R1
    D=M // Grabbing Color
    @R2
    A=M // Set address
    M=D // Write color to address

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