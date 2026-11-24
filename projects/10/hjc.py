'''
Hack JACK Compiler (HJC)

Author: James Giffen
Date: 11/18/2025
'''

import os
import argparse
from typing import List

# Set up parsing for command line arguments
parser = argparse.ArgumentParser(prog="hjc", description="Hack JACK Compiler")
parser.add_argument("filename", help="Path to the .jack file/directory to be compiled", type=str)
parser.add_argument("-t", "--tokens", help="Will enable the outputting of the tokens to an XML file", action="store_true", default=False)

# Set up current directory
cwd = os.getcwd()

# Define constants
SYMBOLS = {'{', '}', '(', ')', '[', ']', '.', ',', ';', '+', '-', '*', '/', '&', '|', '<', '>', '=', '~'}

KEYWORDS = ['class', 'constructor', 'function', 'method', 'field', 'static', 'var', 'int', 'char', 'boolean', 'void', 'true', 'false', 'null', 'this', 'let', 'do', 'if', 'else', 'while', 'return']

# ----------------------------- Token Class -----------------------------
class Token:
    def __init__(self, token_type: str, value: str | int, tokenXML: str = ""):
        self.token_type = token_type
        self.token_XML = tokenXML
        self.value = value

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

# ------------------------- CompilationEngine Class -------------------------
class CompilationEngine:
    def __init__(self, tokens: List[Token], output_path: str):
        # Take in the tokens from the Tokenizer
        self.tokens = tokens
        
        # We want to create / write to this file in real time to ensure we get the indents right
        self.output_path = output_path
        self.output_file = open(self.output_path, 'w')
        
        # Determine indentation level
        self.indent_level = 0
        
        # Current index/current token
        self.currentIndex = 0
        self.currentToken: Token | None = self.tokens[0] if self.tokens else None
    
    # ---- General Helpers ----
    def close(self):
        # Close the output file when done since we are editing it in real time
        self.output_file.close()
    
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
        self._write_line(f"<{tag}>")
        self.indent_level += 1
        
    def _tagClose(self, tag: str):
        self.indent_level -= 1
        self._write_line(f"</{tag}>")
        
    # ---- Class Compiler ----
    def compileClass(self):
        # Write the open tag for the class
        self._tagOpen("class")
        
        # Now we can write the first token which should be a KEYWORD "class"
        self._writeAdvance(expectedType="KEYWORD", expectedValue="class")
        
        # Now we can write the name of the class which should be an IDENTIFIER
        expectedClassName = os.path.basename(self.output_path).replace('.xml', '')
        self._writeAdvance(expectedType="IDENTIFIER", expectedValue=expectedClassName)
        
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
        self._writeAdvance(expectedType="KEYWORD")
        
        # Write the type of variable. Since it could also be a class, we need to handle that case
        if self._tt() == "KEYWORD" and self._tv() in {"int", "char", "boolean"}:
            self._writeAdvance(expectedType="KEYWORD")
        elif self._tt() == "IDENTIFIER":
            self._writeAdvance(expectedType="IDENTIFIER")
        else:
            raise ValueError(f"Unexpected token in type: {self._tt()} {self._tv()}")
        
        # Write the variable name
        self._writeAdvance(expectedType="IDENTIFIER")
        
        # Since we can define multiple variables, we need to loop through the commas and their names
        while self._tt() == "SYMBOL" and self._tv() == ",":
            self._writeAdvance(expectedType="SYMBOL", expectedValue=",")
            self._writeAdvance(expectedType="IDENTIFIER")
        
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
        self._writeAdvance(expectedType="KEYWORD")
        
        # Now we can write the type that we are expecting to output
        if self._tt() == "KEYWORD" and self._tv() in {"int", "char", "boolean", "void"}:
            self._writeAdvance(expectedType="KEYWORD")
        elif self._tt() == "IDENTIFIER":
            self._writeAdvance(expectedType="IDENTIFIER")
        else:
            raise ValueError(f"Invalid return type: {self._tt()} {self._tv()}")
        
        # Now write the name of the function
        self._writeAdvance(expectedType="IDENTIFIER")
        
        # Now we are expecting the parameter list so handle the parenthesis and then call the parameter list
        self._writeAdvance(expectedType="SYMBOL", expectedValue="(")
        self.compileParameterList()
        self._writeAdvance(expectedType="SYMBOL", expectedValue=")")
        
        # Then call the subroutine body
        self.compileSubroutineBody()
        
        # Write the closing tag for a subroutine declaration
        self._tagClose("subroutineDec")

        
    # ---- Parameter List Compiler ----
    def compileParameterList(self):
        # Write the open tag for the parameterList
        self._tagOpen("parameterList")
        
        # We can check if there are any parameters and the iterate through them
        if self._tt() in {"KEYWORD", "IDENTIFIER"}:
            if self._tt() == "KEYWORD" and self._tv() in ("int", "char", "boolean"):
                self._writeAdvance(expectedType="KEYWORD")
            elif self._tt() == "IDENTIFIER":
                self._writeAdvance(expectedType="IDENTIFIER")
            else:
                raise ValueError(f"Unexpected token in type: {self._tt()} {self._tv()}")
            
            # Then write the parameter name
            self._writeAdvance(expectedType="IDENTIFIER")
            
            while self._tt() == "SYMBOL" and self._tv() == ",":
                # Write the comma
                self._writeAdvance(expectedType="SYMBOL", expectedValue=",")
                
                # Then chen check which kind of variable it is
                if self._tt() == "KEYWORD" and self._tv() in ("int", "char", "boolean"):
                    self._writeAdvance(expectedType="KEYWORD")
                elif self._tt() == "IDENTIFIER":
                    self._writeAdvance(expectedType="IDENTIFIER")
                else:
                    raise ValueError(f"Unexpected token in type: {self._tt()} {self._tv()}")
                
                # Then write the parameter name
                self._writeAdvance(expectedType="IDENTIFIER")
            
        # Write the closing tag for a parameterList
        self._tagClose("parameterList")
    
    # ---- Subroutine Body Compiler ----
    def compileSubroutineBody(self):
        # Write the open tag for the Subroutine Body
        self._tagOpen("subroutineBody")
        
        # Now write the open bracket for the subroutine body
        self._writeAdvance(expectedType="SYMBOL", expectedValue="{")
        
        # Now we search for variable declarations as they HAVE to be first
        while self._tt() == "KEYWORD" and self._tv() == "var":
            self.compileVarDec()
        
        # Then we compile all the statments
        self.compileStatements()
        
        # Write the closing bracket for the subroutine body
        self._writeAdvance(expectedType="SYMBOL", expectedValue="}")
        
        # Write the closing tag for the Subroutine Body
        self._tagClose("subroutineBody")
        
    # ---- Variables Compiler ----
    def compileVarDec(self):
        
        # Write the open tag for the variable declaration
        self._tagOpen("varDec")
        
        # Write the var statement
        self._writeAdvance(expectedType="KEYWORD", expectedValue="var")
        
        # Write the type of variable. Since it could also be a class, we need to handle that case
        if self._tt() == "KEYWORD" and self._tv() in {"int", "char", "boolean"}:
            self._writeAdvance(expectedType="KEYWORD")
        elif self._tt() == "IDENTIFIER":
            self._writeAdvance(expectedType="IDENTIFIER")
        else:
            raise ValueError(f"Unexpected token in type: {self._tt()} {self._tv()}")
        
        # Write the variable name
        self._writeAdvance(expectedType="IDENTIFIER")
        
        # Since we can define multiple variables, we need to loop through the commas and their names
        while self._tt() == "SYMBOL" and self._tv() == ",":
            self._writeAdvance(expectedType="SYMBOL", expectedValue=",")
            self._writeAdvance(expectedType="IDENTIFIER")
        
        # Now we have to expect a ; to end the delcaration
        self._writeAdvance(expectedType="SYMBOL", expectedValue=";")
        
        # Write the closing tag for the variable declaration
        self._tagClose("varDec")
    
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
        self._writeAdvance(expectedType="IDENTIFIER")
        
        # Since we could be dealing with an array we can check for "["
        if self._tt() == "SYMBOL" and self._tv() == "[":
            self._writeAdvance(expectedType="SYMBOL", expectedValue="[")
            self.compileExpression()
            self._writeAdvance(expectedType="SYMBOL", expectedValue="]")
            
        # We should now always expect an equals sign
        self._writeAdvance(expectedType="SYMBOL", expectedValue="=")
        
        # Now it could be any expression so we call that
        self.compileExpression()
        
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
        
        # Then we compile statements
        self.compileStatements()
        
        # Then we close the bracket
        self._writeAdvance(expectedType="SYMBOL", expectedValue="}")
        
        # If there is an else, handle it
        if self._tt() == "KEYWORD" and self._tv() == "else":
            self._writeAdvance(expectedType="KEYWORD", expectedValue="else")
            self._writeAdvance(expectedType="SYMBOL", expectedValue="{")
            self.compileStatements()
            self._writeAdvance(expectedType="SYMBOL", expectedValue="}")
        
        # Write the closing tag for an if statement
        self._tagClose("ifStatement")
        
    # ---- While Statement Compiler ----
    def compileWhile(self):
        # Write the opening tag for a while statement
        self._tagOpen("whileStatement")
        
        # Since we are compiling a while statement, we should expect a "while"
        self._writeAdvance(expectedType="KEYWORD", expectedValue="while")
        
        # Then we should always then expect "("
        self._writeAdvance(expectedType="SYMBOL", expectedValue="(")
        
        # Then we compile an expression
        self.compileExpression()
        
        # Then we expect a ")" followed by "{"
        self._writeAdvance(expectedType="SYMBOL", expectedValue=")")
        self._writeAdvance(expectedType="SYMBOL", expectedValue="{")
        
        # Then we compile statements
        self.compileStatements()
        
        # Then we close the bracket
        self._writeAdvance(expectedType="SYMBOL", expectedValue="}")
        
        # Write the closing tag for a while statement
        self._tagClose("whileStatement")
        
    # ---- Do Statement Compiler ----
    def compileDo(self):
        # Write the opening tag for a do statement
        self._tagOpen("doStatement")
        
        # Since we are compiling a do statement, we should expect a "do"
        self._writeAdvance(expectedType="KEYWORD", expectedValue="do")
        
        # Then there will always be some kind of name either class name or function name
        self._writeAdvance(expectedType="IDENTIFIER")
        
        # Since this name could be the class, we need to check for "."
        while self._tt() == "SYMBOL" and self._tv() == ".":
            # Write the "." and then the word after it
            self._writeAdvance(expectedType="SYMBOL", expectedValue=".")
            self._writeAdvance(expectedType="IDENTIFIER")
            
        # Now we handle the parenthesis and the expression list
        self._writeAdvance(expectedType="SYMBOL", expectedValue="(")
        self.compileExpressionList()
        self._writeAdvance(expectedType="SYMBOL", expectedValue=")")
        
        # Then we always expect a semicolon
        self._writeAdvance(expectedType="SYMBOL", expectedValue=";")
        
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
            
        # Now we can write the ";"
        self._writeAdvance(expectedType="SYMBOL", expectedValue=";")
        
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
        self.compileTerm()
        
        while self._tt() == "SYMBOL" and self._tv() in {'+', '-', '*', '/', '&', '|','<', '>', '='}:
            # Since every term should follow with an operator if one exists
            self._writeAdvance(expectedType="SYMBOL")
            
            # Then we can attempt to write another term because otherwise the expression would be hanging
            self.compileTerm()
        
        # Write the closing tag for an expression
        self._tagClose("expression")
        
    # ---- Term Compiler ----
    def compileTerm(self):
        # Write the opening tag for a term
        self._tagOpen("term")
        
        # Since we are dealing with all kinds of different terms, check which kind of term it is
        # Case #1 - Integer Constant
        if self._tt() == "INT_CONST":
            self._writeAdvance(expectedType="INT_CONST")
            
        # Case #2 - String Constant
        elif self._tt() == "STRING_CONST":
            self._writeAdvance(expectedType="STRING_CONST")
            
        # Case #3 - Keywords (true, false, etc)
        elif self._tt() == "KEYWORD" and self._tv() in {"true", "false", "null", "this"}:
            self._writeAdvance(expectedType="KEYWORD")
            
        # Case #4 - Parenthetical expression
        elif self._tt() == "SYMBOL" and self._tv() == "(":
            self._writeAdvance(expectedType="SYMBOL", expectedValue="(")
            self.compileExpression()
            self._writeAdvance(expectedType="SYMBOL", expectedValue=")")
            
        # Case #5 - Unary Operator Term
        elif self._tt() == "SYMBOL" and self._tv() in {"-", "~"}:
            self._writeAdvance(expectedType="SYMBOL")
            self.compileTerm()
            
        # Case #6 - Basic variable name
        elif self._tt() == "IDENTIFIER" and not(self._nextTT() == "SYMBOL" and self._nextTV() in {'[', '(', '.'}):
            self._writeAdvance(expectedType="IDENTIFIER")
            
        # Case #7 - Array variable
        elif self._tt()== "IDENTIFIER" and (self._nextTT() == "SYMBOL" and self._nextTV() == "["):
            self._writeAdvance(expectedType="IDENTIFIER")
            self._writeAdvance(expectedType="SYMBOL", expectedValue="[")
            self.compileExpression()
            self._writeAdvance(expectedType="SYMBOL", expectedValue="]")
        
        # Case #8 - Subroutine call
        elif self._tt() == "IDENTIFIER" and (self._nextTT() == "SYMBOL" and self._nextTV() in {'(', '.'}):
            self._writeAdvance(expectedType="IDENTIFIER")
            
            # External function call "Identifier.Identifier(expressionList)"
            if self._tt() == "SYMBOL" and self._tv() == ".":
                self._writeAdvance(expectedType="SYMBOL", expectedValue=".")
                self._writeAdvance(expectedType="IDENTIFIER")
                self._writeAdvance(expectedType="SYMBOL", expectedValue="(")
                self.compileExpressionList()
                self._writeAdvance(expectedType="SYMBOL", expectedValue=")")
            
            # Internal function call "Identifier(expressionList)"
            elif self._tt() == "SYMBOL" and self._tv() == "(":
                self._writeAdvance(expectedType="SYMBOL", expectedValue="(")
                self.compileExpressionList()
                self._writeAdvance(expectedType="SYMBOL", expectedValue=")")
            
            else:
                raise ValueError(f"Invalid Subroutine Call term '{self._tv()}' with token type '{self._tt()}'")
        
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
    output_tokens = True
    
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
        compilation_engine = CompilationEngine(tokens, output_path)
        
        compilation_engine.compileClass()
        print(f"Compiled {os.path.basename(file)} to {os.path.basename(compilation_engine.output_path)}")
        compilation_engine.close()