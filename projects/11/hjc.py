'''
Hack JACK Compiler (HJC)

Author: James Giffen
Date: 12/4/2025
'''

import os
import argparse
from typing import List
from io import TextIOWrapper

# Set up parsing for command line arguments
parser = argparse.ArgumentParser(prog="hjc", description="Hack JACK Compiler")
parser.add_argument("filename", help="Path to the .jack file/directory to be compiled", type=str)
parser.add_argument("-t", "--tokens", help="Will enable the outputting of the tokens to an XML file", action="store_true", default=False)
parser.add_argument("-x", "--xml", help="Will enable the outputting of the compilation engine XML output for debugging", action="store_true", default=False)

# Set up current directory
cwd = os.getcwd()

# Define constants
SYMBOLS = {'{', '}', '(', ')', '[', ']', '.', ',', ';', '+', '-', '*', '/', '&', '|', '<', '>', '=', '~'}
KEYWORDS = ['class', 'constructor', 'function', 'method', 'field', 'static', 'var', 'int', 'char', 'boolean', 'void', 'true', 'false', 'null', 'this', 'let', 'do', 'if', 'else', 'while', 'return']

VARMAPPING = {"static": "static",
              "field": "this",
              "arg": "argument",
              "var": "local"}

ARITHMATICMAPPING = {"+": "add",
                     "-": "sub",
                     "*": "call Math.multiply 2",
                     "/": "call Math.divide 2",
                     "&": "and",
                     "|": "or",
                     "<": "lt",
                     ">": "gt",
                     "=": "eq",}

# ----------------------------- Token Class -----------------------------
class Token:
    def __init__(self, token_type: str, value: str | int, tokenXML: str = "", tokenVM: str = ""):
        self.token_type = token_type
        self.token_XML = tokenXML
        self.value = value
        self.token_VM = tokenVM

# ----------------------------- Tokenizer Class -----------------------------
class Tokenizer:
    def __init__(self, file_path: str):
        
        # Taken in the file path to read from
        self.file_path = file_path
        
        # Read the file and gather the lines
        with open(file_path, 'r') as file:
            self.input_lines = file.readlines()
        
        # Initialize the list of tokens
        self.tokens: List[Token] = []
        
    def tokenize(self):
        '''
        Turns the input .jack file into a list of Token Class
        '''
        blockComment = False

        # Loop through each line in the input file (keep line numbers)
        for lineno, line in enumerate(self.input_lines, start=1):
            line = line.rstrip('\n')

            # Remove/skip block comments
            while True:
                if not blockComment:
                    start = line.find('/*')
                    if start == -1: # There was no block comment found on this line
                        break
                    end = line.find('*/', start + 2)
                    if end != -1: # The find was successful
                        # Remove the /* ... */ segment and continue checking the resulting line
                        line = line[:start] + line[end + 2:] # We add 2 to skip past */
                        continue
                    else: # The find was unsuccessful since it returned -1
                        # Start of block comment that doesn't end on this line
                        blockComment = True
                        line = line[:start]
                        break
                else:
                    end = line.find('*/') # Since we are inside a block comment because blockComment is True, we need to find the end
                    if end != -1: # The find was successful and we eliminate all the text up to the end of the block comment
                        line = line[end + 2:]
                        blockComment = False
                        continue
                    else: # The find was unsuccessful since it returned -1 and we eliminate the entire line
                        # Still inside block comment, so skip the line
                        line = ''
                        break

            # Ignore empty lines and inline comments
            line = line.split("//")[0].strip()
            if not line:
                continue

            # Now go through each line character by character in search of tokens
            i = 0 # Character index
            while i < len(line):
                char = line[i]
                
                # ----------------- WHITESPACE -----------------
                if char.isspace():
                    i += 1
                    continue
                
                # ----------------- STRING CONSTANT -----------------
                if char == '"':
                    i += 1
                    string_value = ""
                    # Build up the string that is the string constant
                    while i < len(line) and line[i] != '"':
                        string_value += line[i]
                        i += 1
                    # Ensure closing quote was found
                    if i >= len(line) or line[i] != '"':
                        raise IndexError("String not closed before end of line")
                    # Append token and skip closing quote
                    self.tokens.append(Token("STRING_CONST", string_value, f"<stringConstant> {string_value} </stringConstant>"))
                    i += 1
                    continue
                
                # ----------------- SYMBOL -----------------
                if char in SYMBOLS:
                    # Since symbols are only one character, we can just add them directly
                    if char == '<': # Handle XML special characters
                        self.tokens.append(Token("SYMBOL", char, f"<symbol> &lt; </symbol>"))
                    elif char == '>':
                        self.tokens.append(Token("SYMBOL", char, f"<symbol> &gt; </symbol>"))
                    elif char == '&':
                        self.tokens.append(Token("SYMBOL", char, f"<symbol> &amp; </symbol>"))
                    else: # Otherwise, just add the symbol normally
                        self.tokens.append(Token("SYMBOL", char, f"<symbol> {char} </symbol>"))
                    i += 1
                    continue
                
                # ----------------- INTEGER CONSTANT -----------------
                if char.isdigit():
                    int_value = ""
                    # Build up the string that is the integer constant
                    while i < len(line) and line[i].isdigit():
                        int_value += line[i]
                        i += 1
                    self.tokens.append(Token("INT_CONST", int_value, f"<integerConstant> {int_value} </integerConstant>"))
                    continue
                
                # ----------------- IDENTIFIER / KEYWORD -----------------
                if char.isalpha() or char == '_':
                    value = ""
                    # Build up the string that is the identifier/keyword
                    while i < len(line) and (line[i].isalnum() or line[i] == '_'):
                        value += line[i]
                        i += 1
                    if value in KEYWORDS: # Check if it's a keyword
                        self.tokens.append(Token("KEYWORD", value, f"<keyword> {value} </keyword>"))
                    else: # Otherwise, it's an identifier
                        self.tokens.append(Token("IDENTIFIER", value, f"<identifier> {value} </identifier>"))
                    continue
                
                # If we reach here, it's an unrecognized character
                raise ValueError(f"Unrecognized character '{char}' in line {lineno}")
                
    def write_output(self, output_path: str):
        with open(output_path, 'w') as file:
            file.write("<tokens>\n")
            for token in self.tokens:
                file.write(f"{token.token_XML}\n")
            file.write("</tokens>\n")
        return self.close()
            
    def close(self):
        returnTokens = self.tokens
        self.tokens = []
        return returnTokens

