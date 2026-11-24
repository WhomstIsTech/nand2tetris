import os
import argparse

# Define custom SymbolTable class
class SymbolTable:
    def __init__(self):
        self._table = {}

        # Setting up registers R0-R15
        for i in range(16):
            self._table[f"R{i}"] = i

        # Extra pointers and I/O
        self._table.update({
            "SP": 0, "LCL": 1, "ARG": 2, "THIS": 3, "THAT": 4,
            "SCREEN": 16384, "KBD": 24576
        })

        # Next available variable address (variables start at 16 and end at 255)
        self._next_var = 16

    def add_label(self, symbol, rom_address):
        if symbol not in self._table: # Do we have this symbol already?
            self._table[symbol] = rom_address

    def add_variable(self, symbol):
        if symbol not in self._table: # Do we have this symbol already?
            self._table[symbol] = self._next_var
            self._next_var += 1
        return self._table[symbol]

    def contains(self, symbol):
        return symbol in self._table

    def get_address(self, symbol):
        return self._table[symbol]
    
    def clear(self):
        self._table = {}
        self.__init__()

# Define lookup tables for dest, comp, and jump fields
DEST_TABLE = {
    None:  "000",
    "M":   "001",
    "D":   "010",
    "MD":  "011",
    "A":   "100",
    "AM":  "101",
    "AD":  "110",
    "AMD": "111",
}

JUMP_TABLE = {
    None:  "000",
    "JGT": "001",
    "JEQ": "010",
    "JGE": "011",
    "JLT": "100",
    "JNE": "101",
    "JLE": "110",
    "JMP": "111",
}

COMP_TABLE = {
    "0":   "0101010",
    "1":   "0111111",
    "-1":  "0111010",
    "D":   "0001100",
    "A":   "0110000",
    "!D":  "0001101",
    "!A":  "0110001",
    "-D":  "0001111",
    "-A":  "0110011",
    "D+1": "0011111",
    "1+D": "0011111",
    "A+1": "0110111",
    "1+A": "0110111",
    "D-1": "0001110",
    "A-1": "0110010",
    "D+A": "0000010",
    "D-A": "0010011",
    "A-D": "0000111",
    "D&A": "0000000",
    "A&D": "0000000",
    "D|A": "0010101",
    "A|D": "0010101",
    "M":   "1110000",
    "!M":  "1110001",
    "-M":  "1110011",
    "M+1": "1110111",
    "1+M": "1110111",
    "M-1": "1110010",
    "D+M": "1000010",
    "M+D": "1000010",
    "D-M": "1010011",
    "M-D": "1000111",
    "D&M": "1000000",
    "M&D": "1000000",
    "D|M": "1010101",
    "M|D": "1010101"
}

# Set up parsing for command line arguments
parser = argparse.ArgumentParser(prog="hasm", description="Hack Assembler")
parser.add_argument("filename", help="Path to the .asm file to be assembled", type=str)
parser.add_argument("-o", "--output", help="Path to the output .hack file", default=None, type=str)
parser.add_argument("--debug", help="Enable debug mode", action="store_true")

# Set up current directory
cwd = os.getcwd()

