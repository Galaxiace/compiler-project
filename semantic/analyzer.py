# semantic/analyzer.py
"""
Основной семантический анализатор.
Обходит AST, выполняет проверки и строит декорированное дерево.
"""

from typing import List, Dict, Optional, Any, Union
from parser.ast import *
from parser.visitor import Visitor
from .symbol_table import SymbolTable, SymbolInfo, SymbolKind, Type, create_builtin_types
from .type_system import TypeCompatibility
from .errors import *
from .decorated_ast import *


class SemanticAnalyzer(Visitor):
    """
    Семантический анализатор.

    Выполняет:
    - Построение таблицы символов
    - Проверку типов
    - Проверку объявлений
    - Построение декорированного AST
    """

    def __init__(self):
        self.symbol_table = SymbolTable()
        self.builtin_types = create_builtin_types()
        self.errors: List[SemanticError] = []
        self.current_function: Optional[SymbolInfo] = None
        self.loop_depth = 0

        self.decorated_program = None

    def analyze(self, ast: ProgramNode) -> DecoratedProgram:
        """Запускает семантический анализ."""
        # Первый проход: регистрация всех объявлений
        self._register_declarations(ast)

        # Второй проход: анализ тел функций и выражений
        self._analyze_declarations(ast)

        # Строим декорированное AST
        decorated = self._build_decorated_ast(ast)

        return decorated

    def _register_declarations(self, ast: ProgramNode):
        """Первый проход: регистрация всех объявлений."""
        for decl in ast.declarations:
            if isinstance(decl, FunctionDeclNode):
                self._register_function(decl)
            elif isinstance(decl, StructDeclNode):
                self._register_struct(decl)
            elif isinstance(decl, VarDeclNode):
                self._register_global_variable(decl)

    def _register_function(self, node: FunctionDeclNode):
        """Регистрирует функцию в таблице символов."""
        existing = self.symbol_table.lookup(node.name)
        if existing and existing.kind == SymbolKind.FUNCTION:
            self.errors.append(DuplicateDeclarationError(
                node.name, "function", node.line, node.column, existing.line
            ))
            return

        param_types = []
        for param in node.parameters:
            param_type = self._get_type_from_name(param.type_name)
            if param_type:
                param_types.append(param_type)

        return_type = self._get_type_from_name(node.return_type)
        if not return_type:
            return_type = self.builtin_types['void']

        func_type = Type(
            name=node.name,
            return_type=return_type,
            param_types=param_types
        )

        info = SymbolInfo(
            name=node.name,
            kind=SymbolKind.FUNCTION,
            type=func_type,
            line=node.line,
            column=node.column,
            parameters=node.parameters,
            return_type_node=return_type
        )

        self.symbol_table.insert(node.name, info)

    def _register_struct(self, node: StructDeclNode):
        """Регистрирует структуру в таблице символов."""
        existing = self.symbol_table.lookup(node.name)
        if existing:
            self.errors.append(DuplicateDeclarationError(
                node.name, "struct", node.line, node.column, existing.line
            ))
            return

        field_types = {}
        field_names = set()
        for field in node.fields:
            if field.name in field_names:
                self.errors.append(DuplicateDeclarationError(
                    field.name, "field", field.line, field.column,
                    self._find_field_line(node, field.name)
                ))
            else:
                field_names.add(field.name)
                field_type = self._get_type_from_name(field.type_name)
                if field_type:
                    field_types[field.name] = field_type

        struct_type = Type(
            name=node.name,
            is_struct=True,
            fields=field_types
        )

        info = SymbolInfo(
            name=node.name,
            kind=SymbolKind.STRUCT,
            type=struct_type,
            line=node.line,
            column=node.column,
            fields=field_types
        )

        self.symbol_table.insert(node.name, info)

    def _register_global_variable(self, node: VarDeclNode):
        """Регистрирует глобальную переменную."""
        var_type = self._get_type_from_name(node.type_name)
        if not var_type:
            var_type = self._lookup_struct_type(node.type_name)

        if not var_type:
            self.errors.append(SemanticError(
                f"unknown type '{node.type_name}'", node.line, node.column
            ))
            return

        existing = self.symbol_table.lookup(node.name)
        if existing:
            self.errors.append(DuplicateDeclarationError(
                node.name, "variable", node.line, node.column, existing.line
            ))
            return

        info = SymbolInfo(
            name=node.name,
            kind=SymbolKind.VARIABLE,
            type=var_type,
            line=node.line,
            column=node.column,
            is_initialized=node.initializer is not None
        )

        self.symbol_table.insert(node.name, info)

    def _analyze_declarations(self, ast: ProgramNode):
        """Второй проход: анализ тел функций и выражений."""
        for decl in ast.declarations:
            if isinstance(decl, FunctionDeclNode):
                self._analyze_function(decl)
            elif isinstance(decl, StructDeclNode):
                pass
            elif isinstance(decl, VarDeclNode):
                if decl.initializer:
                    self._analyze_expression(decl.initializer)

    def _analyze_function(self, node: FunctionDeclNode):
        """Анализирует тело функции."""
        self.symbol_table.enter_scope(f"function:{node.name}")

        func_info = self.symbol_table.lookup(node.name)
        if not func_info:
            self.symbol_table.exit_scope()
            return

        self.current_function = func_info

        # Регистрируем параметры (всегда инициализированы)
        for param in node.parameters:
            param_type = self._get_type_from_name(param.type_name)
            if not param_type:
                param_type = self._lookup_struct_type(param.type_name)

            if param_type:
                param_info = SymbolInfo(
                    name=param.name,
                    kind=SymbolKind.PARAMETER,
                    type=param_type,
                    line=param.line,
                    column=param.column,
                    is_initialized=True
                )
                self.symbol_table.insert(param.name, param_info)

        # Анализируем тело
        self._analyze_block(node.body)

        # Проверяем, что все пути возвращают значение
        if func_info.return_type_node and func_info.return_type_node.name != 'void':
            has_return = self._check_has_return(node.body)
            if not has_return:
                self.errors.append(InvalidReturnTypeError(
                    func_info.return_type_node.name, "void", node.body.line, node.body.column
                ))

        self.symbol_table.exit_scope()
        self.current_function = None

    def _analyze_block(self, node: BlockStmtNode):
        """Анализирует блок операторов."""
        self.symbol_table.enter_scope(f"block:{node.line}")

        for stmt in node.statements:
            self._analyze_statement(stmt)

        self.symbol_table.exit_scope()

    def _analyze_statement(self, node: StatementNode):
        """Анализирует оператор."""
        if isinstance(node, VarDeclNode):
            self._analyze_var_decl(node)
        elif isinstance(node, IfStmtNode):
            self._analyze_if(node)
        elif isinstance(node, WhileStmtNode):
            self._analyze_while(node)
        elif isinstance(node, ForStmtNode):
            self._analyze_for(node)
        elif isinstance(node, ReturnStmtNode):
            self._analyze_return(node)
        elif isinstance(node, ExprStmtNode):
            self._analyze_expr_stmt(node)
        elif isinstance(node, BlockStmtNode):
            self._analyze_block(node)

    def _analyze_var_decl(self, node: VarDeclNode):
        """Анализирует объявление переменной."""
        existing = self.symbol_table.lookup_local(node.name)
        if existing:
            self.errors.append(DuplicateDeclarationError(
                node.name, "variable", node.line, node.column, existing.line
            ))
            return

        var_type = self._get_type_from_name(node.type_name)
        if not var_type:
            var_type = self._lookup_struct_type(node.type_name)

        if not var_type:
            self.errors.append(SemanticError(
                f"unknown type '{node.type_name}'", node.line, node.column
            ))
            return

        is_initialized = False
        if node.initializer:
            init_type = self._analyze_expression(node.initializer)
            is_initialized = True

            if init_type and not TypeCompatibility.is_compatible(var_type, init_type):
                self.errors.append(TypeMismatchError(
                    var_type.name, init_type.name, node.line, node.column,
                    "variable initialization"
                ))

        info = SymbolInfo(
            name=node.name,
            kind=SymbolKind.VARIABLE,
            type=var_type,
            line=node.line,
            column=node.column,
            is_initialized=is_initialized
        )

        self.symbol_table.insert(node.name, info)

    def _analyze_if(self, node: IfStmtNode):
        """Анализирует условный оператор."""
        cond_type = self._analyze_expression(node.condition)

        if cond_type and cond_type.name != 'bool':
            self.errors.append(InvalidConditionTypeError(
                cond_type.name, node.condition.line, node.condition.column
            ))

        self._analyze_statement(node.then_branch)
        if node.else_branch:
            self._analyze_statement(node.else_branch)

    def _analyze_while(self, node: WhileStmtNode):
        """Анализирует цикл while."""
        cond_type = self._analyze_expression(node.condition)

        if cond_type and cond_type.name != 'bool':
            self.errors.append(InvalidConditionTypeError(
                cond_type.name, node.condition.line, node.condition.column
            ))

        self.loop_depth += 1
        self._analyze_statement(node.body)
        self.loop_depth -= 1

    def _analyze_for(self, node: ForStmtNode):
        """Анализирует цикл for."""
        self.symbol_table.enter_scope(f"for:{node.line}")

        if node.init:
            self._analyze_statement(node.init)

        if node.condition:
            cond_type = self._analyze_expression(node.condition)
            if cond_type and cond_type.name != 'bool':
                self.errors.append(InvalidConditionTypeError(
                    cond_type.name, node.condition.line, node.condition.column
                ))

        if node.update:
            self._analyze_expression(node.update)

        self.loop_depth += 1
        self._analyze_statement(node.body)
        self.loop_depth -= 1

        self.symbol_table.exit_scope()

    def _analyze_return(self, node: ReturnStmtNode):
        """Анализирует оператор return."""
        if not self.current_function:
            self.errors.append(SemanticError(
                "return outside function", node.line, node.column
            ))
            return

        expected_type = self.current_function.return_type_node

        if node.value:
            value_type = self._analyze_expression(node.value)

            if expected_type and value_type:
                if not TypeCompatibility.is_compatible(expected_type, value_type):
                    self.errors.append(InvalidReturnTypeError(
                        expected_type.name, value_type.name, node.line, node.column
                    ))
        else:
            if expected_type and expected_type.name != 'void':
                self.errors.append(InvalidReturnTypeError(
                    expected_type.name, "void", node.line, node.column
                ))

    def _analyze_expr_stmt(self, node: ExprStmtNode):
        """Анализирует оператор-выражение."""
        self._analyze_expression(node.expression)

    def _analyze_expression(self, node: ExpressionNode) -> Optional[Type]:
        """Анализирует выражение и возвращает его тип."""
        if isinstance(node, LiteralExprNode):
            return self._analyze_literal(node)
        elif isinstance(node, IdentifierExprNode):
            return self._analyze_identifier(node)
        elif isinstance(node, BinaryExprNode):
            return self._analyze_binary(node)
        elif isinstance(node, UnaryExprNode):
            return self._analyze_unary(node)
        elif isinstance(node, AssignmentExprNode):
            return self._analyze_assignment(node)
        elif isinstance(node, CallExprNode):
            return self._analyze_call(node)
        elif isinstance(node, GroupingExprNode):
            return self._analyze_grouping(node)
        elif isinstance(node, CastExprNode):
            return self._analyze_cast(node)

        return None

    def _analyze_literal(self, node: LiteralExprNode) -> Type:
        """Определяет тип литерала."""
        # Сначала проверяем bool (самый специфичный)
        if isinstance(node.value, bool):
            return self.builtin_types['bool']
        elif isinstance(node.value, int):
            return self.builtin_types['int']
        elif isinstance(node.value, float):
            return self.builtin_types['float']
        elif isinstance(node.value, str):
            return self.builtin_types['string']
        elif node.value is None:
            return self.builtin_types['void']

        return self.builtin_types['void']

    def _analyze_identifier(self, node: IdentifierExprNode) -> Optional[Type]:
        """Анализирует идентификатор."""
        info = self.symbol_table.lookup(node.name)

        if not info:
            suggestion = self._find_similar_name(node.name)
            self.errors.append(UndeclaredIdentifierError(
                node.name, node.line, node.column, suggestion
            ))
            return None

        # ПРОВЕРКА ИНИЦИАЛИЗАЦИИ - ЭТО ОШИБКА!
        if info.kind in (SymbolKind.VARIABLE, SymbolKind.PARAMETER):
            if not info.is_initialized:
                self.errors.append(UseBeforeDeclarationError(
                    node.name, node.line, node.column
                ))

        return info.type

    def _analyze_binary(self, node: BinaryExprNode) -> Optional[Type]:
        """Анализирует бинарную операцию."""
        left_type = self._analyze_expression(node.left)
        right_type = self._analyze_expression(node.right)

        if not left_type or not right_type:
            return None

        result_type = TypeCompatibility.get_binary_result_type(
            left_type, right_type, node.operator
        )

        if not result_type:
            self.errors.append(TypeMismatchError(
                "compatible types", f"{left_type.name} {node.operator} {right_type.name}",
                node.line, node.column, "binary operation"
            ))
            return None

        return result_type

    def _analyze_unary(self, node: UnaryExprNode) -> Optional[Type]:
        """Анализирует унарную операцию."""
        operand_type = self._analyze_expression(node.operand)

        if not operand_type:
            return None

        result_type = TypeCompatibility.get_unary_result_type(operand_type, node.operator)

        if not result_type:
            self.errors.append(TypeMismatchError(
                f"type compatible with {node.operator}", operand_type.name,
                node.line, node.column, "unary operation"
            ))
            return None

        return result_type

    def _analyze_assignment(self, node: AssignmentExprNode) -> Optional[Type]:
        """Анализирует присваивание."""
        if not isinstance(node.target, IdentifierExprNode):
            self.errors.append(InvalidAssignmentTargetError(node.line, node.column))
            return None

        target_name = node.target.name

        # Сначала проверяем, существует ли переменная
        target_info = self.symbol_table.lookup(target_name)
        if not target_info:
            self.errors.append(UndeclaredIdentifierError(
                target_name, node.target.line, node.target.column
            ))
            return None

        if target_info.kind in (SymbolKind.VARIABLE, SymbolKind.PARAMETER):
            target_info.is_initialized = True

        # Анализируем значение
        value_type = self._analyze_expression(node.value)

        if not value_type:
            return None

        # Проверяем совместимость типов
        if not TypeCompatibility.is_compatible(target_info.type, value_type):
            self.errors.append(TypeMismatchError(
                target_info.type.name, value_type.name, node.line, node.column,
                "assignment"
            ))
            return None

        return target_info.type

    def _analyze_call(self, node: CallExprNode) -> Optional[Type]:
        """Анализирует вызов функции."""
        if not isinstance(node.callee, IdentifierExprNode):
            self.errors.append(SemanticError(
                "invalid function call", node.line, node.column
            ))
            return None

        func_info = self.symbol_table.lookup(node.callee.name)

        if not func_info or func_info.kind != SymbolKind.FUNCTION:
            self.errors.append(UndeclaredIdentifierError(
                node.callee.name, node.line, node.column
            ))
            return None

        expected_count = len(func_info.parameters)
        actual_count = len(node.arguments)

        if expected_count != actual_count:
            self.errors.append(ArgumentCountMismatchError(
                node.callee.name, expected_count, actual_count, node.line, node.column
            ))
            return None

        for i, (param, arg) in enumerate(zip(func_info.parameters, node.arguments)):
            param_type = self._get_type_from_name(param.type_name)
            if not param_type:
                param_type = self._lookup_struct_type(param.type_name)

            arg_type = self._analyze_expression(arg)

            if param_type and arg_type:
                if not TypeCompatibility.is_compatible(param_type, arg_type):
                    self.errors.append(TypeMismatchError(
                        param_type.name, arg_type.name, arg.line, arg.column,
                        f"argument {i + 1} of '{node.callee.name}'"
                    ))

        return func_info.return_type_node or self.builtin_types['void']

    def _analyze_grouping(self, node: GroupingExprNode) -> Optional[Type]:
        """Анализирует группировку в скобках."""
        return self._analyze_expression(node.expression)

    def _analyze_cast(self, node: CastExprNode) -> Optional[Type]:
        """Анализирует приведение типа."""
        target_type = self._get_type_from_name(node.type_name)
        if not target_type:
            target_type = self._lookup_struct_type(node.type_name)

        if not target_type:
            self.errors.append(SemanticError(
                f"unknown type '{node.type_name}'", node.line, node.column
            ))
            return None

        expr_type = self._analyze_expression(node.expression)

        return target_type

    def _get_type_from_name(self, type_name: str) -> Optional[Type]:
        """Возвращает тип по имени (только встроенные типы)."""
        return self.builtin_types.get(type_name)

    def _lookup_struct_type(self, type_name: str) -> Optional[Type]:
        """Ищет тип структуры в таблице символов."""
        info = self.symbol_table.lookup(type_name)
        if info and info.kind == SymbolKind.STRUCT:
            return info.type
        return None

    def _find_similar_name(self, name: str) -> Optional[str]:
        """Ищет похожее имя в таблице символов для подсказки."""
        all_symbols = []
        scope = self.symbol_table.current_scope
        while scope:
            all_symbols.extend(scope.symbols.keys())
            scope = scope.parent

        for sym in all_symbols:
            if self._levenshtein_distance(name, sym) <= 2:
                return f"did you mean '{sym}'?"

        return None

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Вычисляет расстояние Левенштейна между двумя строками."""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    def _check_has_return(self, node: StatementNode) -> bool:
        """Проверяет, содержит ли блок оператор return."""
        if isinstance(node, ReturnStmtNode):
            return True
        elif isinstance(node, BlockStmtNode):
            for stmt in node.statements:
                if self._check_has_return(stmt):
                    return True
        elif isinstance(node, IfStmtNode):
            if self._check_has_return(node.then_branch):
                if node.else_branch and self._check_has_return(node.else_branch):
                    return True
        return False

    def _find_field_line(self, struct_node: StructDeclNode, field_name: str) -> int:
        """Находит строку объявления поля для сообщения об ошибке."""
        for field in struct_node.fields:
            if field.name == field_name:
                return field.line
        return struct_node.line

    def _build_decorated_ast(self, ast: ProgramNode) -> DecoratedProgram:
        """Строит декорированное AST."""
        decorated = DecoratedProgram(ast, self.symbol_table)
        self.decorated_program = decorated
        return decorated

    def get_errors(self) -> List[SemanticError]:
        """Возвращает список семантических ошибок."""
        return self.errors

    def get_symbol_table(self) -> SymbolTable:
        """Возвращает таблицу символов."""
        return self.symbol_table

    def get_decorated_ast(self) -> Optional[DecoratedProgram]:
        """Возвращает декорированное AST."""
        return self.decorated_program