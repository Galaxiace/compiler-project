# Формальная грамматика языка MiniCompiler

## Синтаксическая грамматика

### Программа

Program ::= { Declaration }


### Объявления

Declaration ::= FunctionDecl | StructDecl | VarDecl | Statement

### Функции

FunctionDecl ::= "fn" Identifier "(" [ Parameters ] ")" [ "->" Type ] Block

Parameters ::= Parameter { "," Parameter }

Parameter ::= Type Identifier


### Структуры

StructDecl ::= "struct" Identifier "{" { VarDecl } "}"

### Переменные

VarDecl ::= Type Identifier [ "=" Expression ] ";"

### Типы

Type ::= "int" | "float" | "bool" | "void" | Identifier

### Операторы

Statement ::= Block
| IfStmt
| WhileStmt
| ForStmt
| ReturnStmt
| ExprStmt
| VarDecl
| EmptyStmt

Block ::= "{" { Statement } "}"

IfStmt ::= "if" "(" Expression ")" Statement [ "else" Statement ]

WhileStmt ::= "while" "(" Expression ")" Statement

ForStmt ::= "for" "(" [ ExprStmt ] ";" [ Expression ] ";" [ Expression ] ")" Statement

ReturnStmt ::= "return" [ Expression ] ";"

ExprStmt ::= Expression ";"

EmptyStmt ::= ";"

### Выражения (с приоритетами)

Expression ::= Assignment

Assignment ::= LogicalOr { ("=" | "+=" | "-=" | "*=" | "/=" | "%=") Assignment }

LogicalOr ::= LogicalAnd { "||" LogicalAnd }

LogicalAnd ::= Equality { "&&" Equality }

Equality ::= Relational { ("==" | "!=") Relational }

Relational ::= Additive { ("<" | ">" | "<=" | ">=") Additive }

Additive ::= Multiplicative { ("+" | "-") Multiplicative }

Multiplicative ::= Unary { ("*" | "/" | "%") Unary }

Unary ::= ("-" | "!" | "+") Unary | Primary

Primary ::= Literal | Identifier | "(" Expression ")" | Call


Call ::= Identifier "(" [ Arguments ] ")"

Arguments ::= Expression { "," Expression }

Literal ::= Integer | Float | String | Boolean | "null"

## Приоритет и ассоциативность операторов

| Уровень | Операторы | Ассоциативность |
|---------|-----------|-----------------|
| 1 (наивысший) | `()` (вызов функции), `()` (группировка) | Левая |
| 2 | `-` `!` `+` (унарные) | Правая |
| 3 | `*` `/` `%` | Левая |
| 4 | `+` `-` | Левая |
| 5 | `<` `<=` `>` `>=` | Неассоциативные |
| 6 | `==` `!=` | Неассоциативные |
| 7 | `&&` | Левая |
| 8 | `\|\|` | Левая |
| 9 (низший) | `=` `+=` `-=` `*=` `/=` `%=` | Правая |

## Терминальные символы

Терминальные символы соответствуют типам токенов, определенным в лексическом анализаторе:

- **Ключевые слова**: `fn`, `struct`, `if`, `else`, `while`, `for`, `return`, `int`, `float`, `bool`, `void`, `true`, `false`
- **Операторы**: `+`, `-`, `*`, `/`, `%`, `=`, `+=`, `-=`, `*=`, `/=`, `%=`, `==`, `!=`, `<`, `>`, `<=`, `>=`, `&&`, `||`, `!`, `->`
- **Разделители**: `(`, `)`, `{`, `}`, `;`, `,`, `[`, `]`
- **Литералы**: `INT_LITERAL`, `FLOAT_LITERAL`, `STRING_LITERAL`, `BOOL_LITERAL`
- **Идентификаторы**: `IDENTIFIER`

---