# MiniCompiler — Спринт 3: Семантический анализ


Учебный проект компилятора для упрощенного C-подобного языка. 
Реализованы лексический анализатор, рекурсивный парсер и семантический анализатор.

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
├── tests/                                        # Тесты
│   ├── init.py
│   ├── test_lexer.py                             # Модульные тесты
│   ├── test_parser.py                            # Тесты парсера
│   ├── test_file_comparison.py                   # Сравнение с эталонами
│   ├── test_runner.py                            # Запуск тестов
│   ├── test_semantic.py                          # Тесты семантики
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
│   ├── test_full.src
│   └── test_short.src
│
│
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
