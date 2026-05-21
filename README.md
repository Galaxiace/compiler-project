# MiniCompiler — Спринт 4: Промежуточное представление


Учебный проект компилятора для упрощенного C-подобного языка. 
Реализованы лексический анализатор, рекурсивный парсер, семантический анализатор и промежуточное представление.

---

## Структура проекта

```
compiler-project/
│
│
├── lexer/                                        # Основной пакет лексера
│   ├── init.py
│   ├── cli.py                                    # Интерфейс командной строки
│   ├── errors.py                                 # Классы ошибок лексического анализа
│   ├── scanner.py                                # Основная логика сканера
│   └── token.py                                  # Определения токенов и их типов
│
│
├── parser/                                       # Парсер
│   ├── init.py
│   ├── ast.py                                    # Классы AST узлов
│   ├── parser.py                                 # Основной парсер
│   ├── visitor.py                                # Базовый Visitor
│   ├── pretty_printer.py                         # Красивый вывод AST
│   ├── dot_generator.py                          # Генерация Graphviz DOT
│   └── json_generator.py                         # JSON вывод 
│
│
├── semantic/                                     # Семантический анализатор
│   ├── init.py
│   ├── analyzer.py                               # Основной анализатор
│   ├── decorated_ast.py                          # Декорированное AST
│   ├── errors.py                                 # Семантические ошибки
│   ├── symbol_table.py                           # Таблица символов
│   ├── type_system.py                            # Система типов и совместимость
│
│
├── ir/                                           # Промежуточное представление
│   ├── __init__.py                               
│   ├── ir_instructions.py                        # IROpcode, IROperand, IRInstruction
│   ├── basic_block.py                            # BasicBlock
│   ├── control_flow.py                           # IRFunction, IRProgram
│   ├── ir_generator.py                           # IRGenerator (из AST)
│   ├── ir_writer.py                              # Текстовый вывод
│   ├── dot_generator.py                          # DOT для Graphviz
│   ├── optimizer.py
│   ├── json_generator.py                         # JSON вывод
│   └── validator.py                              # Валидатор IR
│
│
├── codegen/                                      # x86-64 Кодогенерация
│   ├── stack_frame.py                            # Управление стековым фреймом (выделение, смещения, выравнивание)   
│   └── x86_generator.py                          # Генератор NASM-кода из IR (System V AMD64 ABI)
│
│
├── runtime/                                      # Runtime библиотека
│   └── runtime.asm                               # print_int, print_string, read_int, exit, _start
│
│
├── tests/                                        # Тесты
│   ├── init.py
│   ├── test_lexer.py                             # Модульные тесты
│   ├── test_parser.py                            # Тесты парсера
│   ├── test_advanced_features.py
│   ├── test_control_flow.py
│   ├── test_file_comparison.py                   # Сравнение с эталонами
│   ├── test_ir.py                                # Тесты IR
│   ├── test_runner.py                            # Запуск тестов
│   ├── test_semantic.py                          # Тесты семантики
│   ├── test_arrays.py
│   │
│   ├── codegen/                                  # Тесты кодогенерации
│   │   ├── valid/                                # Валидные тестовые примеры
│   │   ├── invalid/                              # Невалидные тестовые примеры 
│   │   └── run_tests.sh                          # Скрипт автоматического тестирования
│   │
│   └── lexer/                                    # Тестовые файлы
│       ├── valid/                                # Валидные тестовые примеры
│       └── invalid/                              # Невалидные тестовые примеры
│
│
├── docs/                                         # Документация
│   ├── language_spec.md                          # Спецификация языка
│   └── grammar.md 
│
│
├── examples/                                     # Примеры кода
│   ├── test_complete.src
│   ├── test_full.src
│   └── test_short.src
│
│
├── build_demo.sh
├── requirements.txt                              # Зависимости проекта
├── setup.py                                      # Установочный файл
└── README.md                                     # Этот файл
```

---

## Использование

### Лексический анализ

```bash

python -m lexer.cli --input examples/test_short.src --mode lex
```

### Парсинг с указанием формата вывода

```bash

python -m lexer.cli --input examples/test_short.src --mode parse --ast-format text
```

```bash

python -m lexer.cli --input examples/test_short.src --mode parse --ast-format dot --output ast.dot
```

```bash

python -m lexer.cli --input examples/test_short.src --mode parse --ast-format json --output ast.json
```

### Опции семантического анализа

#### Подробный вывод

