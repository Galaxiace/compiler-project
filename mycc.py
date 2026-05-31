#!/usr/bin/env python3
"""
MiniCompiler - Main entry point (Sprint 8)
Полноценный CLI с поддержкой всех режимов компиляции, оптимизаций и диагностики.

Usage:
  ./mycc [options] <sourcefile>
  ./mycc --help
  ./mycc --version
"""

import argparse
import sys
import os
from pathlib import Path
from typing import Optional, List, Tuple

# Version info
__version__ = "1.0.0"
__target__ = "x86_64-linux-gnu"
from datetime import date
__build_date__ = date.today().strftime("%Y-%m-%d")

# Импорты компилятора
from lexer.scanner import Scanner
from lexer.token import Token, TokenType
from lexer.errors import LexicalError

from parser.parser import Parser, ParseError
from parser.pretty_printer import PrettyPrinter
from parser.dot_generator import DotGenerator
from parser.json_generator import JsonGenerator
from parser.ast import ProgramNode

from semantic.analyzer import SemanticAnalyzer
from semantic.errors import SemanticError

from ir.ir_generator import IRGenerator
from ir.ir_writer import IRWriter
from ir.dot_generator import IRDotGenerator
from ir.control_flow import IRProgram

# Optional import for optimizer
try:
    from ir.optimizer import IROptimizer

    HAS_OPTIMIZER = True
except ImportError:
    HAS_OPTIMIZER = False

from codegen.x86_generator import X86Generator

# Импорты системы ошибок
from errors import (
    ErrorHandler, ErrorCategory, ErrorCodes, ErrorFactory,
    CompilerMessage, Colors
)


class CompilerError(Exception):
    """Base class for compiler errors"""

    def __init__(self, message: str, exit_code: int = 1):
        self.message = message
        self.exit_code = exit_code
        super().__init__(message)