# ------------------------- SymbolTable Class -------------------------
class SymbolTable:
    def __init__(self):
        self.classVars = {}
        self.subRoutVars = {}
        self.counts = {'static': 0, 'field': 0, 'arg': 0, 'var':0}
    
    def resetSubroutine(self):
        # Reset just the variables that are saved for subroutines
        self.subRoutVars = {}
        self.counts['arg'] = 0
        self.counts['var'] = 0
    
    def addSymbol(self, name: str, varType: str, vmType: str):
        idx = self.counts[vmType]
        self.counts[vmType] += 1
        if vmType in ("static", "field"):
            self.classVars[name] = (varType, vmType, idx)
        else:
            self.subRoutVars[name] = (varType, vmType, idx)
    
    def varCount(self, vmType):
        return self.counts[vmType]
    
    def varType(self, name: str):
        if name in self.subRoutVars:
            return self.subRoutVars[name][0]
        if name in self.classVars:
            return self.classVars[name][0]
        raise ValueError(f"Variable '{name}' was never declared. Declare it before use.")
    
    def vmType(self, name: str):
        if name in self.subRoutVars:
            return self.subRoutVars[name][1]
        if name in self.classVars:
            return self.classVars[name][1]
        raise ValueError(f"Variable '{name}' was never declared. Declare it before use.")
    
    def index(self, name: str):
        if name in self.subRoutVars:
            return self.subRoutVars[name][2]
        if name in self.classVars:
            return self.classVars[name][2]
        raise ValueError(f"Variable '{name}' was never declared. Declare it before use.")
    
    def inSymbolTable(self, name: str):
        return name in self.subRoutVars or name in self.classVars
    
# ------------------------- VMWriter Class -------------------------
class vmWriter:
    def __init__(self, output_file: TextIOWrapper):
        self.output_file = output_file
        
        # Indentation level only changes for function calls.
        # This is just to look nice in the output file.
        self.indent_level = 0
        
    def close(self):
        self.output_file.close()
        
    def _write_line(self, line: str | int | None):
        # Generate the correct indentation and write the line
        indent = '' * self.indent_level
        self.output_file.write(f"{indent}{line}\n")
        
    # ---- Basic VM Commands ----
    def writePush(self, segment: str | int | None, index: int):
        self._write_line(f"push {segment} {index}")
        
    def writePop(self, segment: str | int | None, index: int):
        self._write_line(f"pop {segment} {index}")
        
    def writeArithmetic(self, command: str | int | None):
        self._write_line(command)
        
    # ---- VM Flow Commands ----
    def writeLabel(self, label: str | int | None):
        self._write_line(f"label {label}")
    
    def writeGoto(self, label: str | int | None):
        self._write_line(f"goto {label}")
    
    def writeIfGoto(self, label: str | int | None):
        self._write_line(f"if-goto {label}")
        
    # ---- Function Commands ----
    def writeCall(self, name: str | int | None, nArgs: int):
        self._write_line(f"call {name} {nArgs}")
        
    def writeFunction(self, name: str | int | None, nLocals: int):
        self._write_line(f"function {name} {nLocals}")
        self.indent_level += 1
        
    def writeReturn(self):
        self._write_line("return")
        self.indent_level -= 1
    
    # ---- Comment Commands ----
    def writeComment(self, comment):
        self._write_line(f"// {comment}")