```bash

python -m lexer.cli --input examples/test_short.src --mode semantic --verbose
```

#### Сохранить отчет в файл

```bash

python -m lexer.cli --input examples/test_short.src --mode semantic --output report.txt
```

### Генерация промежуточного представления (IR)

#### Генерация IR в текстовом формате

```bash

python -m lexer.cli --input examples/test_short.src --mode ir
```

#### Сохранение IR в файл

```bash

python -m lexer.cli --input examples/test_short.src --mode ir --output test_short.ir
```

#### Генерация IR в формате JSON

```bash

python -m lexer.cli --input examples/test_short.src --mode ir --ir-format json
```

#### Генерация Control Flow Graph (CFG) в формате DOT

```bash

python -m lexer.cli --input examples/test_short.src --mode ir --ir-format dot --output test_short.dot
```

#### Визуализация CFG (требуется Graphviz)

```bash

# Генерация PNG из DOT файла
dot -Tpng test_short.dot > test_short_cfg.png 2>/dev/null
```

#### Генерация IR со статистикой

```bash

python -m lexer.cli --input examples/test_short.src --mode ir --stats
```

#### Валидация IR

```bash

python -m lexer.cli --input examples/test_short.src --mode ir --validate
```

#### Подробный вывод с отчетом

```bash

python -m lexer.cli --input examples/test_short.src --mode ir --verbose
```


#### Компиляция в ассемблер

```bash

# Базовая компиляция
python -m lexer.cli --input examples/test_short.src --mode compile --output test_short.asm
```

```bash

# Компиляция большого примера
python -m lexer.cli --input examples/test_complete.src --mode compile --output test_complete.asm
```

#### Проверка

```bash

# Ассемблирование
nasm -f elf64 -o test_short.o test_short.asm

# Ассемблирование runtime
nasm -f elf64 -o runtime.o runtime/runtime.asm

# Линковка
ld -o test_short runtime.o test_short.o

# Запуск
./test_short

# Проверка результата
echo $?
# Ожидаемый вывод: 52 (42 + 10)
```

#### Демо

```bash

python -m lexer.cli --input examples/demo_fibonacci.src --mode compile --output /tmp/demo.asm --optimize
nasm -f elf64 -o /tmp/demo.o /tmp/demo.asm
nasm -f elf64 -o /tmp/runtime.o runtime/runtime.asm
ld -o /tmp/demo_program /tmp/runtime.o /tmp/demo.o
/tmp/demo_program
echo "Fibonacci(10) = $?"
```

#### Проверка оптимизаций

```bash

python -m lexer.cli --input examples/demo_fibonacci.src --mode ir --optimize --stats 2>&1 | head -30
```

---

## Пример вывода AST

```
Program [line 1]:
  FunctionDecl: main -> void [line 1]:
    Parameters: []
    Body [line 1]:
      Block [line 2-5]:
        VarDecl: int x = [line 3]:
          Literal: 42 [line 3]
        Return [line 4]: void
```

---

## Тестирование 

### Запуск всех тестов
```bash

pytest tests/ -v
```

### Тестирование valid и invalid src:

```bash

python tests/test_runner.py -v
```
```bash

tests/codegen/run_tests.sh
```

### Тестирование файла со всеми токенами

```bash

python -m lexer.cli --input examples/test_full.src
```

### Тестирование файла с базовыми конструкциями
```bash

python -m lexer.cli --input tests/lexer/valid/test_basic.src
```

### Тестирование файла с операторами
```bash

python -m lexer.cli --input tests/lexer/valid/test_operators.src
```

### Тестирование файла с недопустимыми символами
```bash

python -m lexer.cli --input tests/lexer/invalid/test_invalid_char.src
```

### Тестирование файла с незакрытой строкой
```bash

python -m lexer.cli --input tests/lexer/invalid/test_unterminated_string.src
```

---

## Детальное описание компонентов

### 1. Пакет `lexer/` — ядро лексического анализатора

#### `token.py` — определение токенов
Содержит перечисление `TokenType` со всеми типами токенов и класс `Token` для хранения информации о токене.

