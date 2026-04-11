from typing import List, Optional, Union, Any
from lexer.token import Token, TokenType
from lexer.errors import LexicalError
from .ast import *


class ParseError(Exception):
    """Класс ошибки парсера"""

    def __init__(self, message: str, token: Token):
        self.message = message
        self.token = token
        self.line = token.line
        self.column = token.column
        super().__init__(f"[{token.line}:{token.column}] {message}")


class Parser:
    """
    Рекурсивный парсер для языка MiniCompiler.
    Реализует LL(1) грамматику с одним токеном предпросмотра.
    """

    def __init__(self, tokens: List[Token]):
        """
        Инициализация парсера списком токенов.

        Args:
            tokens: Список токенов от лексера
        """
        self.tokens = tokens
        self.current = 0
        self.errors: List[ParseError] = []

    def parse(self) -> ProgramNode:
        """
        Главный метод парсинга. Строит AST для всей программы.

        Returns:
            ProgramNode - корневой узел AST
        """
        try:
            program = self.parse_program()
            # Проверяем, что дошли до конца файла
            if not self.is_at_end():
                token = self.peek()
                if token.type != TokenType.END_OF_FILE:
                    self.error(f"Неожиданный токен после конца программы: {token.type}", token)
            return program
        except ParseError as e:
            self.errors.append(e)
            # Возвращаем пустую программу в случае ошибки
            return ProgramNode([], 1, 1)

    # ============= Вспомогательные методы =============

    def is_at_end(self) -> bool:
        """Проверяет, достигнут ли конец токенов"""
        return self.current >= len(self.tokens) or self.peek().type == TokenType.END_OF_FILE

    def peek(self) -> Token:
        """Возвращает текущий токен без продвижения"""
        if self.current < len(self.tokens):
            return self.tokens[self.current]
        # Если вышли за границы, возвращаем EOF токен
        return Token(TokenType.END_OF_FILE, "", 0, 0)

    def previous(self) -> Token:
        """Возвращает предыдущий токен"""
        return self.tokens[self.current - 1]

    def advance(self) -> Token:
        """Продвигается к следующему токену и возвращает его"""
        if not self.is_at_end():
            self.current += 1
        return self.previous()

    def check(self, token_type: TokenType) -> bool:
        """Проверяет, является ли текущий токен заданного типа"""
        if self.is_at_end():
            return False
        return self.peek().type == token_type

    def match(self, *token_types: TokenType) -> bool:
        """
        Проверяет, является ли текущий токен одним из заданных типов.
        Если да, продвигается к следующему токену.

        Returns:
            True если совпадение найдено, иначе False
        """
        for token_type in token_types:
            if self.check(token_type):
                self.advance()
                return True
        return False

    def consume(self, token_type: TokenType, message: str) -> Token:
        """
        Ожидает токен заданного типа. Если токен не совпадает, генерирует ошибку.

        Args:
            token_type: Ожидаемый тип токена
            message: Сообщение об ошибке

        Returns:
            Token - считанный токен
        """
        if self.check(token_type):
            return self.advance()

        # Ошибка - ожидаемый токен не найден
        token = self.peek()
        error = ParseError(f"{message}. Ожидался {token_type.name}, получен {token.type.name}", token)
        self.errors.append(error)

        # Пытаемся восстановиться после ошибки
        self.synchronize()
        raise error

    def error(self, message: str, token: Token) -> ParseError:
        """
        Создает и регистрирует ошибку парсинга.

        Args:
            message: Сообщение об ошибке
            token: Токен, на котором произошла ошибка
        """
        error = ParseError(message, token)
        self.errors.append(error)
        return error

    def synchronize(self):
        """
        Синхронизация после ошибки (panic mode recovery).
        Пропускает токены до следующей точки синхронизации.
        """
        self.advance()

        while not self.is_at_end():
            if self.previous().type == TokenType.SEMICOLON:
                return

            # Проверяем начало нового оператора или объявления
            token = self.peek()
            if token.type in [
                TokenType.FN, TokenType.STRUCT, TokenType.INT, TokenType.FLOAT,
                TokenType.BOOL, TokenType.VOID, TokenType.IF, TokenType.WHILE,
                TokenType.FOR, TokenType.RETURN, TokenType.LBRACE
            ]:
                return

            self.advance()

    # ============= Методы парсинга =============

    def parse_program(self) -> ProgramNode:
        """
        Program ::= { Declaration }
        """
        declarations = []
        line = 1
        column = 1

        # Парсим объявления, пока не дойдем до конца файла
        while not self.is_at_end():
            try:
                # Пропускаем возможные лишние точки с запятой между объявлениями
                while self.match(TokenType.SEMICOLON):
                    pass

                if self.is_at_end():
                    break

                # Сохраняем текущую позицию для отладки
                current_pos = self.current
                current_token = self.peek()

                decl = self.parse_declaration()
                if decl:
                    declarations.append(decl)
                    # Запоминаем позицию первого объявления
                    if len(declarations) == 1:
                        line = decl.line
                        column = decl.column

                # Проверяем, продвинулись ли мы
                if self.current == current_pos:
                    # Зациклились - принудительно продвигаемся
                    self.advance()

            except ParseError:
                # При ошибке пытаемся синхронизироваться и продолжить
                self.synchronize()

        return ProgramNode(declarations, line, column)

    def parse_declaration(self) -> Optional[DeclarationNode]:
        """
        Declaration ::= FunctionDecl | StructDecl | VarDecl
        """
        token = self.peek()

        try:
            if self.match(TokenType.FN):
                return self.parse_function_decl()
            elif self.match(TokenType.STRUCT):
                return self.parse_struct_decl()
            elif self.match(TokenType.INT, TokenType.FLOAT, TokenType.BOOL, TokenType.VOID):
                # Это точно объявление переменной (ключевое слово типа)
                self.current -= 1  # возвращаемся назад, чтобы parse_var_decl считала тип
                return self.parse_var_decl()
            elif self.match(TokenType.IDENTIFIER):
                # Может быть объявление переменной с пользовательским типом или выражение
                # Смотрим следующий токен
                if self.check(TokenType.IDENTIFIER):
                    # Два идентификатора подряд - это "тип имя" (объявление переменной)
                    self.current -= 1  # возвращаемся назад
                    return self.parse_var_decl()
                elif self.check(TokenType.LPAREN):
                    # Идентификатор с последующей '(' - это вызов функции на верхнем уровне? (не должно быть)
                    # Возвращаемся назад и обрабатываем как оператор
                    self.current -= 1
                    return self.parse_statement()
                else:
                    # Это выражение (оператор)
                    self.current -= 1  # возвращаемся назад
                    return self.parse_statement()
            else:
                # Все остальное - операторы
                return self.parse_statement()
        except ParseError:
            # Пробрасываем ошибку для синхронизации
            raise

    def parse_function_decl(self) -> FunctionDeclNode:
        """
        FunctionDecl ::= "fn" Identifier "(" [ Parameters ] ")" [ "->" Type ] Block
        """
        token = self.previous()  # токен fn

        # Имя функции
        name_token = self.consume(TokenType.IDENTIFIER, "Ожидалось имя функции")
        name = name_token.lexeme

        # Открывающая скобка параметров
        self.consume(TokenType.LPAREN, "Ожидалась '(' после имени функции")

        # Парсим параметры
        parameters = []
        if not self.check(TokenType.RPAREN):
            parameters = self.parse_parameters()

        # Закрывающая скобка параметров
        self.consume(TokenType.RPAREN, "Ожидалась ')' после параметров")

        # Необязательный возвращаемый тип
        return_type = "void"  # по умолчанию
        if self.match(TokenType.ARROW):  # ->
            if self.match(TokenType.INT, TokenType.FLOAT, TokenType.BOOL, TokenType.VOID, TokenType.IDENTIFIER):
                return_type = self.previous().lexeme
            else:
                return_type = self.consume(TokenType.IDENTIFIER, "Ожидался тип после '->'").lexeme

        # Тело функции - ожидаем открывающую скобку {
        self.consume(TokenType.LBRACE, "Ожидалась '{' перед телом функции")
        body = self.parse_block()

        return FunctionDeclNode(return_type, name, parameters, body, token.line, token.column)

    def parse_parameters(self) -> List[ParamNode]:
        """
        Parameters ::= Parameter { "," Parameter }
        Parameter ::= Type Identifier
        """
        parameters = []

        # Первый параметр
        param = self.parse_parameter()
        parameters.append(param)

        # Остальные параметры через запятую
        while self.match(TokenType.COMMA):
            param = self.parse_parameter()
            parameters.append(param)

        return parameters

    def parse_parameter(self) -> ParamNode:
        """
        Parameter ::= Type Identifier
        """
        # Тип параметра - может быть ключевым словом или идентификатором
        if self.match(TokenType.INT, TokenType.FLOAT, TokenType.BOOL, TokenType.VOID, TokenType.IDENTIFIER):
            type_token = self.previous()
            type_name = type_token.lexeme
        else:
            type_token = self.consume(TokenType.IDENTIFIER, "Ожидался тип параметра")
            type_name = type_token.lexeme

        # Имя параметра
        name_token = self.consume(TokenType.IDENTIFIER, "Ожидалось имя параметра")
        name = name_token.lexeme

        return ParamNode(type_name, name, type_token.line, type_token.column)

    def parse_struct_decl(self) -> StructDeclNode:
        """
        StructDecl ::= "struct" Identifier "{" { VarDecl } "}"
        """
        token = self.previous()  # токен struct

        # Имя структуры
        name_token = self.consume(TokenType.IDENTIFIER, "Ожидалось имя структуры")
        name = name_token.lexeme

        # Открывающая фигурная скобка
        self.consume(TokenType.LBRACE, "Ожидалась '{' после имени структуры")

        # Парсим поля
        fields = []
        while not self.check(TokenType.RBRACE) and not self.is_at_end():
            try:
                field = self.parse_var_decl()
                fields.append(field)
            except ParseError:
                # При ошибке пропускаем до точки с запятой или закрывающей скобки
                self.synchronize()

        # Закрывающая фигурная скобка
        self.consume(TokenType.RBRACE, "Ожидалась '}' после полей структуры")

        return StructDeclNode(name, fields, token.line, token.column)

    def parse_var_decl(self) -> VarDeclNode:
        """
        VarDecl ::= Type Identifier [ "=" Expression ] ";"
        """
        # Тип переменной - может быть ключевым словом (int, float, bool, void) или идентификатором
        if self.match(TokenType.INT, TokenType.FLOAT, TokenType.BOOL, TokenType.VOID, TokenType.IDENTIFIER):
            type_token = self.previous()
            type_name = type_token.lexeme
        else:
            type_token = self.consume(TokenType.IDENTIFIER, "Ожидался тип переменной")
            type_name = type_token.lexeme

        # Имя переменной
        name_token = self.consume(TokenType.IDENTIFIER, "Ожидалось имя переменной")
        name = name_token.lexeme

        # Необязательная инициализация
        initializer = None
        if self.match(TokenType.ASSIGN):
            initializer = self.parse_expression()

        # Точка с запятой
        self.consume(TokenType.SEMICOLON, "Ожидалась ';' после объявления переменной")

        return VarDeclNode(type_name, name, type_token.line, type_token.column, initializer)

    def parse_statement(self) -> StatementNode:
        """
        Statement ::= Block | IfStmt | WhileStmt | ForStmt | ReturnStmt
                    | ExprStmt | VarDecl | EmptyStmt
        """
        token = self.peek()

        try:
            if self.check(TokenType.LBRACE):
                # Потребляем LBRACE и парсим блок
                self.advance()
                return self.parse_block()
            elif self.match(TokenType.IF):
                return self.parse_if_stmt()
            elif self.match(TokenType.WHILE):
                return self.parse_while_stmt()
            elif self.match(TokenType.FOR):
                return self.parse_for_stmt()
            elif self.match(TokenType.RETURN):
                return self.parse_return_stmt()
            elif self.match(TokenType.SEMICOLON):
                # Пустой оператор
                return EmptyStmtNode(token.line, token.column)
            elif self.match(TokenType.INT, TokenType.FLOAT, TokenType.BOOL, TokenType.VOID):
                # После типа должен быть идентификатор для объявления переменной
                if self.check(TokenType.IDENTIFIER):
                    # Это объявление переменной
                    self.current -= 1  # возвращаемся назад
                    return self.parse_var_decl()
                else:
                    # Странная ситуация - тип без имени переменной
                    self.error("Ожидалось имя переменной после типа", self.peek())
                    # Пытаемся восстановиться
                    return self.parse_expr_stmt()
            elif self.match(TokenType.IDENTIFIER):
                # Проверяем, является ли следующий токен идентификатором
                # Если да, то это "тип имя" (объявление переменной с пользовательским типом)
                if self.check(TokenType.IDENTIFIER):
                    # Это объявление переменной с пользовательским типом
                    self.current -= 1  # возвращаемся назад
                    return self.parse_var_decl()
                else:
                    # Это выражение
                    self.current -= 1  # возвращаемся назад
                    return self.parse_expr_stmt()
            else:
                # Все остальное - выражения
                return self.parse_expr_stmt()
        except ParseError:
            # Пробрасываем ошибку для синхронизации
            raise

    def parse_block(self) -> BlockStmtNode:
        """
        Block ::= "{" { Statement } "}"
        Предполагается, что открывающая скобка { уже потреблена
        """
        token = self.previous()  # токен { (уже потреблен)

        statements = []

        # Парсим операторы до закрывающей скобки
        while not self.check(TokenType.RBRACE) and not self.is_at_end():
            try:
                stmt = self.parse_statement()
                statements.append(stmt)
            except ParseError:
                # При ошибке синхронизируемся
                self.synchronize()

        # Проверяем наличие закрывающей скобки
        if self.check(TokenType.RBRACE):
            self.advance()  # потребляем RBRACE
        else:
            # Достигнут конец файла без закрывающей скобки
            self.error("Ожидалась '}' после блока", self.previous())

        return BlockStmtNode(statements, token.line, token.column)

    def parse_if_stmt(self) -> IfStmtNode:
        """
        IfStmt ::= "if" "(" Expression ")" Statement [ "else" Statement ]
        """
        token = self.previous()  # токен if

        # Условие в скобках
        self.consume(TokenType.LPAREN, "Ожидалась '(' после 'if'")
        condition = self.parse_expression()
        self.consume(TokenType.RPAREN, "Ожидалась ')' после условия")

        # Ветка then
        then_branch = self.parse_statement()

        # Необязательная ветка else
        else_branch = None
        if self.match(TokenType.ELSE):
            else_branch = self.parse_statement()

        return IfStmtNode(condition, then_branch, token.line, token.column, else_branch)

    def parse_while_stmt(self) -> WhileStmtNode:
        """
        WhileStmt ::= "while" "(" Expression ")" Statement
        """
        token = self.previous()  # токен while

        # Условие в скобках
        self.consume(TokenType.LPAREN, "Ожидалась '(' после 'while'")
        condition = self.parse_expression()
        self.consume(TokenType.RPAREN, "Ожидалась ')' после условия")

        # Тело цикла
        body = self.parse_statement()

        return WhileStmtNode(condition, body, token.line, token.column)

    def parse_for_stmt(self) -> ForStmtNode:
        """
        ForStmt ::= "for" "(" [ ExprStmt ] ";" [ Expression ] ";" [ Expression ] ")" Statement
        """
        token = self.previous()  # токен for

        self.consume(TokenType.LPAREN, "Ожидалась '(' после 'for'")

        # Инициализация (может быть пустой)
        init = None
        if not self.check(TokenType.SEMICOLON):
            if self.match(TokenType.INT, TokenType.FLOAT, TokenType.BOOL):
                # Объявление переменной в init
                self.current -= 1
                init = self.parse_var_decl()
            else:
                init = self.parse_expr_stmt()
        else:
            # Пустая инициализация - пропускаем
            self.consume(TokenType.SEMICOLON, "Ожидалась ';'")

        # Условие (может быть пустым)
        condition = None
        if not self.check(TokenType.SEMICOLON):
            condition = self.parse_expression()
        self.consume(TokenType.SEMICOLON, "Ожидалась ';' после условия цикла")

        # Обновление (может быть пустым)
        update = None
        if not self.check(TokenType.RPAREN):
            update = self.parse_expression()
        self.consume(TokenType.RPAREN, "Ожидалась ')' после заголовка цикла")

        # Тело цикла
        body = self.parse_statement()

        return ForStmtNode(init, condition, update, body, token.line, token.column)

    def parse_return_stmt(self) -> ReturnStmtNode:
        """
        ReturnStmt ::= "return" [ Expression ] ";"
        """
        token = self.previous()  # токен return

        # Может быть возвращаемое значение или просто return;
        value = None
        if not self.check(TokenType.SEMICOLON):
            value = self.parse_expression()

        self.consume(TokenType.SEMICOLON, "Ожидалась ';' после return")

        return ReturnStmtNode(token.line, token.column, value)

    def parse_expr_stmt(self) -> ExprStmtNode:
        """
        ExprStmt ::= Expression ";"
        """
        expr = self.parse_expression()
        self.consume(TokenType.SEMICOLON, "Ожидалась ';' после выражения")
        return ExprStmtNode(expr, expr.line, expr.column)

    # ============= Методы парсинга выражений =============

    def parse_expression(self) -> ExpressionNode:
        """
        Expression ::= Assignment
        """
        return self.parse_assignment()

    def parse_assignment(self) -> ExpressionNode:
        """
        Assignment ::= LogicalOr [ ("=" | "+=" | "-=" | "*=" | "/=" | "%=") Assignment ]
        """
        expr = self.parse_logical_or()

        # Проверяем операторы присваивания
        if self.match(TokenType.ASSIGN, TokenType.PLUS_ASSIGN, TokenType.MINUS_ASSIGN,
                      TokenType.STAR_ASSIGN, TokenType.SLASH_ASSIGN, TokenType.PERCENT_ASSIGN):
            operator_token = self.previous()
            operator = operator_token.lexeme
            value = self.parse_assignment()  # правоассоциативное

            # Цель присваивания должна быть идентификатором
            if not isinstance(expr, IdentifierExprNode):
                # Если это не идентификатор, возможно это элемент массива или поле структуры
                # Пока просто возвращаем как есть
                pass

            return AssignmentExprNode(expr, operator, value, expr.line, expr.column)

        return expr

    def parse_logical_or(self) -> ExpressionNode:
        """
        LogicalOr ::= LogicalAnd { "||" LogicalAnd }
        """
        expr = self.parse_logical_and()

        while self.match(TokenType.OR_OR):
            operator = self.previous().lexeme
            right = self.parse_logical_and()
            expr = BinaryExprNode(expr, operator, right, expr.line, expr.column)

        return expr

    def parse_logical_and(self) -> ExpressionNode:
        """
        LogicalAnd ::= Equality { "&&" Equality }
        """
        expr = self.parse_equality()

        while self.match(TokenType.AND_AND):
            operator = self.previous().lexeme
            right = self.parse_equality()
            expr = BinaryExprNode(expr, operator, right, expr.line, expr.column)

        return expr

    def parse_equality(self) -> ExpressionNode:
        """
        Equality ::= Relational { ("==" | "!=") Relational }
        """
        expr = self.parse_relational()

        while self.match(TokenType.EQ_EQ, TokenType.NOT_EQ):
            operator = self.previous().lexeme
            right = self.parse_relational()
            expr = BinaryExprNode(expr, operator, right, expr.line, expr.column)

        return expr

    def parse_relational(self) -> ExpressionNode:
        """
        Relational ::= Additive { ("<" | ">" | "<=" | ">=") Additive }
        """
        expr = self.parse_additive()

        while self.match(TokenType.LESS, TokenType.GREATER, TokenType.LESS_EQ, TokenType.GREATER_EQ):
            operator = self.previous().lexeme
            right = self.parse_additive()
            expr = BinaryExprNode(expr, operator, right, expr.line, expr.column)

        return expr

    def parse_additive(self) -> ExpressionNode:
        """
        Additive ::= Multiplicative { ("+" | "-") Multiplicative }
        """
        expr = self.parse_multiplicative()

        while self.match(TokenType.PLUS, TokenType.MINUS):
            operator = self.previous().lexeme
            right = self.parse_multiplicative()
            expr = BinaryExprNode(expr, operator, right, expr.line, expr.column)

        return expr

    def parse_multiplicative(self) -> ExpressionNode:
        """
        Multiplicative ::= Unary { ("*" | "/" | "%") Unary }
        """
        expr = self.parse_unary()

        while self.match(TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            operator = self.previous().lexeme
            right = self.parse_unary()
            expr = BinaryExprNode(expr, operator, right, expr.line, expr.column)

        return expr

    def parse_unary(self) -> ExpressionNode:
        """
        Unary ::= ("-" | "!" | "+") Unary | Primary
        """
        if self.match(TokenType.MINUS, TokenType.NOT, TokenType.PLUS):
            token = self.previous()  # Получаем токен, а не строку
            operator = token.lexeme
            operand = self.parse_unary()
            return UnaryExprNode(operator, operand, token.line, token.column)

        return self.parse_primary()

    def parse_primary(self) -> ExpressionNode:
        """
        Primary ::= Literal | Identifier | "(" Expression ")" | Call | "(" Type ")" Expression
        """
        token = self.peek()

        if self.match(TokenType.INT_LITERAL):
            return LiteralExprNode(token.literal, token.line, token.column)

        if self.match(TokenType.FLOAT_LITERAL):
            return LiteralExprNode(token.literal, token.line, token.column)

        if self.match(TokenType.STRING_LITERAL):
            return LiteralExprNode(token.literal, token.line, token.column)

        if self.match(TokenType.TRUE):
            return LiteralExprNode(True, token.line, token.column)

        if self.match(TokenType.FALSE):
            return LiteralExprNode(False, token.line, token.column)

        if self.match(TokenType.IDENTIFIER):
            name = token.lexeme

            # Проверяем, не является ли идентификатор вызовом функции
            if self.check(TokenType.LPAREN):
                self.advance()  # потребляем LPAREN
                return self.parse_call(name, token.line, token.column)

            return IdentifierExprNode(name, token.line, token.column)

        if self.match(TokenType.LPAREN):
            # Сохраняем позицию
            line, column = token.line, token.column

            # Проверяем на приведение типа (Type)
            if self.check(TokenType.IDENTIFIER) and self.check_next(TokenType.RPAREN):
                # Приведение типа: (Type) Expression
                type_token = self.advance()
                self.consume(TokenType.RPAREN, "Ожидалась ')' после типа")
                expr = self.parse_expression()
                return CastExprNode(type_token.lexeme, expr, line, column)
            else:
                # Группировка: ( Expression )
                expr = self.parse_expression()
                self.consume(TokenType.RPAREN, "Ожидалась ')' после выражения")
                return GroupingExprNode(expr, line, column)

        # Если ничего не подошло, генерируем ошибку
        raise self.error(f"Неожиданный токен в выражении: {token.type.name}", token)

    def check_next(self, token_type: TokenType) -> bool:
        """
        Проверяет следующий токен (lookahead = 2)
        """
        if self.current + 1 >= len(self.tokens):
            return False
        return self.tokens[self.current + 1].type == token_type

    def parse_call(self, name: str, line: int, column: int) -> CallExprNode:
        """
        Call ::= Identifier "(" [ Arguments ] ")"
        """
        # Создаем узел идентификатора для вызываемого выражения
        callee = IdentifierExprNode(name, line, column)

        # Парсим аргументы
        arguments = []

        if not self.check(TokenType.RPAREN):
            # Парсим первый аргумент
            arguments.append(self.parse_expression())

            # Парсим остальные аргументы через запятую
            while self.match(TokenType.COMMA):
                arguments.append(self.parse_expression())

        # Закрывающая скобка
        self.consume(TokenType.RPAREN, "Ожидалась ')' после аргументов")

        return CallExprNode(callee, arguments, line, column)