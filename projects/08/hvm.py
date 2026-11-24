'''
Hack Virtual Machine Translator

Memory Map Reminder:
RAM address   Typical contents
-----------   -------------------------------------------
0-15           fixed registers (SP, LCL, ARG, THIS, THAT, temp (5-12), R13-R15 (scratchpad))
16-255         static variables
256-2047       stack (starts here)
2048-16383     other RAM stuff
16384-...      screen, keyboard-mapped I/O

This module translates Hack VM commands into Hack assembly code. Can handle both single .vm files and directories of .vm files.

Author: James Giffen
Date: 11/3/2025
'''

import os
import argparse
from typing import List

# Set up parsing for command line arguments
parser = argparse.ArgumentParser(prog="hvm", description="Hack Virtual Machine Translator")
parser.add_argument("filename", help="Path to the .vm file/directory to be translated", type=str)
parser.add_argument("-o", "--output", help="Path to the output .asm file", default=None, type=str)
parser.add_argument("--debug", help="Enable debug mode", action="store_true")
parser.add_argument("-n", "--no-bootstrap", help="Do not include bootstrap code", action="store_true", default=False)

# Set up current directory
cwd = os.getcwd()

# ----------------------------- VM Structures -----------------------------
ARITH = {"add","sub","neg","eq","gt","lt","and","or","not"}

SEGMENT_BASE = {
    "local": "LCL",
    "argument": "ARG",
    "this": "THIS",
    "that": "THAT"
}

TEMP_START = 5
TEMP_END = 12 # Used for error handling

POINTER_MAP = {0: "THIS", 1: "THAT"}

COMMAND_TYPES = {
    "C_ARITHMETIC",
    "C_PUSH",
    "C_POP",
    "C_LABEL",
    "C_GOTO",
    "C_IF",
    "C_FUNCTION",
    "C_RETURN",
    "C_CALL",
    "CHANGE_FILE",
    "C_INIT"
}

# ----------------------------- Command Class -----------------------------
class Command:
    def __init__(self, command_type: str, arg1: str, arg2: int | None):
        # The idea here is to have a simple structure to hold parsed commands to be used by the CodeWriter
        self.ctype = command_type
        self.arg1 = arg1
        self.arg2 = arg2

