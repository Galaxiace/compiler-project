# Developer Documentation

## MiniCompiler состоит из 6 основных модулей:

```
Исходный код (.src)
↓
[LEXER] → токены
↓
[PARSER] → AST
↓
[SEMANTIC] → Decorated AST
↓
[IR] → Intermediate Representation
↓
[CODEGEN] → x86-64 Assembly (NASM)
↓
[LINKER] → Executable (ELF64)
```

### Модули

| Модуль       | Путь        | Описание                                 |
|--------------|-------------|------------------------------------------|
| **Lexer**    | `lexer/`    | Лексический анализ                       |
| **Parser**   | `parser/`   | Рекурсивный спуск, построение AST        |
| **Semantic** | `semantic/` | Проверка типов, таблица символов         |
| **IR**       | `ir/`       | Промежуточное представление, оптимизации |
| **Codegen**  | `codegen/`  | Генерация x86-64 NASM                    |
| **Runtime**  | `runtime/`  | Runtime библиотека                       |

---

## API Reference

### Lexer API

```
from lexer.scanner import Scanner
from lexer.token import Token, TokenType

scanner = Scanner(source_code)
tokens = scanner.scan_tokens()
```

### Parser API

```
from parser.parser import Parser
from parser.ast import ProgramNode

parser = Parser(tokens)
ast = parser.parse()
```

### Semantic API

```
from semantic.analyzer import SemanticAnalyzer

analyzer = SemanticAnalyzer()
decorated_ast = analyzer.analyze(ast)
errors = analyzer.get_errors()
```

### IR API

```
from ir.ir_generator import IRGenerator
from ir.optimizer import IROptimizer

generator = IRGenerator(symbol_table)
ir_program = generator.generate_from_ast(ast)

optimizer = IROptimizer(ir_program)
ir_program = optimizer.optimize()
```

### Codegen API

```
from codegen.x86_generator import X86Generator

generator = X86Generator(ir_program)
asm_code = generator.generate()
```

---

## Добавление новых возможностей

### Новая языковая 

1. Добавить токен в lexer/token.py

2. Распознавание в lexer/scanner.py

3. AST узел в parser/ast.py

4. Правило парсинга в parser/parser.py

5. Семантическую проверку в semantic/analyzer.py

6. Генерацию IR в ir/ir_generator.py

7. Кодогенерацию в codegen/x86_generator.py

---

## Отладка

```
# Просмотр токенов
mycc -E program.src

# Просмотр AST
mycc --ast program.src

# Просмотр IR
mycc --ir program.src

# Подробная компиляция
mycc -v program.src -o program
```

---

## Тестирование

```
# Все тесты
make test-all

# Покрытие
make coverage

# Конкретный тест
pytest tests/test_lexer.py -v
```



















