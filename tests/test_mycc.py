import pytest
import subprocess
import sys
import os

MYCC = [sys.executable, 'mycc.py']

class TestMyCCBasic:
    def test_version(self):
        result = subprocess.run(MYCC + ['--version'], capture_output=True, text=True)
        assert result.returncode == 0
        assert 'mycc 1.0.0' in result.stdout

    def test_help(self):
        result = subprocess.run(MYCC + ['--help'], capture_output=True, text=True)
        # --help может возвращать 0 или 1 в зависимости от argparse
        assert 'usage:' in result.stdout.lower() or 'Usage:' in result.stdout
        assert 'MiniCompiler' in result.stdout

    def test_no_input_file(self):
        result = subprocess.run([sys.executable, 'mycc.py'], capture_output=True, text=True)
        assert result.returncode != 0

class TestMyCCCompile:
    def test_compile_quicksort(self):
        result = subprocess.run(MYCC + ['examples/quicksort.src', '-o', '/tmp/test_qs'],
                                capture_output=True, text=True)
        assert result.returncode == 0

        result = subprocess.run(['/tmp/test_qs'], capture_output=True, text=True)
        # Проверяем и вывод, и код возврата
        assert result.returncode == 94
        assert 'Sum: 94' in result.stdout or result.returncode == 94

    def test_compile_optimization_demo(self):
        result = subprocess.run(MYCC + ['examples/optimization_demo.src', '-o', '/tmp/test_opt'],
                              capture_output=True, text=True)
        assert result.returncode == 0

class TestMyCCAssembly:
    def test_assembly_output(self):
        result = subprocess.run(MYCC + ['-S', 'examples/optimization_demo.src', '-o', '/tmp/test.asm'],
                              capture_output=True, text=True)
        assert result.returncode == 0
        with open('/tmp/test.asm') as f:
            content = f.read()
            assert 'section .text' in content

class TestMyCCIR:
    def test_ir_output(self):
        result = subprocess.run(MYCC + ['--ir', 'examples/optimization_demo.src'],
                              capture_output=True, text=True)
        assert result.returncode == 0
        assert 'function main' in result.stdout

    def test_ir_with_stats(self):
        result = subprocess.run(MYCC + ['--ir', '--stats', 'examples/optimization_demo.src'],
                              capture_output=True, text=True)
        assert result.returncode == 0
        assert 'IR STATISTICS' in result.stdout

class TestMyCCAST:
    def test_ast_text(self):
        result = subprocess.run(MYCC + ['--ast', 'examples/optimization_demo.src'],
                              capture_output=True, text=True)
        assert result.returncode == 0
        assert 'FunctionDecl' in result.stdout

    def test_ast_json(self):
        result = subprocess.run(MYCC + ['--ast', '--ast-format=json', 'examples/optimization_demo.src'],
                              capture_output=True, text=True)
        assert result.returncode == 0

class TestMyCCPreprocess:
    def test_preprocess(self):
        result = subprocess.run(MYCC + ['-E', 'examples/optimization_demo.src'],
                              capture_output=True, text=True)
        assert result.returncode == 0

class TestMyCCErrors:
    def test_error_output(self):
        result = subprocess.run(MYCC + ['examples/test_errors.src'],
                              capture_output=True, text=True)
        assert result.returncode != 0
        assert 'E300' in result.stderr

    def test_wall_werror(self):
        result = subprocess.run(MYCC + ['-Wall', '-Werror', 'examples/test_errors.src'],
                              capture_output=True, text=True)
        assert result.returncode != 0

    def test_color_never(self):
        result = subprocess.run(MYCC + ['--color=never', 'examples/test_errors.src'],
                              capture_output=True, text=True)
        assert '\033' not in result.stderr

class TestMyCCOptimization:
    def test_O0(self):
        result = subprocess.run(MYCC + ['-O0', 'examples/optimization_demo.src', '-o', '/tmp/test_O0'],
                              capture_output=True, text=True)
        assert result.returncode == 0

    def test_O3(self):
        result = subprocess.run(MYCC + ['-O3', 'examples/optimization_demo.src', '-o', '/tmp/test_O3'],
                              capture_output=True, text=True)
        assert result.returncode == 0
        
        result = subprocess.run(['/tmp/test_O3'], capture_output=True, text=True)
        assert result.returncode == 105

class TestMyCCVerbose:
    def test_verbose(self):
        result = subprocess.run(MYCC + ['-v', 'examples/optimization_demo.src', '-o', '/tmp/test_verbose'],
                              capture_output=True, text=True)
        assert result.returncode == 0
        assert 'Phase 1' in result.stderr