# --------------------------- CodeWriter Class ----------------------------
class CodeWriter:
    def __init__(self, commands: List[Command], debug: bool = False):
        
        self.functionName = "null"  # Current function name for label scoping
        self.file_name = None  # Input file name for static variables
        
        self.label_counter = 0   # Unique label counter this is incremented for each label
        self.debug = debug # Enable debug prints (if needed)
        
        self.commands = commands # List of Command objects to translate
        self.asm_lines = [] # List of CodeWriter's output lines
        self.call_counts = {} # Track number of calls to each function for unique return labels
    
    def __len__(self):
        return len(self.asm_lines)
    
    def setFileName(self, file: str):
        self.file_name = os.path.splitext(file)[0]
        self.setFunctionName("null")  # Reset function name when file changes
        
    def setFunctionName(self, functionName: str):
        functionName = functionName.split('.')[-1]
        functionName = f"{self.file_name}.{functionName}"
        if functionName not in self.call_counts:
            self.call_counts[functionName] = 0
        self.functionName = functionName
    
    def close(self):
        lines = self.asm_lines
        self.asm_lines = []
        return lines

    def write(self, lines: list[str]):
        self.asm_lines.extend(lines)
    
    # ---- Stack operation helpers ----
    def pushD(self):
        '''
        Push the value in D register onto the stack. The SP always points to the next free slot, 
        so we store D at *SP and then increment SP.
        '''
        self.write(["@SP",      # Get the stack pointer
                    "A=M",      # Go to the top of the stack
                    "M=D",      # Store D at top of stack
                    "@SP",      # Increment SP
                    "M=M+1"])
        
    def popD(self):
        '''
        Pop the value from the stack into the D register. The SP always points to the next free slot,
        so we decrement SP and store *SP into D.
        '''
        self.write(["@SP",   # Get the stack pointer
                    "M=M-1", # Decrement SP
                    "A=M",   # Go to the top of the stack
                    "D=M"])  # Store value into D
        
    # ---- Arithmetic commands ----
    def writeArithmetic(self, operation: str):
        '''
        Wrapper function for handling arithmetic operations: add, sub, neg, eq, gt, lt, and, or, not.
        '''
        if operation in ("add", "sub", "and", "or"):
            self._two_operand(operation)
        elif operation in ("neg", "not"):
            self._one_operand(operation)
        elif operation in ("eq", "gt", "lt"):
            self._comparison(operation)
        else:
            raise ValueError(f"Unknown arithmetic operation: {operation}")
    
    def _two_operand(self, operation: str):
        self.popD() # Pop the first value off the stack into D
        
        # Go to the second value on the stack (where we will perform the operation)
        self.write(["@SP", 
                    "M=M-1",
                    "A=M"])
        
        # Check which operation to perform
        if operation == "add":
            self.write(["M=D+M"]) 
        elif operation == "sub":
            self.write(["M=M-D"])
        elif operation == "and":
            self.write(["M=D&M"])
        elif operation == "or":
            self.write(["M=D|M"])
        
        # Finally, increment SP to reflect the new top of stack  
        self.write(["@SP",
                    "M=M+1"])
    
    def _one_operand(self, operation: str):
        # Go to the top of the stack
        self.write(["@SP",
                    "M=M-1",
                    "A=M"])
        
        if operation == "neg":
            self.write(["M=-M"])
        elif operation == "not":
            self.write(["M=!M"])
            
        # Increment stack pointer again
        self.write(["@SP",
                    "M=M+1"])

    def _comparison(self, operation: str):
        self.popD() # Pop the second operand off the stack into D
        
        # Go to the first operand on the stack and subtract the second from it. Then store result to D
        self.write(["@SP", 
                    "M=M-1",
                    "A=M",
                    "D=M-D"])
        
        # Generate unique labels for TRUE and END
        true_label = f"{self.file_name}_TRUE{self.label_counter}"
        end_label = f"{self.file_name}_END{self.label_counter}"
        self.label_counter += 1
        
        jmp_translation = {
            "eq": "JEQ",
            "gt": "JGT",
            "lt": "JLT"
        }
        
        self.write([f"@{true_label}",                      # Get ready to jump to TRUE label
                    f"D;{jmp_translation[operation]}",     # Jump to TRUE label if condition met otherwise continue
                    "@SP",                                 # Grab current stack pointer
                    "A=M",                                 # Go to top of stack
                    "M=0",                                 # Set value false (0) because we didn't jump
                    f"@{end_label}",                       # Get ready to jump to END label
                    "0;JMP",                               # Jump to END label
                    f"({true_label})",                     # TRUE label
                    "@SP",                                 # Grab current stack pointer
                    "A=M",                                 # Go to top of stack
                    "M=-1",                                # Set to true (-1) because we did jump
                    f"({end_label})",                      # END label
                    "@SP",                                 # Finally, increment SP to reflect new top of stack
                    "M=M+1"])
    
    # ---- Push/Pop commands ----
    def writePushPop(self, command_type: str, arg1: str, arg2: int | None): # Done this way to match Command class. Can think of it as (command, segment, index) as well
        '''
        Wrapper function for handling push and pop commands.
        '''
        if command_type == "C_PUSH":
            self._push(arg1, arg2)
        elif command_type == "C_POP":
            self._pop(arg1, arg2)
        else:
            raise ValueError(f"Unknown command type: {command_type}")
        
    def _push(self, segment: str, index):
        if segment == "constant":
            # Put the constant in A and then D
            self.write([f"@{index}",
                        "D=A"])
            # Push D onto the stack
            self.pushD()
            
        elif segment in SEGMENT_BASE:
            # Translate segment to its base
            base = SEGMENT_BASE[segment]
            
            # Get the value at segment base + index into D
            self.write([f"@{base}",      # Get starting address of segment
                        "D=M",           # D = base address
                        f"@{index}",     # Get index
                        "A=D+A",         # A = base + index
                        "D=M"])          # D = value at that address
            
            # Push D onto the stack
            self.pushD()
            
        elif segment == "temp":
            # Calculate the absolute address of the temp segment
            base = TEMP_START + index
            if base > TEMP_END:
                raise ValueError(f"Temp segment index out of bounds: {index}")
            
            # Get the value at temp base into D
            self.write([f"@{base}",
                        "D=M"])
            
            # Push D onto the stack
            self.pushD()
            
        elif segment == "pointer":
            try:
                # Get the pointer address
                pointer = POINTER_MAP[index]
                
                # Get the value at pointer into D
                self.write([f"@{pointer}",
                            "D=M"])
                
                # Push D onto the stack
                self.pushD()
            except KeyError:
                raise ValueError(f"Pointer segment index out of bounds: {index}") # Only 0 and 1 are valid
            
        elif segment == "static":
            # Grab the variable from filename.index into D
            self.write([f"@{self.file_name}.{index}",
                        "D=M"])
            
            # Push D onto the stack
            self.pushD()
        else:
            raise ValueError(f"Unknown argument: {segment}")
    
    def _pop(self, segment: str, index):
        if segment in SEGMENT_BASE:
            # Translate segment to its base
            base = SEGMENT_BASE[segment]
            
            # Get the value at segment base + index into R13 for temporary storage
            self.write([f"@{base}",     # Get starting address of segment
                        "D=M",          # D = base address
                        f"@{index}",    # Get index
                        "D=D+A",        # D = base + index
                        "@R13",         # Use R13 as a temporary storage
                        "M=D"])         # Store the address in R13
            
            # Pop the top of the stack into D
            self.popD()
            
            # Store D into the address stored in R13
            self.write(["@R13",
                        "A=M",
                        "M=D"])
            
        elif segment == "temp":
            # Calculate the absolute address of the temp segment
            base = TEMP_START + index
            if base > TEMP_END:
                raise ValueError(f"Temp segment index out of bounds: {index}")
            
            # Pop the top of the stack into D
            self.popD()
            
            # Get the value at temp base into D
            self.write([f"@{base}",
                        "M=D"])
            
        elif segment == "pointer":
            try:
                # Get the pointer address
                pointer = POINTER_MAP[index]
                
                # Pop the top of the stack into D
                self.popD()
                
                # Put the value from D into the pointer segment
                self.write([f"@{pointer}",
                            "M=D"])
                
            except KeyError:
                raise ValueError(f"Pointer segment index out of bounds: {index}") # Only 0 and 1 are valid
            
        elif segment == "static":
            # Pop the top of the stack into D
            self.popD()
            
            # Put D into filename.index address
            self.write([f"@{self.file_name}.{index}",
                        "M=D"])
            
        else:
            raise ValueError(f"Unknown argument: {segment}")
    
    # ---- Label commands ----
    def writeLabel(self, label: str):
        self.write([f"({self.functionName}${label})"]) # Label format is (file_name.functionName$label)
    
    # ---- Goto commands ----
    def writeGoto(self, label: str):
        # Label format is (file_name.functionName$label) and then we jump to it unconditionally
        self.write([f"@{self.functionName}${label}",
                     "0;JMP"])

    # ---- If-goto commands ----
    def writeIf(self, label: str):
        self.popD() # Get the top of the stack into D
        # Label format is (file_name.functionName$label) and then we jump to it if D != 0
        self.write([f"@{self.functionName}${label}",
                     "D;JNE"])

    # ---- Function commands ----
    def writeFunction(self, name: str, n_vars: int | None):
        if n_vars is None:
            n_vars = 0
            
        # Declare the function (the name gets scoped when parsing)
        self.write([f"({name})"])
        
        # Save the function name for label scope
        self.setFunctionName(name)
        
        # Initialize all local variables required to 0
        for _ in range(n_vars):
            self.write(["@0",
                        "D=A"])
            self.pushD()
        
    # ---- Call commands ----
    def writeCall(self, name: str, n_args: int | None):
        if n_args is None:
            n_args = 0
        
        # Create the return label and push onto stack
        if name not in self.call_counts:
            self.call_counts[name] = 0
            
        return_label = f"{name}$ret.{self.call_counts[name]}"
        self.call_counts[name] += 1
        
        self.write([f"@{return_label}",
                    "D=A"])
        self.pushD()
        
        # Push LCL, ARG, THIS, THAT onto the stack
        for segment in ["LCL", "ARG", "THIS", "THAT"]:
            self.write([f"@{segment}",
                        "D=M"])
            self.pushD()
            
        # Reposition ARG (memory location of ARG = SP location - number of arguments - 5)
        # The 5 accounts for the return address, LCL, ARG, THIS, THAT we just pushed
        self.write(["@SP",
                    "D=M",
                    f"@{n_args + 5}",
                    "D=D-A",
                    "@ARG",
                    "M=D"])
        
        # Repositions LCL (LCL = SP) since the SP current points to the slot after the function frame we just pushed
        self.write(["@SP",
                    "D=M",
                    "@LCL",
                    "M=D"])
        
        # Transfer control to the called function (Jump to the function's label)
        self.write([f"@{name}",
                    "0;JMP"])
        
        # Declare the return label (so we can jump back here after the function returns)
        self.write([f"({return_label})"])
        
    # ---- Return commands ----
    def writeReturn(self):
        # Save the address of LCL into a temp variable (Save the top of the current function's frame)
        self.write(["@LCL",
                    "D=M",  # Get address of LCL into D
                    "@R13", 
                    "M=D"]) # Store address of LCL into R13
        
        # Get the return address into a temp variable (we can do this because D is still address of LCL)
        self.write(["@5",    # Get 5 into A
                    "A=D-A", # A = address of LCL - 5
                    "D=M",   # Now we are at the return address, so store that into D
                    "@R14",  # Store return address in R14
                    "M=D"])
        
        # Reposition the return value for the caller
        self.popD()         # Pop the return value into D
        self.write(["@ARG", # Go to ARG value
                    "A=M",  # Set the address to the memory location stored at ARG
                    "M=D"]) # memory location of ARG = return value
        
        # Reposition the stack pointer of the caller (put the stack pointer just after the return value)
        self.write(["@ARG",
                    "D=M+1", # D = address in ARG + 1
                    "@SP",
                    "M=D"])  # SP = address in ARG + 1
        
        # Restore THAT, THIS, ARG, LCL of the caller (Go back up the stack frame and restore segments in the reverse order we put them there)
        for i, segment in enumerate(["THAT", "THIS", "ARG", "LCL"]):
            self.write(["@R13",        # get address of LCL out of R13
                        "D=M",         # D = address of LCL
                        f"@{i+1}",     # Get i+1 into A (1 for THAT, 2 for THIS, etc.)
                        "A=D-A",       # A = address of LCL - (i+1)
                        "D=M",         # D = value at that address
                        f"@{segment}", # Go to segment we are restoring (THAT, THIS, ARG, LCL)
                        "M=D"])        # Restore segment
                        
        # Go to the return address and jump
        self.write(["@R14", # Get return address from R14
                    "A=M",
                    "0;JMP"]) # Jump to return address
    
    # ---- Bootstrap code ----
    def writeInit(self):
        self.write(["@256", 
                    "D=A",
                    "@SP",
                    "M=D"])
        self.writeCall("Sys.init", 0) # Call Sys.init with 0 arguments
    
    # ---- Main command translation loop ----
    def cmdAsm(self):
        for command in self.commands:
            if command.ctype == "C_ARITHMETIC":
                self.writeArithmetic(command.arg1)
            elif command.ctype in ("C_PUSH", "C_POP"):
                self.writePushPop(command.ctype, command.arg1, command.arg2)
            elif command.ctype == "C_LABEL":
                self.writeLabel(command.arg1)
            elif command.ctype == "C_GOTO":
                self.writeGoto(command.arg1)
            elif command.ctype == "C_IF":
                self.writeIf(command.arg1)
            elif command.ctype == "C_FUNCTION":
                self.writeFunction(command.arg1, command.arg2)
            elif command.ctype == "C_CALL":
                self.writeCall(command.arg1, command.arg2)
            elif command.ctype == "C_RETURN":
                self.writeReturn()
            elif command.ctype == "C_INIT":
                if self.commands.index(command) == 0:  # Only allow writing bootstrap code at the start (Shouldn't happen, but just in case)
                    self.writeInit()
                else:
                    raise ValueError("C_INIT command can only appear at the beginning of the command list.")
            elif command.ctype == "CHANGE_FILE":
                self.setFileName(command.arg1)
            else:
                raise ValueError(f"Unsupported command type in cmdAsm: {command.ctype}")

