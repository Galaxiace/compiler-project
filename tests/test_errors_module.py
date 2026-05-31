import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from errors import (
    ErrorHandler, ErrorCategory, ErrorCodes, ErrorFactory,
    CompilerMessage, ErrorSeverity, Colors
)

class TestErrorHandler:
    def test_add_error(self):
        handler = ErrorHandler(max_errors=5)
        handler.add_error('E001', 'Test error', ErrorCategory.LEXICAL, line=1, column=5)
        assert handler.has_errors()
        assert handler.error_count == 1
        assert handler.warning_count == 0

    def test_add_warning(self):
        handler = ErrorHandler(warning_level="all")
        handler.add_warning('W001', 'Test warning', ErrorCategory.SEMANTIC, line=1, column=1)
        assert handler.warning_count == 1
        assert handler.error_count == 0

    def test_warning_level_none(self):
        handler = ErrorHandler(warning_level="none")
        handler.add_warning('W001', 'Test', ErrorCategory.SEMANTIC)
        assert handler.warning_count == 0

    def test_warnings_as_errors(self):
        handler = ErrorHandler(warnings_as_errors=True, warning_level="all")
        handler.add_warning('W001', 'Test', ErrorCategory.SEMANTIC)
        assert handler.error_count == 1

    def test_max_errors(self):
        handler = ErrorHandler(max_errors=2)
        handler.add_error('E001', 'Error 1', ErrorCategory.LEXICAL, line=1, column=1)
        handler.add_error('E002', 'Error 2', ErrorCategory.LEXICAL, line=2, column=1)
        assert not handler.too_many_errors()
        handler.add_error('E003', 'Error 3', ErrorCategory.LEXICAL, line=3, column=1)
        assert handler.too_many_errors()

    def test_load_source(self):
        handler = ErrorHandler()
        handler.load_source("line1\nline2\nline3")
        assert handler.get_source_line(1) == "line1"
        assert handler.get_source_line(2) == "line2"
        assert handler.get_source_line(99) == ""

    def test_print_summary(self):
        handler = ErrorHandler()
        handler.add_error('E001', 'Test', ErrorCategory.LEXICAL)
        # Не должно падать
        handler.print_summary()

class TestErrorCodes:
    def test_lexical_codes(self):
        assert ErrorCodes.LEX_INVALID_CHAR == 'E001'
        assert ErrorCodes.LEX_UNTERMINATED_STRING == 'E002'
        assert ErrorCodes.LEX_INVALID_NUMBER == 'E004'

    def test_syntax_codes(self):
        assert ErrorCodes.SYNTAX_UNEXPECTED_TOKEN == 'E100'
        assert ErrorCodes.SYNTAX_MISSING_SEMICOLON == 'E101'

    def test_semantic_codes(self):
        assert ErrorCodes.SEMANTIC_UNDECLARED == 'E300'
        assert ErrorCodes.SEMANTIC_TYPE_MISMATCH == 'E200'
        assert ErrorCodes.SEMANTIC_DUPLICATE == 'E301'

    def test_warning_codes(self):
        assert ErrorCodes.WARN_UNUSED_VARIABLE == 'W001'
        assert ErrorCodes.WARN_IMPLICIT_CAST == 'W002'

class TestCompilerMessage:
    def test_format_human(self):
        msg = CompilerMessage(
            code='E001',
            message='Test error',
            category=ErrorCategory.LEXICAL,
            severity=ErrorSeverity.ERROR,
            line=1,
            column=5,
            source_line="int x = @;",
            context="in source file",
            suggestion="Remove invalid character"
        )
        formatted = msg.format_human(color=False)
        assert 'E001' in formatted
        assert 'Test error' in formatted
        assert '1' in formatted

    def test_format_json(self):
        msg = CompilerMessage(
            code='E300',
            message='Undefined variable',
            category=ErrorCategory.SEMANTIC,
            line=5,
            column=10
        )
        formatted = msg.format_json()
        import json
        data = json.loads(formatted)
        assert data['code'] == 'E300'
        assert data['line'] == 5

class TestColors:
    def test_colors_exist(self):
        assert hasattr(Colors, 'RED')
        assert hasattr(Colors, 'GREEN')
        assert hasattr(Colors, 'NC')

    def test_disable_colors(self):
        Colors.disable()
        assert Colors.RED == ''
        assert Colors.GREEN == ''
        assert Colors.BOLD == ''

class TestErrorHandlerExtra:
    def test_multiple_errors_and_warnings(self):
        handler = ErrorHandler(warning_level="all")
        handler.add_error('E001', 'Error 1', ErrorCategory.LEXICAL, line=1, column=1)
        handler.add_error('E002', 'Error 2', ErrorCategory.SYNTAX, line=2, column=1)
        handler.add_warning('W001', 'Warning 1', ErrorCategory.SEMANTIC, line=3, column=1)
        assert handler.error_count == 2
        assert handler.warning_count == 1

    def test_source_file_name(self):
        handler = ErrorHandler(source_file="custom.src")
        handler.add_error('E001', 'Test', ErrorCategory.LEXICAL, line=1, column=1)
        assert len(handler.messages) == 1
        assert handler.messages[0].file_path == "custom.src"

    def test_error_with_context(self):
        handler = ErrorHandler()
        handler.load_source("int x = 5;\nint y = x + z;\n")
        handler.add_error('E300', 'Undefined variable', ErrorCategory.SEMANTIC, 
                         line=2, column=13, context="in function main",
                         suggestion="Did you mean 'x'?")
        assert handler.has_errors()
        msg = handler.messages[0]
        assert msg.context == "in function main"
        assert msg.suggestion == "Did you mean 'x'?"

    def test_no_warnings_by_default(self):
        handler = ErrorHandler()
        handler.add_warning('W001', 'Test', ErrorCategory.SEMANTIC)
        assert handler.warning_count == 0  # По умолчанию warnings не считаются

    def test_format_output(self):
        handler = ErrorHandler(output_format="json")
        handler.add_error('E001', 'Test', ErrorCategory.LEXICAL, line=1, column=1)
        # Не должно падать при выводе
        handler.print_summary()