# ------------------------- CompilationEngine Class -------------------------
class CompilationEngine:
    def __init__(self, tokens: List[Token], output_path: str, writeXML: bool = False):
        # Take in the tokens from the Tokenizer
        self.tokens = tokens
        
        # Whether to write XML output (for debugging)
        self.writeXML = writeXML
        
        # We want to create / write to this file in real time to ensure we get the indents right
        self.output_path = output_path
        if writeXML:
            self.output_file = open(self.output_path, 'w')
        
        # Determine indentation level
        self.indent_level = 0
        
        # Create a symbol table and vm writer
        self.symbolTable = SymbolTable()
        self.vmWriter = vmWriter(open(self.output_path.replace('.xml', '.vm'), 'w'))
        
        # Current index/current token
        self.currentIndex = 0
        self.currentToken: Token | None = self.tokens[0] if self.tokens else None
        
        # Current class name for VM function naming
        self.className = ""
        
        # Handle label counting for if and while statements
        self.ifcount = 0
        self.whilecount = 0
    
    # ---- General Helpers ----
    def close(self):
        # Close the output file when done since we are editing it in real time
        if self.writeXML:
            self.output_file.close()
        self.vmWriter.close()
    
    def _write_line(self, line: str):
        # Generate the correct indentation and write the line
        indent = '  ' * self.indent_level
        self.output_file.write(f"{indent}{line}\n")
        
    def _advance(self):
        '''
        Advance to the next token and grab it
        If none are left, set the current one to none
        '''
        self.currentIndex += 1
        
        if self.currentIndex < len(self.tokens):
            self.currentToken = self.tokens[self.currentIndex]
        else:
            self.currentToken = None
            
    def _writeAdvance(self, expectedType: str | None = None, expectedValue: str | None = None):
        '''
        Write the current token as a line and then advance to the next token
        '''
        # Check if the current token is valid
        if self.currentToken is None:
            raise ValueError("Unexpected end of input while parsing")
        
        # Check if we are expecting this type of token
        if expectedType is not None and self.currentToken.token_type != expectedType:
            raise ValueError(f"Expected type {expectedType}, got {self.currentToken.token_type} with value {self.currentToken.value}")
        
        # Check if we are expecting the value in the token
        if expectedValue is not None and self.currentToken.value != expectedValue:
            raise ValueError(f"Expected value {expectedValue}, got {self.currentToken.value} with type {self.currentToken.token_type}")
        
        # Now we can write everything if we are getting what we expect
        if self.writeXML:
            self._write_line(self.currentToken.token_XML)
        self._advance()
    
    def _nextTT(self):
        '''
        Look at the next token's type
        Return None if there isn't a token after it
        '''
        return self.tokens[self.currentIndex + 1].token_type if self.currentIndex + 1 < len(self.tokens) else None
    
    def _nextTV(self):
        '''
        Look at the next token's value
        Return None if there isn't a token after it
        '''
        return self.tokens[self.currentIndex + 1].value if self.currentIndex + 1 < len(self.tokens) else None
    
    def _tt(self):
        '''
        Grab the current token's type and return it
        Return None if the current token is None
        '''
        return self.currentToken.token_type if self.currentToken else None
    
    def _tv(self):
        '''
        Grab the current token's value and return it
        Return None if the current token is None
        '''
        return self.currentToken.value if self.currentToken else None
        
    # ---- Tag Writers ----
    def _tagOpen(self, tag: str):
        if not self.writeXML:
            return
        self._write_line(f"<{tag}>")
        self.indent_level += 1
        
    def _tagClose(self, tag: str):
        if not self.writeXML:
            return
        self.indent_level -= 1
        self._write_line(f"</{tag}>")
        
    # ---- Class Compiler ----
    def compileClass(self):
        # Write the open tag for the class
        self._tagOpen("class")
        
        # Reset the symbol table for a new class
        self.symbolTable = SymbolTable()
        
        # Now we can write the first token which should be a KEYWORD "class"
        self._writeAdvance(expectedType="KEYWORD", expectedValue="class")
        
        # Now we can write the name of the class which should be an IDENTIFIER and be the same as the file name
        expectedClassName = os.path.basename(self.output_path).replace('.xml', '')
        self._writeAdvance(expectedType="IDENTIFIER", expectedValue=expectedClassName)
        self.className = expectedClassName
        
        self.vmWriter.writeComment(f"Class {expectedClassName}")
        
        # Now we need an open bracket
        self._writeAdvance(expectedType="SYMBOL", expectedValue="{")
        
        # The class can have variables so we declare them now
        while self._tt() == "KEYWORD" and self._tv() in {"field", "static"}:
            self.compileClassVarDec()
        
        # The class can have subroutines so we declare them now
        while self._tt() == "KEYWORD" and self._tv() in {"constructor", "function", "method"}:
            self.compileSubroutine()
        
        # Now we are done with the class so we expect a close bracket
        self._writeAdvance(expectedType="SYMBOL", expectedValue="}")
        
        # Write the close tag for the class
        self._tagClose("class")
        
    # ---- Class Variables Compiler ----
    def compileClassVarDec(self):
        # Write the open tag for the variable declaration
        self._tagOpen("classVarDec")
        
        # Write "static" or "field"
        currentVMType = self._tv()
        self._writeAdvance(expectedType="KEYWORD")
        
        # Write the type of variable. Since it could also be a class, we need to handle that case
        if self._tt() == "KEYWORD" and self._tv() in {"int", "char", "boolean"}:
            currentVarType = self._tv()
            self._writeAdvance(expectedType="KEYWORD")
        elif self._tt() == "IDENTIFIER":
            currentVarType = self._tv()
            self._writeAdvance(expectedType="IDENTIFIER")
        else:
            raise ValueError(f"Unexpected token in type: {self._tt()} {self._tv()}")
        
        # Write the variable name
        currentName = self._tv()
        self._writeAdvance(expectedType="IDENTIFIER")
        
        # Add the variable to the symbol table
        self.symbolTable.addSymbol(str(currentName), str(currentVarType), str(currentVMType))
        
        # Since we can define multiple variables, we need to loop through the commas and their names
        while self._tt() == "SYMBOL" and self._tv() == ",":
            self._writeAdvance(expectedType="SYMBOL", expectedValue=",")
            currentName = self._tv()
            self._writeAdvance(expectedType="IDENTIFIER")
            self.symbolTable.addSymbol(str(currentName), str(currentVarType), str(currentVMType))
        
        # Now we have to expect a ; to end the delcaration
        self._writeAdvance(expectedType="SYMBOL", expectedValue=";")
        
        # Write the closing tag for the variable declaration
        self._tagClose("classVarDec")
    
    # -------- Subroutine-Related Compilation --------
    # ---- Subroutine Compiler ----
    def compileSubroutine(self):
        # Write the open tag for a subroutine declaration
        self._tagOpen("subroutineDec")
        
        # Now we can write the function, method or constructor
        currentSubroutineType = self._tv()
        self._writeAdvance(expectedType="KEYWORD")
        
        # Reset the subroutine symbol table
        self.symbolTable.resetSubroutine()
        
        # If it is a method, we need to add the argument "this" to the symbol table to not mess up the count (even if we don't use it)
        if currentSubroutineType == "method":
            self.symbolTable.addSymbol("this", self.className, "arg")
        
        # Reset the if and while label counters
        self.ifcount = 0
        self.whilecount = 0
        
        # Now we can write the type that we are expecting to output
        if self._tt() == "KEYWORD" and self._tv() in {"int", "char", "boolean", "void"}:
            self._writeAdvance(expectedType="KEYWORD")
        elif self._tt() == "IDENTIFIER":
            self._writeAdvance(expectedType="IDENTIFIER")
        else:
            raise ValueError(f"Invalid return type: {self._tt()} {self._tv()}")
        
        # Now write the name of the function
        subroutineName = self._tv()
        self._writeAdvance(expectedType="IDENTIFIER")
        fullFunctionName = f"{self.className}.{subroutineName}"
        
        self.vmWriter.writeComment(f"Start of {fullFunctionName}")
        
        # Now we are expecting the parameter list so handle the parenthesis and then call the parameter list
        self._writeAdvance(expectedType="SYMBOL", expectedValue="(")
        self.compileParameterList()
        self._writeAdvance(expectedType="SYMBOL", expectedValue=")")
        
        # Then call the subroutine body
        self.compileSubroutineBody(fullFunctionName, currentSubroutineType)
        
        # Write the closing tag for a subroutine declaration
        self._tagClose("subroutineDec")
        
    # ---- Parameter List Compiler ----
    def compileParameterList(self):
        # Write the open tag for the parameterList
        self._tagOpen("parameterList")
        
        # We can check if there are any parameters and the iterate through them
        if self._tt() in {"KEYWORD", "IDENTIFIER"}:
            if self._tt() == "KEYWORD" and self._tv() in ("int", "char", "boolean"):
                currentVarType = self._tv()
                self._writeAdvance(expectedType="KEYWORD")
            elif self._tt() == "IDENTIFIER":
                currentVarType = self._tv()
                self._writeAdvance(expectedType="IDENTIFIER")
            else:
                raise ValueError(f"Unexpected token in type: {self._tt()} {self._tv()}")
            
            # Then write the parameter name
            currentName = self._tv()
            self._writeAdvance(expectedType="IDENTIFIER")
            
            # Add the parameter to the symbol table
            self.symbolTable.addSymbol(str(currentName), str(currentVarType), "arg")
            
            while self._tt() == "SYMBOL" and self._tv() == ",":
                # Write the comma
                self._writeAdvance(expectedType="SYMBOL", expectedValue=",")
                
                # Then chen check which kind of variable it is
                if self._tt() == "KEYWORD" and self._tv() in ("int", "char", "boolean"):
                    currentVarType = self._tv()
                    self._writeAdvance(expectedType="KEYWORD")
                elif self._tt() == "IDENTIFIER":
                    currentVarType = self._tv()
                    self._writeAdvance(expectedType="IDENTIFIER")
                else:
                    raise ValueError(f"Unexpected token in type: {self._tt()} {self._tv()}")
                
                # Then write the parameter name
                currentName = self._tv()
                self._writeAdvance(expectedType="IDENTIFIER")
                
                # Add the parameter to the symbol table
                self.symbolTable.addSymbol(str(currentName), str(currentVarType), "arg")
            
        # Write the closing tag for a parameterList
        self._tagClose("parameterList")
    
    # ---- Subroutine Body Compiler ----
    def compileSubroutineBody(self, fullFunctionName: str | int | None, currentSubroutineType: str | int | None):
        # Write the open tag for the Subroutine Body
        self._tagOpen("subroutineBody")
        
        # Now write the open bracket for the subroutine body
        self._writeAdvance(expectedType="SYMBOL", expectedValue="{")
        
        # Now we search for variable declarations as they HAVE to be first
        localsCount = 0
        while self._tt() == "KEYWORD" and self._tv() == "var":
            localsCount += self.compileVarDec()
            
        # Now we can write the function declaration in VM
        self.vmWriter.writeFunction(fullFunctionName, localsCount)
        
        # If this is a method, we need to set the this pointer
        if currentSubroutineType == "method":
            self.vmWriter.writePush("argument", 0)
            self.vmWriter.writePop("pointer", 0)
        # If this is a constructor, we need to allocate memory for the object
        elif currentSubroutineType == "constructor":
            fieldCount = self.symbolTable.varCount("field")
            self.vmWriter.writePush("constant", fieldCount)
            self.vmWriter.writeCall("Memory.alloc", 1)
            self.vmWriter.writePop("pointer", 0)
        
        # Then we compile all the statements
        self.compileStatements()
        
        # Write the closing bracket for the subroutine body
        self._writeAdvance(expectedType="SYMBOL", expectedValue="}")
        
        # Write the closing tag for the Subroutine Body
        self._tagClose("subroutineBody")
        
    # ---- Variables Compiler ----
    def compileVarDec(self):
        # Count of local variables declared
        numLocals = 0
        
        # Write the open tag for the variable declaration
        self._tagOpen("varDec")
        
        # Write the var statement
        currentVMType = self._tv()
        self._writeAdvance(expectedType="KEYWORD", expectedValue="var")
        
        # Write the type of variable. Since it could also be a class, we need to handle that case
        if self._tt() == "KEYWORD" and self._tv() in {"int", "char", "boolean"}:
            currentVarType = self._tv()
            self._writeAdvance(expectedType="KEYWORD")
        elif self._tt() == "IDENTIFIER":
            currentVarType = self._tv()
            self._writeAdvance(expectedType="IDENTIFIER")
        else:
            raise ValueError(f"Unexpected token in type: {self._tt()} {self._tv()}")
        
        # Write the variable name
        currentName = self._tv()
        self._writeAdvance(expectedType="IDENTIFIER")
        
        # Add the variable to the symbol table
        self.symbolTable.addSymbol(str(currentName), str(currentVarType), str(currentVMType))
        numLocals += 1
        
        # Since we can define multiple variables, we need to loop through the commas and their names
        while self._tt() == "SYMBOL" and self._tv() == ",":
            self._writeAdvance(expectedType="SYMBOL", expectedValue=",")
            currentName = self._tv()
            self._writeAdvance(expectedType="IDENTIFIER")
            self.symbolTable.addSymbol(str(currentName), str(currentVarType), str(currentVMType)) # Write to the Symbol Table
            numLocals += 1
        
        # Now we have to expect a ; to end the delcaration
        self._writeAdvance(expectedType="SYMBOL", expectedValue=";")
        
        # Write the closing tag for the variable declaration
        self._tagClose("varDec")
        
        return numLocals
    
    # -------- All Statement-Related Compilation --------
    # ---- Statement Compiler ----
    def compileStatements(self):
        # Write the opening tag for a statement
        self._tagOpen("statements")
        
        # While we have statements, handle them
        while self._tt() == "KEYWORD" and self._tv() in {"let", "if", "while", "do", "return"}:
            if self._tv() == "let":
                self.compileLet()
            elif self._tv() == "if":
                self.compileIf()
            elif self._tv() == "while":
                self.compileWhile()
            elif self._tv() == "do":
                self.compileDo()
            elif self._tv() == "return":
                self.compileReturn()
        
        # Write the closing tag for a statement
        self._tagClose("statements")
        
    # ---- Let Statement Compiler ----
    def compileLet(self):
        # Write the opening tag for a let statement
        self._tagOpen("letStatement")
        
        # Since we are compiling a let statement, we should expect a "let"
        self._writeAdvance(expectedType="KEYWORD", expectedValue="let")
        
        # Then we always expect a variable name
        currentVarName = self._tv()
        self._writeAdvance(expectedType="IDENTIFIER")
        
        # Check if we are dealing with an array
        isArray = False
        
        # Grab the variable info from the symbol table
        varVMType = self.symbolTable.vmType(str(currentVarName))
        segment = VARMAPPING[varVMType]
        varIndex = self.symbolTable.index(str(currentVarName))
        
        # Since we could be dealing with an array we can check for "["
        if self._tt() == "SYMBOL" and self._tv() == "[":
            # Now we are dealing with an array
            isArray = True
            
            self._writeAdvance(expectedType="SYMBOL", expectedValue="[")
            self.compileExpression()
            self._writeAdvance(expectedType="SYMBOL", expectedValue="]")
            
            # Grab the base address of the array
            self.vmWriter.writePush(segment, varIndex)
            
            # Now the stack looks like [..., index, base]
            # Now we need to add the base address to the offset (the expression we just compiled)
            self.vmWriter.writeArithmetic("add")
            
        # We should now always expect an equals sign
        self._writeAdvance(expectedType="SYMBOL", expectedValue="=")
        
        # Now it could be any expression so we call that
        self.compileExpression()
        
        # Now store the result in the variable
        if isArray:
            # Stack: [..., address, value]
            # Now we need to save the value temporarily
            self.vmWriter.writePop("temp", 0)  # Pop value into temp 0
            # Then set the address to the pointer 1 (THAT)
            self.vmWriter.writePop("pointer", 1)
            # Then we can push the value back onto the stack
            self.vmWriter.writePush("temp", 0)  # Push value back onto stack
            # Finally, we can pop the value into THAT 0
            self.vmWriter.writePop("that", 0)
        else:
            # Not an array, so just pop the value into the variable
            self.vmWriter.writePop(segment, varIndex)
        
        # And we always end with ;
        self._writeAdvance(expectedType="SYMBOL", expectedValue=";")
        
        # Write the closing tag for a let statement
        self._tagClose("letStatement")
        
    # ---- If Statement Compiler ----
    def compileIf(self):
        # Write the opening tag for an if statement
        self._tagOpen("ifStatement")
        
        # Since we are compiling an if statement, we should expect a "if"
        self._writeAdvance(expectedType="KEYWORD", expectedValue="if")
        
        # Then we should always then expect "("
        self._writeAdvance(expectedType="SYMBOL", expectedValue="(")
        
        # Then we compile an expression
        self.compileExpression()
        
        # Then we expect a ")" followed by "{"
        self._writeAdvance(expectedType="SYMBOL", expectedValue=")")
        self._writeAdvance(expectedType="SYMBOL", expectedValue="{")
        
        # Now generate the labels for the if statement
        # The stack looks like [..., expressionResult]
        ifLabelTrue = f"IF_TRUE{self.ifcount}"
        ifLabelFalse = f"IF_FALSE{self.ifcount}"
        ifLabelEnd = f"IF_END{self.ifcount}"
        self.ifcount += 1
        
        # Write the VM commands for the if statement
        self.vmWriter.writeIfGoto(ifLabelTrue)
        self.vmWriter.writeGoto(ifLabelFalse)
        self.vmWriter.writeLabel(ifLabelTrue)
        
        # Then we compile statements
        self.compileStatements()
        
        # Then we close the bracket
        self._writeAdvance(expectedType="SYMBOL", expectedValue="}")
        
        # If there is an else, handle it
        if self._tt() == "KEYWORD" and self._tv() == "else":
            self._writeAdvance(expectedType="KEYWORD", expectedValue="else")
            
            # Since there is an else we have to have an end label after the if true statements
            self.vmWriter.writeGoto(ifLabelEnd)
            self.vmWriter.writeLabel(ifLabelFalse)
            
            self._writeAdvance(expectedType="SYMBOL", expectedValue="{")
            self.compileStatements()
            self._writeAdvance(expectedType="SYMBOL", expectedValue="}")
            
            # Write the end label
            self.vmWriter.writeLabel(ifLabelEnd)
        else:
            # Otherwise, just write the false label since there is no else
            self.vmWriter.writeLabel(ifLabelFalse)
        
        # Write the closing tag for an if statement
        self._tagClose("ifStatement")
        
    # ---- While Statement Compiler ----
    def compileWhile(self):
        # Write the opening tag for a while statement
        self._tagOpen("whileStatement")
        
        # Since we are compiling a while statement, we should expect a "while"
        self._writeAdvance(expectedType="KEYWORD", expectedValue="while")
        
        # Now generate the labels for the while statement
        whileLabelStart = f"WHILE_EXP{self.whilecount}"
        whileLabelEnd = f"WHILE_END{self.whilecount}"
        self.whilecount += 1
        
        # Write the VM commands for the while statement
        self.vmWriter.writeLabel(whileLabelStart)
        
        # Then we should always then expect "("
        self._writeAdvance(expectedType="SYMBOL", expectedValue="(")
        
        # Then we compile an expression
        self.compileExpression()
        
        # Then we expect a ")" followed by "{"
        self._writeAdvance(expectedType="SYMBOL", expectedValue=")")
        self._writeAdvance(expectedType="SYMBOL", expectedValue="{")
        
        # Now we jump to the end if the expression is false
        self.vmWriter.writeArithmetic("not")
        self.vmWriter.writeIfGoto(whileLabelEnd)
        
        # Then we compile statements
        self.compileStatements()
        
        # Then we close the bracket
        self._writeAdvance(expectedType="SYMBOL", expectedValue="}")
        
        # Finally, we need to go back to the start of the while and write the end label
        self.vmWriter.writeGoto(whileLabelStart)
        self.vmWriter.writeLabel(whileLabelEnd)
        
        # Write the closing tag for a while statement
        self._tagClose("whileStatement")
        
    # ---- Do Statement Compiler ----
    def compileDo(self):
        # Write the opening tag for a do statement
        self._tagOpen("doStatement")
        
        # Since we are compiling a do statement, we should expect a "do"
        self._writeAdvance(expectedType="KEYWORD", expectedValue="do")
        
        # Initialize number of arguments
        numArgs = 0
        
        # Then there will always be some kind of name either class name or function name
        base = str(self._tv())
        self._writeAdvance(expectedType="IDENTIFIER")
        
        # Since this name could be the class, we need to check for "."
        if self._tt() == "SYMBOL" and self._tv() == ".":
            # Write the "." and then the word after it
            self._writeAdvance(expectedType="SYMBOL", expectedValue=".")
            functionName = str(self._tv()) # Now we have the function name
            self._writeAdvance(expectedType="IDENTIFIER")
            
            # Now check if the base is in the symbol table
            if self.symbolTable.inSymbolTable(base):
                # Grab all the relevant information from the symbol table
                vmType = self.symbolTable.vmType(base)
                segment = VARMAPPING[vmType]
                index = self.symbolTable.index(base)
                
                # Push the variable onto the stack (arg 0 is THIS)
                self.vmWriter.writePush(segment, index)
                numArgs += 1
                
                # Now set the base to the type of the variable
                base = self.symbolTable.varType(base)
            
        else:
            functionName = base
            base = self.className
            # Since we are calling a method from inside the current class, we need to handle that
            self.vmWriter.writePush("pointer", 0) # Push this onto the stack
            numArgs += 1
            
        # Now we handle the parenthesis and the expression list
        self._writeAdvance(expectedType="SYMBOL", expectedValue="(")
        numArgs += self.compileExpressionList()
        self._writeAdvance(expectedType="SYMBOL", expectedValue=")")
        
        # Then we always expect a semicolon
        self._writeAdvance(expectedType="SYMBOL", expectedValue=";")
        
        # Now we write the call to the function or method
        self.vmWriter.writeCall(f"{base}.{functionName}", numArgs)
        
        # Discard the return value since we aren't in an expression and are just running the command (Prevents memory overflow)
        self.vmWriter.writePop("temp", 0)
        
        # Write the closing tag for a do statement
        self._tagClose("doStatement")
        
    # ---- Return Statement Compiler ----
    def compileReturn(self):
        # Write the opening tag for a return statement
        self._tagOpen("returnStatement")
        
        # Since we are compiling a return statement, we should expect a "return"
        self._writeAdvance(expectedType="KEYWORD", expectedValue="return")
        
        # Since there could be an expression, we need to check if it is null or an expression
        if self._tt() != "SYMBOL" or self._tv() != ";":
            self.compileExpression()
        else:
            # Handle the case of a void return by writing a 0 push
            self.vmWriter.writePush("constant", 0)
            
        # Now we can write the ";"
        self._writeAdvance(expectedType="SYMBOL", expectedValue=";")
        
        # Now we can write the VM return command
        self.vmWriter.writeReturn()
        
        # Write the closing tag for a return statement
        self._tagClose("returnStatement")
        
    # -------- Expression-Related Compilation --------
    # ---- Expression List Compiler ----
    def compileExpressionList(self):
        expressionCount = 0
        # Write the opening tag for the expressionList
        self._tagOpen("expressionList")
        
        # We are inside the parenthesis, so we should just loop through the expressions we do have
        while self._tt() != "SYMBOL" or self._tv() != ")":
            self.compileExpression()
            
            # After an expression, there could be a comma, so handle that
            if self._tt() == "SYMBOL" and self._tv() == ",":
                self._writeAdvance(expectedType="SYMBOL", expectedValue=",")
            
            # Update the number of expressions
            expressionCount += 1
        
        # Write the closing tag for the expressionList
        self._tagClose("expressionList")
        return expressionCount
    
    # ---- Expression Compiler ----
    def compileExpression(self):
        # Write the opening tag for an expression
        self._tagOpen("expression")
        
        # We always expect a term at the start of an expression, so call that immediately
        # This will push the term1's value onto the stack
        self.compileTerm()
        
        while self._tt() == "SYMBOL" and self._tv() in {'+', '-', '*', '/', '&', '|','<', '>', '='}:
            # Since every term should follow with an operator if one exists
            symbol = str(self._tv())
            self._writeAdvance(expectedType="SYMBOL")
            
            # Then we can attempt to write another term because otherwise the expression would be hanging
            # This will push term2's value onto the stack
            self.compileTerm()
            
            # Now the stack looks like [..., term1, term2]
            # So we write the appropriate VM command since stack arithmatic is post-fix
            command = ARITHMATICMAPPING[symbol]
            self.vmWriter.writeArithmetic(command)
        
        # Write the closing tag for an expression
        self._tagClose("expression")
        
    # ---- Term Compiler ----
    def compileTerm(self):
        # Write the opening tag for a term
        self._tagOpen("term")
        
        # Since we are dealing with all kinds of different terms, check which kind of term it is
        # Case #1 - Integer Constant
        if self._tt() == "INT_CONST":
            # Grab the value and push it onto the stack
            value = str(self._tv())
            self.vmWriter.writePush("constant", int(value))
            
            # Advance past the integer constant
            self._writeAdvance(expectedType="INT_CONST")
            
        # Case #2 - String Constant
        elif self._tt() == "STRING_CONST":
            # Grab the value and create the string in VM
            value = str(self._tv())
            length = len(value)
            self.vmWriter.writePush("constant", length)
            self.vmWriter.writeCall("String.new", 1)
            
            # Now we need to append each character to the string
            # The stack now looks like [..., stringObject]
            # So we don't need to push the string object pointer again
            for char in value:
                self.vmWriter.writePush("constant", ord(char))
                self.vmWriter.writeCall("String.appendChar", 2)
            
            # Advance past the string constant
            self._writeAdvance(expectedType="STRING_CONST")
            
        # Case #3 - Keywords (true, false, etc)
        elif self._tt() == "KEYWORD" and self._tv() in {"true", "false", "null", "this"}:
            # Handle each kind of keyword
            if self._tv() == "true":
                self.vmWriter.writePush("constant", 0)
                self.vmWriter.writeArithmetic("not")
            elif self._tv() in {"false", "null"}:
                self.vmWriter.writePush("constant", 0)
            elif self._tv() == "this":
                self.vmWriter.writePush("pointer", 0)
            
            # Advance past the keyword constant
            self._writeAdvance(expectedType="KEYWORD")
            
        # Case #4 - Parenthetical expression
        elif self._tt() == "SYMBOL" and self._tv() == "(":
            # There is nothing special to do here except compile the expression inside the parenthesis
            self._writeAdvance(expectedType="SYMBOL", expectedValue="(")
            self.compileExpression()
            self._writeAdvance(expectedType="SYMBOL", expectedValue=")")
            
        # Case #5 - Unary Operator Term
        elif self._tt() == "SYMBOL" and self._tv() in {"-", "~"}:
            # Save the symbol for after the term is compiled
            unaryOp = str(self._tv())
            self._writeAdvance(expectedType="SYMBOL")
            self.compileTerm()
            
            # Now the stack looks like [..., term]
            # So we can write the unary operation
            if unaryOp == "-":
                self.vmWriter.writeArithmetic("neg")
            elif unaryOp == "~":
                self.vmWriter.writeArithmetic("not")
            
        # Case #6 - Basic variable name
        elif self._tt() == "IDENTIFIER" and not(self._nextTT() == "SYMBOL" and self._nextTV() in {'[', '(', '.'}):
            # Look up the variable in the symbol table then pull it onto the stack
            varName = str(self._tv())
            vmType = self.symbolTable.vmType(varName)
            segment = VARMAPPING[vmType]
            index = self.symbolTable.index(varName)
            
            # Push the variable onto the stack
            self.vmWriter.writePush(segment, index)
            
            # Advance past the variable
            self._writeAdvance(expectedType="IDENTIFIER")
            
        # Case #7 - Array variable
        elif self._tt()== "IDENTIFIER" and (self._nextTT() == "SYMBOL" and self._nextTV() == "["):
            # Grab the base address of the array
            varName = str(self._tv())
            vmType = self.symbolTable.vmType(varName)
            segment = VARMAPPING[vmType]
            index = self.symbolTable.index(varName)
            
            self._writeAdvance(expectedType="IDENTIFIER")
            self._writeAdvance(expectedType="SYMBOL", expectedValue="[")
            self.compileExpression()
            self._writeAdvance(expectedType="SYMBOL", expectedValue="]")
            
            # Push the base onto the stack
            self.vmWriter.writePush(segment, index)
            
            # Now the stack looks like [..., index, base]
            self.vmWriter.writeArithmetic("add")
            
            # Now pop this value into THAT and then grab the value at that location and push it onto the stack
            self.vmWriter.writePop("pointer", 1)
            self.vmWriter.writePush("that", 0)
        
        # Case #8 - Subroutine call
        elif self._tt() == "IDENTIFIER" and (self._nextTT() == "SYMBOL" and self._nextTV() in {'(', '.'}):
            # Initialize number of arguments
            numArgs = 0
            
            # Then there will always be some kind of name either class name or function name
            base = str(self._tv())
            self._writeAdvance(expectedType="IDENTIFIER")
            
            # Since this name could be the class, we need to check for "."
            if self._tt() == "SYMBOL" and self._tv() == ".":
                # Write the "." and then the word after it
                self._writeAdvance(expectedType="SYMBOL", expectedValue=".")
                functionName = str(self._tv()) # Now we have the function name
                self._writeAdvance(expectedType="IDENTIFIER")
                
                # Now check if the base is in the symbol table
                if self.symbolTable.inSymbolTable(base):
                    # Grab all the relevant information from the symbol table
                    vmType = self.symbolTable.vmType(base)
                    segment = VARMAPPING[vmType]
                    index = self.symbolTable.index(base)
                    
                    # Push the variable onto the stack (arg 0 is THIS)
                    self.vmWriter.writePush(segment, index)
                    numArgs += 1
                    
                    # Now set the base to the type of the variable
                    base = self.symbolTable.varType(base)
                
            else:
                functionName = base
                base = self.className
                # Since we are calling a method from inside the current class, we need to handle that
                self.vmWriter.writePush("pointer", 0) # Push this onto the stack
                numArgs += 1
                
            # Now we handle the parenthesis and the expression list
            self._writeAdvance(expectedType="SYMBOL", expectedValue="(")
            numArgs += self.compileExpressionList()
            self._writeAdvance(expectedType="SYMBOL", expectedValue=")")
            
            # Now we write the call to the function or method
            self.vmWriter.writeCall(f"{base}.{functionName}", numArgs)
        
        # Handle errors (just in case)
        else:
            raise ValueError(f"Invalid term '{self._tv()}' with token type '{self._tt()}'")
                
        # Write the closing tag for a term
        self._tagClose("term")

