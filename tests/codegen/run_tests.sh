#!/bin/bash
# run_tests.sh - Запуск всех тестов кодогенерации

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
RUNTIME="$PROJECT_DIR/runtime/runtime.asm"
PASSED=0
FAILED=0

echo "=========================================="
echo "  MiniCompiler Codegen Tests"
echo "=========================================="
echo ""

# Функция запуска valid теста (ожидает успех)
run_valid_test() {
    local src="$1"
    local expected="$2"
    local name="$(basename "$src" .src)"

    echo -n "  [VALID] $name... "

    # Компиляция
    python -m lexer.cli --input "$src" --mode compile --output /tmp/test_$$.asm 2>/dev/null
    if [ $? -ne 0 ]; then
        echo "❌ (compile error)"
        FAILED=$((FAILED + 1))
        return
    fi

    # Ассемблирование
    nasm -f elf64 -o /tmp/test_$$.o /tmp/test_$$.asm 2>/dev/null
    nasm -f elf64 -o /tmp/runtime_$$.o "$RUNTIME" 2>/dev/null

    if [ $? -ne 0 ]; then
        echo "❌ (assembly error)"
        FAILED=$((FAILED + 1))
        rm -f /tmp/test_$$.asm /tmp/test_$$.o /tmp/runtime_$$.o
        return
    fi

    # Линковка
    ld -o /tmp/test_prog_$$ /tmp/runtime_$$.o /tmp/test_$$.o 2>/dev/null
    if [ $? -ne 0 ]; then
        echo "❌ (link error)"
        FAILED=$((FAILED + 1))
        rm -f /tmp/test_$$.asm /tmp/test_$$.o /tmp/runtime_$$.o
        return
    fi

    # Выполнение
    /tmp/test_prog_$$ 2>/dev/null
    result=$?

    # Очистка
    rm -f /tmp/test_$$.asm /tmp/test_$$.o /tmp/runtime_$$.o /tmp/test_prog_$$

    if [ "$result" = "$expected" ]; then
        echo "✅ (got $result)"
        PASSED=$((PASSED + 1))
    else
        echo "❌ (expected $expected, got $result)"
        FAILED=$((FAILED + 1))
    fi
}

# Функция запуска invalid теста (ожидает ошибку компиляции/сборки/выполнения)
run_invalid_test() {
    local src="$1"
    local expect_error_type="$2"  # compile, assembly, link, runtime
    local name="$(basename "$src" .src)"

    echo -n "  [INVALID] $name... "

    # Компиляция - может завершиться с ошибкой
    python -m lexer.cli --input "$src" --mode compile --output /tmp/test_$$.asm 2>/dev/null
    compile_status=$?

    if [ "$expect_error_type" = "compile" ]; then
        if [ $compile_status -ne 0 ]; then
            echo "✅ (compile error caught)"
            PASSED=$((PASSED + 1))
            rm -f /tmp/test_$$.asm
            return
        else
            echo "❌ (expected compile error, but compiled successfully)"
            FAILED=$((FAILED + 1))
            rm -f /tmp/test_$$.asm
            return
        fi
    fi

    if [ $compile_status -ne 0 ]; then
        echo "⚠️ (unexpected compile error)"
        FAILED=$((FAILED + 1))
        rm -f /tmp/test_$$.asm
        return
    fi

    # Ассемблирование
    nasm -f elf64 -o /tmp/test_$$.o /tmp/test_$$.asm 2>/dev/null
    if [ $? -ne 0 ]; then
        if [ "$expect_error_type" = "assembly" ]; then
            echo "✅ (assembly error caught)"
            PASSED=$((PASSED + 1))
            rm -f /tmp/test_$$.asm
            return
        else
            echo "❌ (unexpected assembly error)"
            FAILED=$((FAILED + 1))
            rm -f /tmp/test_$$.asm
            return
        fi
    fi

    nasm -f elf64 -o /tmp/runtime_$$.o "$RUNTIME" 2>/dev/null

    # Линковка
    ld -o /tmp/test_prog_$$ /tmp/runtime_$$.o /tmp/test_$$.o 2>/dev/null
    if [ $? -ne 0 ]; then
        if [ "$expect_error_type" = "link" ]; then
            echo "✅ (link error caught)"
            PASSED=$((PASSED + 1))
            rm -f /tmp/test_$$.asm /tmp/test_$$.o /tmp/runtime_$$.o
            return
        else
            echo "❌ (unexpected link error)"
            FAILED=$((FAILED + 1))
            rm -f /tmp/test_$$.asm /tmp/test_$$.o /tmp/runtime_$$.o
            return
        fi
    fi

    # Выполнение
    /tmp/test_prog_$$ 2>/dev/null
    result=$?

    rm -f /tmp/test_$$.asm /tmp/test_$$.o /tmp/runtime_$$.o /tmp/test_prog_$$

    if [ "$expect_error_type" = "runtime" ]; then
        # Ожидаем либо аварийное завершение (не 0), либо специфичный код ошибки
        if [ $result -ne 0 ] || [ $result -gt 128 ]; then
            echo "✅ (runtime error caught, code=$result)"
            PASSED=$((PASSED + 1))
        else
            echo "❌ (expected runtime error, but got code $result)"
            FAILED=$((FAILED + 1))
        fi
    else
        echo "⚠️ (unexpected success)"
        FAILED=$((FAILED + 1))
    fi
}

