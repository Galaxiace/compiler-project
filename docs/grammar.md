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

| Приоритет   | Операторы                                               | Ассоциативность |
|-------------|---------------------------------------------------------|-----------------|
| 1 (высший)  | `()` вызов функции, `[]` индексация, `.` поле структуры | Левая           |
| 2           | `-` (унарный), `!`, `+` (унарный)                       | Правая          |
| 3           | `*`, `/`, `%`                                           | Левая           |
| 4           | `+`, `-`                                                | Левая           |
| 5           | `<`, `<=`, `>`, `>=`                                    | Левая           |
| 6           | `==`, `!=`                                              | Левая           |
| 7           | `&`                                                     | Левая           |
| 8           | `^`                                                     | Левая           |
| 9           | `                                                       | `               | Левая |
| 10          | `&&`                                                    | Левая           |
| 11          | `                                                       |                 |` | Левая |
| 12 (низший) | `=`, `+=`, `-=`, `*=`, `/=`, `%=`                       | Правая          |

## Терминальные символы

Терминальные символы соответствуют типам токенов, определенным в лексическом анализаторе:

- **Ключевые слова**: `fn`, `struct`, `extern`, `if`, `else`, `while`, `for`, `return`, `int`, `float`, `bool`, `void`, `true`, `false`
- **Операторы**: `+`, `-`, `*`, `/`, `%`, `=`, `+=`, `-=`, `*=`, `/=`, `%=`, `==`, `!=`, `<`, `>`, `<=`, `>=`, `&&`, `||`, `!`, `->`
- **Разделители**: `(`, `)`, `{`, `}`, `;`, `,`, `[`, `]`
- **Литералы**: `INT_LITERAL`, `FLOAT_LITERAL`, `STRING_LITERAL`, `BOOL_LITERAL`
- **Идентификаторы**: `IDENTIFIER`

---