**Ключевые типы токенов:**
- **Ключевые слова:** `IF`, `ELSE`, `WHILE`, `FOR`, `INT`, `FLOAT`, `BOOL`, `RETURN`, `TRUE`, `FALSE`, `VOID`, `STRUCT`, `FN`
- **Операторы:** `PLUS (+)`, `MINUS (-)`, `STAR (*)`, `SLASH (/)`, `PERCENT (%)`, `ASSIGN (=)`, `EQ_EQ (==)`, `NOT_EQ (!=)`, `LESS (<)`, `GREATER (>)`, `LESS_EQ (<=)`, `GREATER_EQ (>=)`, `AND (&)`, `AND_AND (&&)`, `OR (|)`, `OR_OR (||)`
- **Разделители:** `LPAREN (`, `RPAREN )`, `LBRACE {`, `RBRACE }`, `SEMICOLON ;`, `COMMA ,`
- **Литералы:** `IDENTIFIER`, `INT_LITERAL`, `FLOAT_LITERAL`, `STRING_LITERAL`, `BOOL_LITERAL`
- **Специальные:** `END_OF_FILE`, `INVALID`

#### `errors.py` — иерархия ошибок
``` python
LexicalError              # Базовый класс
├── InvalidCharacterError   # Недопустимый символ
├── UnterminatedStringError # Незакрытая строка
├── UnterminatedCommentError # Незакрытый комментарий
├── InvalidNumberError      # Неправильный формат числа
├── IdentifierTooLongError  # Идентификатор длиннее 255 символов
└── IntegerOutOfRangeError  # Число вне диапазона [-2³¹, 2³¹-1]
```

#### `scanner.py` — основной класс Scanner
Выполняет преобразование исходного кода в токены.

### **Основные методы:**

```
__init__(source) — инициализация с исходным кодом

scan_tokens() — сканирование всех токенов

next_token() — получение следующего токена

peek_token() — просмотр следующего токена без продвижения

is_at_end() — проверка достижения конца файла

get_line() / get_column() — получение текущей позиции
```

### *Внутренние методы для распознавания:*

```
_read_identifier() — чтение идентификаторов и ключевых слов

_read_number() — чтение чисел (int и float)

_read_string() — чтение строк

_read_operator() — чтение операторов

_skip_comment() — пропуск комментариев

cli.py — интерфейс командной строки
```

Обрабатывает аргументы командной строки и запускает сканер.

---

### 2. Директория tests/ — тестирование

`test_lexer.py` — модульные тесты

#### Проверяет все аспекты работы лексера:

1) Распознавание всех типов токенов

2) Обработка граничных случаев

3) Отслеживание позиции

4) Обработка ошибок

### Тестовые файлы .src

#### Хранят примеры кода для тестирования:

1) `valid/` — корректный код, который должен успешно анализироваться

2) `invalid/` — код с ошибками для проверки обработки ошибок

---

### 3. Директория docs/ — документация
`language_spec.md`
Спецификация языка в формате EBNF, описывающая:

1) Лексическую грамматику

2) Ключевые слова

3) Правила для идентификаторов

4) Типы литералов

5) Операторы и разделители

6) Обработку пробелов и комментариев

---

---

## Спринт 5: x86-64 Кодогенерация

### Архитектура

Генератор кода преобразует промежуточное представление (IR) в ассемблер NASM для x86-64 Linux,
следуя соглашениям System V AMD64 ABI.

Исходный код (.src) → Лексер → Парсер → Семантика → IR → x86-64 Ассемблер → NASM → .o → ld → программа


### System V AMD64 ABI

**Передача параметров:**
- Целочисленные/указатели: RDI, RSI, RDX, RCX, R8, R9
- Float/double: XMM0-XMM7
- Остальные аргументы: на стеке (справа-налево)
- Возврат int: RAX
- Возврат float: XMM0

**Стек-фрейм:**

```
Высокие адреса
+------------------+
| Аргументы (>6) | [rbp+32+]
+------------------+
| Return Address | [rbp+8]
+------------------+
| Saved RBP | [rbp] ← RBP
+------------------+
| Локальная 1 | [rbp-4]
+------------------+
| Локальная 2 | [rbp-8]
+------------------+
| Временная 1 | [rbp-12]
+------------------+
| ... |
+------------------+
Низкие адреса
```

### Структура тестов кодогенерации

```
tests/codegen/
├── valid/
│   ├── arithmetic_ops/       # +, -, *, /, %
│   ├── control_flow/         # if/else, while, for
│   ├── function_calls/       # вызовы функций, рекурсия
│   ├── io_operations/        # print_int, read_int
│   └── integration/          # комплексные тесты
├── invalid/
│   ├── assembly_errors/      # ошибки компиляции/ассемблирования
│   └── runtime_errors/       # ошибки времени выполнения
└── run_tests.sh              # скрипт автоматического тестирования
```