# ----------------------------- Main Program ----------------------------
if __name__ == "__main__":
    # Handle command line arguments and input
    args = parser.parse_args()
    input = str(args.filename)
    output_tokens = args.tokens
    writeXML = args.xml
    
    # Check if input file is a full path or relative
    if not os.path.isabs(input):
        input = os.path.join(cwd, input)
    
    # Determine if input is a file or directory and gather .jack files
    if os.path.isdir(input):
        files = [f for f in os.listdir(input) if f.endswith(".jack")]
        for i in range(len(files)):
            files[i] = os.path.join(input, files[i])
    else:
        files = [input]
    
    # Now process each file
    for file in files:
        tokenizer = Tokenizer(file)
        tokenizer.tokenize()
        output_path = os.path.splitext(file)[0] + "T.xml"
        
        # Write the tokenized output for testing
        if output_tokens:
            tokens = tokenizer.write_output(output_path)
            print(f"Tokenized {os.path.basename(file)} to {os.path.basename(output_path)}")
        else:
            tokens = tokenizer.close()

        # Now run the Compilation Engine
        output_path = os.path.splitext(file)[0] + ".xml"
        compilation_engine = CompilationEngine(tokens, output_path, writeXML=writeXML)
        
        compilation_engine.compileClass()
        if writeXML:
            print(f"Wrote XML parse tree to {os.path.basename(compilation_engine.output_path)}")
        print(f"Compiled {os.path.basename(file)} to {os.path.basename(compilation_engine.output_path).replace('.xml', '.vm')}")
        
        compilation_engine.close()