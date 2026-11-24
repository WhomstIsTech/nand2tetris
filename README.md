# nand2tetris

All work related to working with nand2tetris, organized in order of chapter. This repository documents my implementations from *The Elements of Computing Systems*, where each project builds another part of a working computer system—from elementary logic gates through a compiler for the Jack programming language.

## Repository layout

The work is organized under `projects/` in the order completed. Source code, supplied test scripts, and comparison files are included so the implementations can be reviewed with the nand2tetris tools. Generated outputs and the downloaded course platform are intentionally excluded.

| Folder | Focus | What it covers |
| --- | --- | --- |
| `00` | HDL setup | A short introductory HDL exercise used to verify the hardware-simulator workflow. |
| `01` | Elementary logic gates | NAND-based Boolean logic, including multiplexers, demultiplexers, and 16-bit gate variants. |
| `02` | Boolean arithmetic | Arithmetic chips such as adders, an incrementer, and the Hack ALU. |
| `03` | Sequential logic | Clocked memory components, registers, program counter logic, and RAM hierarchies up to 16K. |
| `04` | Machine language | Hack assembly programs for multiplication and screen filling, including an intermediate static-fill exercise. |
| `05` | Computer architecture | CPU, memory, and computer-level HDL integration for the Hack platform. |
| `05-5` | Course exercise | Supporting files and an additional course-specific exercise between the architecture and assembler work. |
| `06` | Assembler | A Python Hack assembler (`hasm.py`) that resolves symbols and translates Hack assembly into machine code. |
| `07` | VM translator I | A Python virtual-machine translator (`hvm.py`) for stack arithmetic and memory-access commands. |
| `08` | VM translator II | Extends the VM translator with branching, functions, calls, returns, and bootstrap handling. |
| `09` | Jack programs | Jack-language programs and games, including Pong and a custom paddle-and-ball project. |
| `10` | Compiler I | The first Jack compiler stage (`hjc.py`): tokenization and syntax analysis with XML output. |
| `11` | Compiler II | Extends the Jack compiler to generate VM code, then validates it with the supplied Jack programs. |

## Tools written for this work

- `projects/06/hasm.py` — Hack assembler
- `projects/07/hvm.py` and `projects/08/hvm.py` — Hack VM translator
- `projects/10/hjc.py` and `projects/11/hjc.py` — Hack Jack compiler

## Credit

This work follows the [nand2tetris](https://www.nand2tetris.org/) curriculum created by Noam Nisan and Shimon Schocken and is based on their book, *The Elements of Computing Systems*. The project ideas, hardware/software platform, specifications, and supplied test materials belong to nand2tetris. The implementations and course work in this repository are my own unless a file notes otherwise.

## Running the work

Use the official [nand2tetris software suite](https://www.nand2tetris.org/software) to run the HDL, Hack assembly, VM, and Jack projects. The Python tools accept a source file or directory from the command line; their built-in help is available with `--help`.