class CompilerPipeline:
    """Main compiler pipeline orchestrator with unified error handling"""

    def __init__(self, args):
        self.args = args

        # Настройка цвета
        if args.color == 'never' or (args.color == 'auto' and not sys.stdout.isatty()):
            Colors.disable()

        # Настройка системы ошибок
        warning_level = "all" if getattr(args, 'Wall', False) else "default"
        self.error_handler = ErrorHandler(
            max_errors=getattr(args, 'max_errors', 20),
            warning_level=warning_level,
            warnings_as_errors=getattr(args, 'Werror', False),
            output_format=getattr(args, 'format', 'human'),
            color=not (args.color == 'never' or (args.color == 'auto' and not sys.stdout.isatty())),
            source_file=args.input if hasattr(args, 'input') else "program.src"
        )

        # Для статистики оптимизаций
        self.optimization_stats = None
        self.before_optimization_instructions = 0
        self.after_optimization_instructions = 0

    def run(self) -> int:
        """Main pipeline execution"""
        try:
            # Загружаем исходный код для контекста ошибок
            source = self._read_source()
            self.error_handler.load_source(source)

            if self.args.verbose:
                print(f"{Colors.CYAN}==> Reading source file: {self.args.input}{Colors.NC}", file=sys.stderr)
                print(f"{Colors.CYAN}==> Source size: {len(source)} bytes{Colors.NC}", file=sys.stderr)

            # Phase 1: Lexer
            if self.args.mode == 'preprocess':
                return self._run_lexer_output(source)

            if self.args.verbose:
                print(f"{Colors.CYAN}==> Phase 1: Lexical analysis...{Colors.NC}", file=sys.stderr)

            tokens = self._run_lexer_phase(source)

            if self.args.verbose:
                print(f"{Colors.CYAN}    Tokens generated: {len(tokens)}{Colors.NC}", file=sys.stderr)

            if self.error_handler.too_many_errors():
                self.error_handler.print_summary()
                return 1

            # Phase 2: Parser
            if self.args.verbose:
                print(f"{Colors.CYAN}==> Phase 2: Parsing...{Colors.NC}", file=sys.stderr)

            ast = self._run_parser_phase(tokens)

            if self.args.verbose:
                func_count = len(
                    [d for d in ast.declarations if hasattr(d, 'node_type') and d.node_type.name == 'FUNCTION_DECL'])
                print(f"{Colors.CYAN}    Functions parsed: {func_count}{Colors.NC}", file=sys.stderr)

            if self.error_handler.too_many_errors():
                self.error_handler.print_summary()
                return 1

            if self.args.mode == 'ast':
                return self._output_ast(ast)

            # Phase 3: Semantic Analysis
            if self.args.verbose:
                print(f"{Colors.CYAN}==> Phase 3: Semantic analysis...{Colors.NC}", file=sys.stderr)

            semantic_ok, analyzer, decorated_ast = self._run_semantic_phase(ast)

            if self.args.verbose:
                if semantic_ok:
                    print(f"{Colors.GREEN}    Semantic analysis: PASSED{Colors.NC}", file=sys.stderr)
                else:
                    print(f"{Colors.RED}    Semantic analysis: FAILED{Colors.NC}", file=sys.stderr)

            if self.error_handler.too_many_errors():
                self.error_handler.print_summary()
                return 1

            if not semantic_ok:
                self.error_handler.print_summary()
                return 1

            if self.args.mode == 'semantic':
                return self._output_semantic(analyzer, decorated_ast)

            # Phase 4: IR Generation
            if self.args.verbose:
                print(f"{Colors.CYAN}==> Phase 4: IR Generation...{Colors.NC}", file=sys.stderr)

            ir_program = self._run_ir_phase(ast)

            if self.args.verbose:
                total_instr = sum(len(b.instructions) for f in ir_program.functions for b in f.blocks)
                print(f"{Colors.CYAN}    Functions: {len(ir_program.functions)}{Colors.NC}", file=sys.stderr)
                print(f"{Colors.CYAN}    Instructions: {total_instr}{Colors.NC}", file=sys.stderr)

            if self.args.optimize:
                if self.args.verbose:
                    before = self.before_optimization_instructions
                    after = self.after_optimization_instructions
                    reduction = ((before - after) / before * 100) if before > 0 else 0
                    print(
                        f"{Colors.YELLOW}    Optimization applied: {before} → {after} instructions ({reduction:.0f}% reduction){Colors.NC}",
                        file=sys.stderr)

            if self.error_handler.too_many_errors():
                self.error_handler.print_summary()
                return 1

            if self.args.mode == 'ir':
                return self._output_ir(ir_program)

            # Phase 5: Code Generation
            if self.args.mode == 'compile':
                if self.args.verbose:
                    print(f"{Colors.CYAN}==> Phase 5: Code Generation...{Colors.NC}", file=sys.stderr)

                result = self._run_codegen(ir_program)

                if self.args.verbose and result == 0:
                    output_file = self.args.output or "a.out"
                    size = os.path.getsize(output_file) if os.path.exists(output_file) else 0
                    print(f"{Colors.GREEN}==> Compilation successful!{Colors.NC}", file=sys.stderr)
                    print(f"{Colors.GREEN}    Output: {output_file} ({size} bytes){Colors.NC}", file=sys.stderr)

                self.error_handler.print_summary()
                return result

        except CompilerError as e:
            if "Semantic errors detected" not in e.message:
                self.error_handler.add_error('E999', e.message, ErrorCategory.CODEGEN)
            self.error_handler.print_summary()
            return e.exit_code
        except Exception as e:
            self.error_handler.add_error('E999', f"Internal compiler error: {e}", ErrorCategory.CODEGEN)
            self.error_handler.print_summary()
            if self.args.verbose:
                import traceback
                traceback.print_exc()
            return 1

        self.error_handler.print_summary()
        return 0

    def _run_lexer_phase(self, source: str) -> List[Token]:
        """Run lexer and return tokens"""
        scanner = Scanner(source)
        tokens = scanner.scan_tokens()

        for error in scanner.errors:
            # Определяем код ошибки по типу
            msg = error.message.lower()
            if "invalid character" in msg:
                code = ErrorCodes.LEX_INVALID_CHAR
            elif "unterminated string" in msg:
                code = ErrorCodes.LEX_UNTERMINATED_STRING
            elif "unterminated comment" in msg:
                code = ErrorCodes.LEX_UNTERMINATED_COMMENT
            elif "invalid number" in msg:
                code = ErrorCodes.LEX_INVALID_NUMBER
            elif "identifier too long" in msg:
                code = ErrorCodes.LEX_IDENTIFIER_TOO_LONG
            elif "integer out of range" in msg:
                code = ErrorCodes.LEX_INTEGER_OUT_OF_RANGE
            else:
                code = "E000"

            self.error_handler.add_error(
                code, error.message, ErrorCategory.LEXICAL,
                line=error.line, column=error.column
            )

        return tokens

    def _run_lexer_output(self, source: str) -> int:
        """Just run lexer and output tokens"""
        tokens = self._run_lexer_phase(source)

        output_lines = []
        for token in tokens:
            if token.type == TokenType.END_OF_FILE:
                output_lines.append(f"{token.line}:{token.column} END_OF_FILE \"\"")
            else:
                literal_str = f" {token.literal}" if token.literal is not None else ""
                output_lines.append(f"{token.line}:{token.column} {token.type.name} \"{token.lexeme}\"{literal_str}")

        output = '\n'.join(output_lines)

        if self.args.output:
            with open(self.args.output, 'w') as f:
                f.write(output)
            if self.args.verbose:
                print(f"{Colors.GREEN}Lexer output written to {self.args.output}{Colors.NC}", file=sys.stderr)
        else:
            print(output)

        return 0 if not self.error_handler.has_errors() else 1

    def _run_parser_phase(self, tokens: List[Token]) -> ProgramNode:
        """Run parser and return AST"""
        parser = Parser(tokens)

        try:
            ast = parser.parse()
        except ParseError as e:
            self.error_handler.add_error(
                ErrorCodes.SYNTAX_UNEXPECTED_TOKEN, e.message,
                ErrorCategory.SYNTAX, line=e.line, column=e.column
            )
            raise CompilerError("Parse failed", 1)

        for error in parser.errors:
            self.error_handler.add_error(
                ErrorCodes.SYNTAX_UNEXPECTED_TOKEN, error.message,
                ErrorCategory.SYNTAX, line=error.line, column=error.column
            )

        return ast

    def _run_semantic_phase(self, ast: ProgramNode) -> Tuple[bool, SemanticAnalyzer, any]:
        """Run semantic analysis"""
        analyzer = SemanticAnalyzer()
        decorated_ast = analyzer.analyze(ast)

        for error in analyzer.get_errors():
            error_code = self._get_semantic_error_code(error)

            # Формируем контекст и подсказки
            context = self._get_error_context(error)
            suggestion = self._get_error_suggestion(error)

            self.error_handler.add_error(
                error_code, error.message, ErrorCategory.SEMANTIC,
                line=error.line, column=error.column,
                context=context,
                suggestion=suggestion
            )

        return len(analyzer.get_errors()) == 0, analyzer, decorated_ast

    def _run_ir_phase(self, ast: ProgramNode, analyzer: SemanticAnalyzer = None) -> IRProgram:
        """Generate IR from AST"""
        # Всегда создаём новый анализатор для IR генерации
        sem_analyzer = SemanticAnalyzer()
        sem_analyzer.analyze(ast)

        if sem_analyzer.get_errors():
            raise CompilerError("Semantic errors detected", 1)

        generator = IRGenerator(sem_analyzer.get_symbol_table())
        generator.analyzer = sem_analyzer
        ir_program = generator.generate_from_ast(ast)

        # Сохраняем количество инструкций до оптимизации
        self.before_optimization_instructions = sum(
            len(block.instructions)
            for func in ir_program.functions
            for block in func.blocks
        )

        # Apply optimizations if requested
        if self.args.optimize and HAS_OPTIMIZER:
            try:
                optimizer = IROptimizer(ir_program)
                ir_program = optimizer.optimize()

                # Сохраняем количество инструкций после оптимизации
                self.after_optimization_instructions = sum(
                    len(block.instructions)
                    for func in ir_program.functions
                    for block in func.blocks
                )

                # Получаем статистику оптимизаций
                if hasattr(optimizer, 'get_stats'):
                    self.optimization_stats = optimizer.get_stats()
                else:
                    self.optimization_stats = {
                        'constant_folding': getattr(optimizer, 'constant_folding_count', 0),
                        'constant_propagation': getattr(optimizer, 'constant_propagation_count', 0),
                        'dead_code_removed': getattr(optimizer, 'dead_code_removed_count', 0),
                        'unreachable_blocks_removed': getattr(optimizer, 'unreachable_blocks_removed', 0),
                        'total_instructions_before': self.before_optimization_instructions,
                        'total_instructions_after': self.after_optimization_instructions,
                        'reduction_percent': int(
                            (self.before_optimization_instructions - self.after_optimization_instructions) /
                            self.before_optimization_instructions * 100
                        ) if self.before_optimization_instructions > 0 else 0
                    }

                if self.args.verbose:
                    print(f"{Colors.CYAN}Optimization applied:{Colors.NC}", file=sys.stderr)
                    if hasattr(optimizer, 'print_stats'):
                        print(optimizer.print_stats(), file=sys.stderr)

            except ImportError as e:
                if self.args.verbose:
                    print(f"Optimizer not available: {e}", file=sys.stderr)
            except Exception as e:
                if self.args.verbose:
                    print(f"Optimization failed: {e}", file=sys.stderr)
                    import traceback
                    traceback.print_exc()

        return ir_program

    def _run_codegen(self, ir_program: IRProgram) -> int:
        """Generate assembly and optionally assemble/link"""
        # Generate assembly
        generator = X86Generator(ir_program)
        asm_code = generator.generate()

        output_file = self.args.output
        if not output_file:
            base = Path(self.args.input).stem
            if self.args.assemble_only:
                output_file = f"{base}.asm"
            elif self.args.compile_only:
                output_file = f"{base}.o"
            else:
                output_file = "a.out"

        # Write assembly
        if self.args.assemble_only:
            with open(output_file, 'w') as f:
                f.write(asm_code)

            if self.args.verbose:
                print(f"{Colors.GREEN}Assembly written to {output_file}{Colors.NC}", file=sys.stderr)
            return 0

        elif self.args.compile_only:
            # Assemble to object file
            import subprocess
            import tempfile

            with tempfile.NamedTemporaryFile(mode='w', suffix='.asm', delete=False) as f:
                f.write(asm_code)
                asm_file = f.name

            try:
                result = subprocess.run(['nasm', '-f', 'elf64', '-o', output_file, asm_file],
                                        capture_output=True, text=True)
                if result.returncode != 0:
                    self.error_handler.add_error(
                        'E500', f"Assembly failed: {result.stderr}",
                        ErrorCategory.CODEGEN
                    )
                    return 1

                if self.args.verbose:
                    print(f"{Colors.GREEN}Object file written to {output_file}{Colors.NC}", file=sys.stderr)
            finally:
                try:
                    os.unlink(asm_file)
                except:
                    pass
            return 0

        else:
            # Full compilation to executable
            import subprocess
            import tempfile

            with tempfile.NamedTemporaryFile(mode='w', suffix='.asm', delete=False) as f:
                f.write(asm_code)
                asm_file = f.name

            obj_file = f"{asm_file}.o"
            runtime_obj = f"{asm_file}_runtime.o"

            try:
                # Assemble main program
                if self.args.verbose:
                    print(f"{Colors.YELLOW}Assembling...{Colors.NC}", file=sys.stderr)
                result = subprocess.run(['nasm', '-f', 'elf64', '-o', obj_file, asm_file],
                                        capture_output=True, text=True)
                if result.returncode != 0:
                    self.error_handler.add_error(
                        'E500', f"Assembly failed: {result.stderr}",
                        ErrorCategory.CODEGEN
                    )
                    return 1

                # Assemble runtime
                runtime_dir = Path(__file__).parent / "runtime"
                result = subprocess.run(['nasm', '-f', 'elf64', '-o', runtime_obj,
                                         str(runtime_dir / 'runtime.asm')],
                                        capture_output=True, text=True)
                if result.returncode != 0:
                    self.error_handler.add_error(
                        'E500', f"Runtime assembly failed: {result.stderr}",
                        ErrorCategory.CODEGEN
                    )
                    return 1

                # Link with gcc instead of ld to automatically include libc
                if self.args.verbose:
                    print(f"{Colors.YELLOW}Linking...{Colors.NC}", file=sys.stderr)
                result = subprocess.run(['gcc', '-no-pie', '-o', output_file, runtime_obj, obj_file],
                                        capture_output=True, text=True)
                if result.returncode != 0:
                    # Fallback: try with ld and explicit libc
                    result = subprocess.run(['ld', '-o', output_file, runtime_obj, obj_file,
                                             '-lc', '-dynamic-linker', '/lib64/ld-linux-x86-64.so.2'],
                                            capture_output=True, text=True)
                    if result.returncode != 0:
                        self.error_handler.add_error(
                            'E501', f"Linking failed: {result.stderr}",
                            ErrorCategory.LINKER
                        )
                        return 1

                if self.args.verbose:
                    print(f"{Colors.GREEN}Executable written to {output_file}{Colors.NC}", file=sys.stderr)

                # Make executable
                os.chmod(output_file, 0o755)

            finally:
                # Cleanup temp files
                for f in [asm_file, obj_file, runtime_obj]:
                    try:
                        if os.path.exists(f):
                            os.unlink(f)
                    except:
                        pass

        return 0

    def _output_ast(self, ast: ProgramNode) -> int:
        """Output AST in specified format"""
        if self.args.ast_format == 'dot':
            generator = DotGenerator()
            output = generator.generate(ast)
        elif self.args.ast_format == 'json':
            generator = JsonGenerator()
            output = generator.generate(ast)
        else:
            printer = PrettyPrinter()
            printer.visit(ast)
            output = printer.get_output()

        if self.args.output:
            with open(self.args.output, 'w') as f:
                f.write(output)
        else:
            print(output)

        return 0

    def _output_semantic(self, analyzer: SemanticAnalyzer, decorated_ast) -> int:
        """Output semantic analysis results"""
        print("=" * 60)
        print("SYMBOL TABLE")
        print("=" * 60)
        print(analyzer.get_symbol_table().dump())

        if self.args.verbose:
            from semantic.decorated_ast import DecoratedASTPrinter
            print("\n" + "=" * 60)
            print("DECORATED AST")
            print("=" * 60)
            printer = DecoratedASTPrinter()
            print(printer.print(decorated_ast))

        return 0

    def _output_ir(self, ir_program: IRProgram) -> int:
        """Output IR in specified format"""
        output = ""

        # Добавляем статистику если запрошена
        if getattr(self.args, 'stats', False):
            output += self._generate_ir_stats(ir_program) + "\n"

        # Генерируем IR в нужном формате
        if self.args.ir_format == 'dot':
            dot_gen = IRDotGenerator()
            ir_output = []
            for func in ir_program.functions:
                ir_output.append(f"// CFG for function: {func.name}")
                ir_output.append(dot_gen.generate_function(func))
            ir_output = "\n".join(ir_output)
        elif self.args.ir_format == 'json':
            from ir.json_generator import IRJsonGenerator
            json_gen = IRJsonGenerator()
            ir_output = json_gen.generate(ir_program)
        else:
            writer = IRWriter()
            ir_output = writer.write_program(ir_program)

        output += ir_output

        if self.args.output:
            with open(self.args.output, 'w') as f:
                f.write(output)
        else:
            print(output)

        return 0

    def _generate_ir_stats(self, ir_program: IRProgram) -> str:
        """Генерирует статистику по IR программе"""
        from ir.ir_instructions import IROpcode

        lines = []
        lines.append("=" * 60)
        lines.append("IR STATISTICS")
        lines.append("=" * 60)

        total_instructions = 0
        instruction_counts = {}
        total_blocks = 0
        total_temporaries = 0

        for func in ir_program.functions:
            total_blocks += len(func.blocks)
            total_temporaries += func.temp_counter

            for block in func.blocks:
                for instr in block.instructions:
                    total_instructions += 1
                    opcode = instr.opcode.name
                    instruction_counts[opcode] = instruction_counts.get(opcode, 0) + 1

        lines.append(f"Total functions:      {len(ir_program.functions)}")
        lines.append(f"Total basic blocks:   {total_blocks}")
        lines.append(f"Total instructions:   {total_instructions}")
        lines.append(f"Total temporaries:    {total_temporaries}")
        lines.append("")

        if instruction_counts:
            lines.append("Instructions by type:")
            for opcode, count in sorted(instruction_counts.items(), key=lambda x: -x[1]):
                percentage = (count / total_instructions * 100) if total_instructions > 0 else 0
                lines.append(f"  {opcode:20} {count:5} ({percentage:5.1f}%)")

        lines.append("=" * 60)

        # Добавляем статистику оптимизаций
        if hasattr(self, 'optimization_stats') and self.optimization_stats:
            stats = self.optimization_stats
            lines.append("")
            lines.append("=" * 60)
            lines.append("OPTIMIZATION STATISTICS")
            lines.append("=" * 60)

            if stats.get('constant_folding', 0) > 0:
                lines.append(f"Constant folding: {stats['constant_folding']} expressions folded")
            if stats.get('constant_propagation', 0) > 0:
                lines.append(f"Constant propagation: {stats['constant_propagation']} variables propagated")
            if stats.get('dead_code_removed', 0) > 0:
                lines.append(f"Dead code elimination: {stats['dead_code_removed']} instructions removed")
            if stats.get('unreachable_blocks_removed', 0) > 0:
                lines.append(f"Unreachable blocks removed: {stats['unreachable_blocks_removed']} blocks")

            if hasattr(self, 'before_optimization_instructions') and hasattr(self, 'after_optimization_instructions'):
                before = self.before_optimization_instructions
                after = self.after_optimization_instructions
                reduction = ((before - after) / before * 100) if before > 0 else 0
                lines.append(f"Total instructions: {before} → {after}")
                lines.append(f"Reduction: {reduction:.0f}%")

            lines.append("=" * 60)

        return "\n".join(lines)

    def _read_source(self) -> str:
        """Read source file"""
        try:
            with open(self.args.input, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            raise CompilerError(f"File not found: {self.args.input}", 1)
        except Exception as e:
            raise CompilerError(f"Cannot read {self.args.input}: {e}", 1)

    def _get_semantic_error_code(self, error: SemanticError) -> str:
        """Map semantic error to error code"""
        error_type = type(error).__name__
        mapping = {
            'UndeclaredIdentifierError': ErrorCodes.SEMANTIC_UNDECLARED,
            'DuplicateDeclarationError': ErrorCodes.SEMANTIC_DUPLICATE,
            'TypeMismatchError': ErrorCodes.SEMANTIC_TYPE_MISMATCH,
            'ArgumentCountMismatchError': ErrorCodes.SEMANTIC_WRONG_ARG_COUNT,
            'InvalidReturnTypeError': ErrorCodes.SEMANTIC_INVALID_RETURN,
            'InvalidConditionTypeError': ErrorCodes.SEMANTIC_INVALID_CONDITION,
            'InvalidAssignmentTargetError': ErrorCodes.SEMANTIC_INVALID_ASSIGNMENT,
            'UseBeforeDeclarationError': ErrorCodes.SEMANTIC_UNINITIALIZED,
        }
        return mapping.get(error_type, 'E399')

    def _get_error_context(self, error: SemanticError) -> str:
        """Получает контекст для ошибки"""
        error_type = type(error).__name__

        if hasattr(error, 'context') and error.context:
            return error.context

        if error_type == 'TypeMismatchError':
            return "while checking types in expression"
        elif error_type == 'UndeclaredIdentifierError':
            return "in current scope"
        elif error_type == 'InvalidConditionTypeError':
            return "condition must be a boolean expression"

        return ""

    def _get_error_suggestion(self, error: SemanticError) -> str:
        """Формирует подсказку для исправления ошибки"""
        error_type = type(error).__name__

        if hasattr(error, 'suggestion') and error.suggestion:
            return error.suggestion

        if error_type == 'TypeMismatchError':
            expected = getattr(error, 'expected', '')
            found = getattr(error, 'found', '')
            if expected == 'int' and found == 'float':
                return "Use explicit cast: (int) expression"
            elif expected == 'bool':
                return "Use comparison operators (==, !=, <, >, etc.)"
            else:
                return f"Convert '{found}' to '{expected}' before assignment"

        elif error_type == 'UndeclaredIdentifierError':
            return "Declare the variable before using it, or check for typos"

        elif error_type == 'InvalidConditionTypeError':
            return "Use a boolean expression: if (x != 0) or if (flag == true)"

        elif error_type == 'ArgumentCountMismatchError':
            expected = getattr(error, 'expected', '?')
            found = getattr(error, 'found', '?')
            return f"Function expects {expected} argument(s), but {found} were provided"

        elif error_type == 'DuplicateDeclarationError':
            return "Use a different name or remove the duplicate declaration"

        return ""


def create_argument_parser() -> argparse.ArgumentParser:
    """Create the argument parser for mycc"""

    parser = argparse.ArgumentParser(
        description=f'MiniCompiler {__version__} - A mini compiler for a C-like language',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,
        epilog="""
Examples:
  # Full compilation
  mycc program.src -o program

  # Generate assembly only
  mycc -S program.src -o program.asm

  # Compile to object file
  mycc -c program.src -o program.o

  # Preprocess (lexer output)
  mycc -E program.src

  # Show AST in JSON format
  mycc --ast --ast-format=json program.src

  # Generate IR with optimizations
  mycc --ir --optimize program.src

  # Verbose output
  mycc -v program.src -o program

  # Enable all warnings
  mycc -Wall program.src -o program

  # Treat warnings as errors
  mycc -Wall -Werror program.src -o program

  # JSON error output for IDE integration
  mycc --format=json program.src -o program

  # Show IR statistics
  mycc --ir --stats program.src
  mycc --ir --optimize --stats program.src
        """
    )

    # Output options
    parser.add_argument('-o', '--output', help='Output file')
    parser.add_argument('-S', '--assemble-only', action='store_true',
                        help='Generate assembly only (don\'t assemble/link)')
    parser.add_argument('-c', '--compile-only', action='store_true',
                        help='Compile to object file')
    parser.add_argument('-E', '--preprocess', action='store_true',
                        help='Preprocess only (lexer output)')

    # AST/IR output
    parser.add_argument('--ast', action='store_true',
                        help='Output abstract syntax tree')
    parser.add_argument('--ir', action='store_true',
                        help='Output intermediate representation')
    parser.add_argument('--ast-format', choices=['text', 'dot', 'json'], default='text',
                        help='AST output format')
    parser.add_argument('--ir-format', choices=['text', 'dot', 'json'], default='text',
                        help='IR output format')

    # Statistics
    parser.add_argument('--stats', action='store_true',
                        help='Show IR statistics and optimization info')

    # Optimization
    parser.add_argument('--optimize', '-O', type=int, choices=[0, 1, 2, 3], const=1, nargs='?',
                        help='Optimization level (0-3)')

    # Target
    parser.add_argument('--target', default='x86_64',
                        help='Target architecture (default: x86_64)')

    # Verbosity
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Verbose output')

    # Warnings
    parser.add_argument('-Wall', action='store_true',
                        help='Enable all warnings')
    parser.add_argument('-Werror', action='store_true',
                        help='Treat warnings as errors')

    # Error format
    parser.add_argument('--format', choices=['human', 'json'], default='human',
                        help='Error output format (default: human)')
    parser.add_argument('--max-errors', type=int, default=20,
                        help='Maximum errors before aborting (default: 20)')

    # Color output
    parser.add_argument('--color', choices=['always', 'never', 'auto'], default='auto',
                        help='Colorized output (default: auto)')

    # Custom help and version
    parser.add_argument('--help', action='help', default=argparse.SUPPRESS,
                        help='Display help message')
    parser.add_argument('--version', action='store_true',
                        help='Display compiler version')

    # Positional argument for input file
    parser.add_argument('input', nargs='*', help='Source file(s)')

    return parser


def main():
    """Main entry point"""
    parser = create_argument_parser()

    # Parse arguments
    try:
        args = parser.parse_args()
    except SystemExit:
        return 1

    # Handle --version (don't require input file)
    if args.version:
        print(f"mycc {__version__}")
        print(f"MiniCompiler — A mini compiler for a C-like language")
        print(f"Built: {__build_date__}")
        print(f"Target: {__target__}")
        return 0

    # Check that input file is provided for operations that need it
    if not args.input:
        parser.print_help()
        print(f"\n{Colors.RED}Error: No input file specified{Colors.NC}", file=sys.stderr)
        return 1

    # Determine mode based on flags
    if args.preprocess:
        args.mode = 'preprocess'
    elif args.ast:
        args.mode = 'ast'
    elif args.ir:
        args.mode = 'ir'
    else:
        args.mode = 'compile'

    # For now, only support single input file
    if len(args.input) > 1:
        print(f"{Colors.YELLOW}Warning: Multiple input files not yet fully supported. Using first file.{Colors.NC}",
              file=sys.stderr)

    args.input = args.input[0]  # Take first file for now

    # Set optimization level
    if args.optimize is not None:
        args.optimize = True
    else:
        args.optimize = False

    # Run compilation pipeline
    pipeline = CompilerPipeline(args)
    exit_code = pipeline.run()

    return exit_code


if __name__ == '__main__':
    sys.exit(main())