if __name__ == "__main__":
    # Handle command line arguments and input/output files
    args = parser.parse_args()
    input_file = str(args.filename)
    
    # Check if input file is a full path or relative
    if not os.path.isabs(input_file):
        input_file = os.path.join(cwd, input_file)
    
    output_file = str(args.output) if args.output else os.path.splitext(input_file)[0] + ".hack"
    
    # Check to make sure we are working with valid files
    if not os.path.isfile(input_file):
        print(f"Error: File '{input_file}' does not exist.")
        exit()
    if not input_file.endswith(".asm"):
        print("Error: Input file must have a .asm extension.")
        exit()
    if not output_file.endswith(".hack"):
        print("Error: Output file must have a .hack extension.")
        exit()
        
    # Does the output directory exist?
    output_dir = os.path.dirname(output_file)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Output directory '{output_dir}' created.")

    # Initialize symbol table
    symbol_table = SymbolTable()
    
    # Open the input file and read lines
    with open(input_file, 'r') as file:
        original_lines = file.readlines()
    if not original_lines[-1].__contains__('\n'):
        original_lines[-1] += '\n'
    temp = []
    for line in original_lines:
        # Remove inline spaces
        line = line.replace(" ", "")
        temp.append(line)
    original_lines = temp
    
    ##################################### Prescreen #####################################
    # Now loop through them and eliminate comments and lines that are empty
    lines = []
    for line in original_lines:
        # Strip ends of whitespace
        line = line.strip()
        
        # Remove comments
        if '//' in line:
            line = line.split('//')[0].strip()
        
        # Only add non-empty lines
        if line:
            lines.append(line)

    if not lines:
        print("Error: No valid instructions found in the input file.")
        exit()
            
    ##################################### PASS 1 #####################################
    # In the first pass, we look for label declarations (e.g., (LABEL))
    # If one is found, we don't add it to the new list, but we do add its address to the symbol table
    # The address is the line number in the final program (not counting labels)
    
    pc = 0  # Initialize program counter
    for line in lines:
        if line.startswith('(') and line.endswith(')'):
            label = line[1:-1]
            if not symbol_table.contains(label):
                symbol_table.add_label(label, pc)
            else:
                print(f"Error: Label '{label}' defined multiple times starting at line {original_lines.index(line) + 1}.")
                exit()
        else:
            pc += 1  # Increment ROM address only for non-label lines
            
    ##################################### PASS 2 #####################################
    # In the second pass, we translate instructions to binary
    # If the line containes @ then it is an A-instruction, thus eliminate the @ and either 
    # look up the symbol in the symbol table or treat it as a numeric constant. Handle
    # negative numbers by converting with two's complement.
    #
    # If C-instruction (dest=comp;jump), break into dest, comp, jump fields. Then
    # handle each field using lookup tables and assemble into final binary code
    
    binary_lines = []
    for line in lines:
        
        # First handle label declarations (skip them)
        if line.startswith('(') and line.endswith(')'):
            continue
        
        # Handle A-instructions (Does the line start with @?)
        if line.startswith('@'):
            symbol = line[1:]
            isNegative = False
            if symbol_table.contains(symbol): # Already in symbol table
                address = symbol_table.get_address(symbol)
            elif symbol.isdigit(): # Positive number handling
                address = int(symbol)
            elif symbol[0] == '-' and symbol[1:].isdigit(): # Negative number handling
                address = int(symbol[1:])
                isNegative = True
            else: # New variable
                address = symbol_table.add_variable(symbol)
            
            # Convert address to 16-bit binary
            binary_code = format(address, '016b')
            if isNegative:
                binary_code = format((1 << 16) - int(binary_code, 2), '016b')
            
            # Ensure address fits in 15 bits
            if address > 0x7FFF:
                fstring_line = line + '\n'
                print(f"Error: Address {address} exceeds 15 bits maximum at line {original_lines.index(fstring_line) + 1}")
                exit()
            
            binary_lines.append(binary_code)
            continue
        
        # Handle C-instructions
        else:
            dest, comp, jump = None, None, None
            line_temp = line
            if '=' in line_temp: # Is there a destination?
                parts = line_temp.split('=')
                dest = parts[0].strip()
                line_temp = parts[1].strip()
            if ';' in line_temp: # Is there a jump?
                parts = line_temp.split(';')
                comp = parts[0].strip()
                jump = parts[1].strip()
            else:
                comp = line_temp.strip()
            
            # Lookup binary codes
            comp_bits = COMP_TABLE.get(comp)
            dest_bits = DEST_TABLE.get(dest)
            jump_bits = JUMP_TABLE.get(jump)
            
            if comp_bits is None:
                fstring_line = line + '\n'
                print(f"Error: Invalid computation '{comp}' in line {original_lines.index(fstring_line) + 1}")
                exit()
                
            if dest_bits is None:
                fstring_line = line + '\n'
                if dest == "":
                    print(f"Error: No destination specified, but '=' was used in line {original_lines.index(fstring_line) + 1}")
                    exit()
                print(f"Error: Invalid destination '{dest}' in line {original_lines.index(fstring_line) + 1}")
                exit()
            
            if jump_bits is None:
                fstring_line = line + '\n'
                if jump == "":
                    print(f"Error: No jump specified, but ';' was used in line {original_lines.index(fstring_line) + 1}")
                    exit()
                print(f"Error: Invalid jump '{jump}' in line {original_lines.index(fstring_line) + 1}")
                exit()
            
            # Assemble the final binary code
            binary_code = f"111{comp_bits}{dest_bits}{jump_bits}"
            binary_lines.append(binary_code)
            
    
    # Now write everything to the output file
    with open(output_file, 'w') as file:
        for line in binary_lines:
            file.write(line + '\n')