# ----------------------------- Parser Class -----------------------------
class Parser:
    def __init__(self, file_name):
        self.file_name = file_name
        
        with open(file_name, 'r') as file:
            self.lines = file.readlines()
            
        self.commands = list[Command]() 

    def __len__(self):
        return len(self.lines)
    
    def loadLines(self):
        with open(self.file_name, 'r') as file:
            self.lines = file.readlines()

    def translateCommands(self):
        for line in self.lines:
            # Remove comments and whitespace
            line = line.split("//")[0].strip()
            if not line:
                continue  # Skip empty lines
            
            parts = line.split()
            cmd = parts[0]
            
            if cmd in ARITH:
                self.commands.append(Command("C_ARITHMETIC", cmd, None))
            elif cmd == "push":
                segment = parts[1]
                index = int(parts[2])
                self.commands.append(Command("C_PUSH", segment, index))
            elif cmd == "pop":
                segment = parts[1]
                index = int(parts[2])
                self.commands.append(Command("C_POP", segment, index))
            elif cmd == "label":
                label = parts[1]
                self.commands.append(Command("C_LABEL", label, None))
            elif cmd == "goto":
                label = parts[1]
                self.commands.append(Command("C_GOTO", label, None))
            elif cmd == "if-goto":
                label = parts[1]
                self.commands.append(Command("C_IF", label, None))
            elif cmd == "function":
                name = parts[1]
                n_vars = int(parts[2])
                self.commands.append(Command("C_FUNCTION", name, n_vars))
            elif cmd == "call":
                name = parts[1]
                n_args = int(parts[2])
                self.commands.append(Command("C_CALL", name, n_args))
            elif cmd == "return":
                self.commands.append(Command("C_RETURN", "", None))
            else:
                raise ValueError(f"Unknown command: {cmd}")
    
    def close(self):
        self.lines = []
        commands = self.commands
        self.commands = []
        return commands