# ============= VALID TESTS =============
echo "--- Arithmetic Operations ---"
run_valid_test "$SCRIPT_DIR/valid/arithmetic_ops/test_add.src" "8"
echo ""

echo "--- Control Flow ---"
# Тесты для if-else
run_valid_test "$SCRIPT_DIR/valid/control_flow/test_if_else.src" "1"
# Тесты для циклов
run_valid_test "$SCRIPT_DIR/valid/control_flow/test_while.src" "45"
run_valid_test "$SCRIPT_DIR/valid/control_flow/test_for.src" "45"
# Тесты для вложенных конструкций
run_valid_test "$SCRIPT_DIR/valid/control_flow/test_nested.src" "5"
# Тесты для short-circuit evaluation
run_valid_test "$SCRIPT_DIR/valid/control_flow/test_short_circuit.src" "0"
# Тесты для логических операторов
run_valid_test "$SCRIPT_DIR/valid/control_flow/test_logical_ops.src" "3"
echo ""

echo "--- Function Calls ---"
run_valid_test "$SCRIPT_DIR/valid/function_calls/test_simple_call.src" "5"
echo ""

echo "--- Complex Expressions ---"
run_valid_test "$SCRIPT_DIR/valid/complex_expressions/test_complex.src" "7"
echo ""

echo "--- Integration ---"
run_valid_test "$SCRIPT_DIR/valid/integration/test_complex.src" "120"
echo ""

# ============= INVALID TESTS =============
echo "--- Assembly Errors ---"
run_invalid_test "$SCRIPT_DIR/invalid/assembly_errors/test_undefined_function.src" "compile"
run_invalid_test "$SCRIPT_DIR/invalid/assembly_errors/test_type_mismatch.src" "compile"
run_invalid_test "$SCRIPT_DIR/invalid/assembly_errors/test_wrong_arg_count.src" "compile"
run_invalid_test "$SCRIPT_DIR/invalid/assembly_errors/test_syntax_error.src" "compile"
run_invalid_test "$SCRIPT_DIR/invalid/assembly_errors/test_duplicate_function.src" "compile"
echo ""

echo "--- Runtime Errors ---"
run_invalid_test "$SCRIPT_DIR/invalid/runtime_errors/test_division_by_zero.src" "runtime"
run_invalid_test "$SCRIPT_DIR/invalid/runtime_errors/test_stack_overflow.src" "runtime"
echo ""

echo "=========================================="
echo "  Results"
echo "=========================================="
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo ""

if [ $FAILED -gt 0 ]; then
    exit 1
fi
exit 0