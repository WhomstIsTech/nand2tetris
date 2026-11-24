// This file is part of www.nand2tetris.org
// and the book "The Elements of Computing Systems"
// by Nisan and Schocken, MIT Press.
// File name: projects/4/Mult.asm

// Multiplies R0 and R1 and stores the result in R2.
// (R0, R1, R2 refer to RAM[0], RAM[1], and RAM[2], respectively.)
// The algorithm is based on repetitive addition.

//// Replace this comment with your code.


    // Clear out R2
    @R2
    M=0

(LOOP)
    // Check if R1 is zero
    @R1
    D = M
    @END
    D; JEQ

    // Then add R0 to R2 if we're still going
    @R0
    D = M
    @R2
    M=M + D

    // Then remove 1 from R1 and jump back to the top of the loop
    @R1
    M = M - 1

    @LOOP
    0; JMP
(END)