# ----------------------------- Main Program ----------------------------
if __name__ == "__main__":
    # Handle command line arguments and input/output files
    args = parser.parse_args()
    input = str(args.filename)
    no_bootstrap = args.no_bootstrap
    
    # Check if input file is a full path or relative
    if not os.path.isabs(input):
        input = os.path.join(cwd, input)

    output_file = str(args.output) if args.output else os.path.splitext(input)[0] + ".asm"

    # Check to make sure we are working with valid files
    if not output_file.endswith(".asm"):
        print("Error: Output file must have a .asm extension.")
        exit()
        
    # Does the output directory exist?
    output_dir = os.path.dirname(output_file)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Output directory '{output_dir}' created.")
    
    # Check if input is a directory
    commands = []
    if os.path.isdir(input):
        vm_files = [os.path.join(input, file) for file in os.listdir(input) if file.endswith('.vm')]
        if not vm_files:
            print(f"Error: No .vm files found in directory '{input}'.")
            exit()

        # Use the directory name for the output .asm file
        dir_name = os.path.basename(os.path.normpath(input))
        output_file = os.path.join(input, dir_name + ".asm")
        
        if not no_bootstrap:
            commands.append(Command("C_INIT", "", None))  # Add bootstrap command at the start

        # Initialize parser and translate commands from all .vm files
        for vm_file in vm_files:
            commands.extend([Command("CHANGE_FILE", os.path.splitext(os.path.basename(vm_file))[0], None)])
            parser = Parser(vm_file)
            parser.translateCommands()
            vm_file_commands = parser.close()
            commands.extend(vm_file_commands)
            print(f"Parsed {len(vm_file_commands)} commands from '{os.path.basename(vm_file)}'.")

    else:
        # Process a single .vm file
        if not os.path.isfile(input):
            print(f"Error: File '{input}' does not exist.")
            exit()
        if not input.endswith(".vm"):
            print("Error: Input file must have a .vm extension.")
            exit()
            
        if not no_bootstrap:
            commands.append(Command("C_INIT", "", None))  # Add bootstrap command at the start
            
        commands.append(Command("CHANGE_FILE", os.path.splitext(os.path.basename(input))[0], None))
        parser = Parser(input)
        parser.translateCommands()
        commands.extend(parser.close())
        print(f"Parsed {len(commands)} commands from '{os.path.basename(input)}'.")

    # Initialize code writer
    code_writer = CodeWriter(commands, debug=args.debug)
    code_writer.cmdAsm()
    asm_lines = code_writer.close()

    print(f"Generated {len(asm_lines)} assembly lines.")

    # Now write everything to the output file
    with open(output_file, 'w') as file:
        for line in asm_lines:
            file.write(line + '\n')

    print(f"Output written to '{os.path.basename(output_file)}'.")