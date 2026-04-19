# ir/ir_generator.py
"""
Генератор IR из декорированного AST.
"""

from typing import List, Optional, Any, Dict, Tuple
from semantic.symbol_table import SymbolTable, SymbolInfo, SymbolKind, Type
from semantic.decorated_ast import (
    DecoratedProgram, DecoratedFunction, DecoratedBlock, DecoratedVar,
    DecoratedIf, DecoratedWhile, DecoratedFor, DecoratedReturn,
    DecoratedExprStmt, DecoratedExpr, DecoratedLiteralExpr,
    DecoratedIdentifierExpr, DecoratedBinaryExpr, DecoratedUnaryExpr,
    DecoratedCallExpr, DecoratedAssignmentExpr, DecoratedGroupingExpr
)

# Импорты из парсера для работы с оригинальным AST
from parser.ast import (
    ProgramNode, FunctionDeclNode, VarDeclNode, StructDeclNode,
    BlockStmtNode, IfStmtNode, WhileStmtNode, ForStmtNode,
    ReturnStmtNode, ExprStmtNode, EmptyStmtNode,
    LiteralExprNode, IdentifierExprNode, BinaryExprNode,
    UnaryExprNode, CallExprNode, AssignmentExprNode, GroupingExprNode,
    CastExprNode
)

from .control_flow import IRProgram, IRFunction
from .basic_block import BasicBlock
from .ir_instructions import (
    IRInstruction, IROpcode, IROperand, IROperandType,
    Temp, Var, Lit, Label, Mem, Global, LabelInst, PhiInst
)


class IRGenerator:
    """
    Генерирует IR из декорированного AST.
    """

    def __init__(self, symbol_table: SymbolTable):
        self.symbol_table = symbol_table
        self.analyzer = None  # Будет установлен извне
        self.program = IRProgram()
        self.current_function: Optional[IRFunction] = None
        self.current_block: Optional[BasicBlock] = None

        # Для построения CFG
        self.break_stack: List[BasicBlock] = []
        self.continue_stack: List[BasicBlock] = []

        # Контекст для выражений
        self.last_value: Optional[IROperand] = None
        self.current_node = None  # Для комментариев

        self.label_counter = 0  # Добавляем счётчик меток

    def generate(self, ast: DecoratedProgram) -> IRProgram:
        """Генерирует IR для всей программы (заглушка)."""
        return self.program

    def generate_from_ast(self, ast: ProgramNode) -> IRProgram:
        """Генерирует IR для всей программы из оригинального AST."""
        # Генерируем функции
        for decl in ast.declarations:
            if isinstance(decl, FunctionDeclNode):
                self._generate_function_from_ast(decl)
            elif isinstance(decl, VarDeclNode):
                self._generate_global_var_from_ast(decl)

        return self.program

    def _generate_global_var_from_ast(self, node: VarDeclNode):
        """Генерирует глобальную переменную из AST узла."""
        var_info = self.symbol_table.lookup(node.name)
        var_type = var_info.type if var_info else None
        var_op = Global(node.name, var_type)
        self.program.global_vars[node.name] = var_op

    def _generate_function_from_ast(self, node: FunctionDeclNode):
        """Генерирует IR для функции из AST узла."""
        self.current_node = node

        # Получаем информацию о функции из таблицы символов
        func_info = self.symbol_table.lookup(node.name)
        return_type = func_info.return_type_node if func_info else None

        func = IRFunction(node.name, return_type)

        # Параметры
        for param in node.parameters:
            param_info = self.symbol_table.lookup(param.name)
            # Получаем тип параметра из объявления
            if param.type_name == 'int':
                param_type = Type('int', size_bytes=4, alignment=4)
            elif param.type_name == 'float':
                param_type = Type('float', size_bytes=8, alignment=8)
            elif param.type_name == 'bool':
                param_type = Type('bool', size_bytes=1, alignment=1)
            else:
                param_type = param_info.type if param_info else Type('int')

            param_op = Temp(param.name, param_type)
            func.parameters.append(param_op)
            func.var_to_temp[param.name] = param_op

        self.current_function = func
        self.program.add_function(func)

        # Создаем entry блок
        entry_block = func.create_block("entry")
        func.set_entry(entry_block)
        self.current_block = entry_block

        # Генерируем тело функции
        self._generate_block_from_ast(node.body)

        # Убеждаемся, что функция завершается return
        if self.current_block and not self.current_block.is_terminated():
            if return_type and return_type.name == 'void':
                self._emit_return(None, node)
            else:
                self._emit_return(Lit(0, return_type), node)

        self.current_function = None
        self.current_block = None
        self.current_node = None

    def _generate_block_from_ast(self, node: BlockStmtNode):
        """Генерирует IR для блока операторов из AST узла."""
        for stmt in node.statements:
            self._generate_statement_from_ast(stmt)

    def _generate_statement_from_ast(self, stmt):
        """Генерирует IR для оператора из AST узла."""
        self.current_node = stmt

        if isinstance(stmt, VarDeclNode):
            self._generate_var_decl_from_ast(stmt)
        elif isinstance(stmt, IfStmtNode):
            self._generate_if_from_ast(stmt)
        elif isinstance(stmt, WhileStmtNode):
            self._generate_while_from_ast(stmt)
        elif isinstance(stmt, ForStmtNode):
            self._generate_for_from_ast(stmt)
        elif isinstance(stmt, ReturnStmtNode):
            self._generate_return_from_ast(stmt)
        elif isinstance(stmt, ExprStmtNode):
            self._generate_expr_stmt_from_ast(stmt)
        elif isinstance(stmt, BlockStmtNode):
            self._generate_block_from_ast(stmt)
        elif isinstance(stmt, EmptyStmtNode):
            pass

    def _generate_var_decl_from_ast(self, node: VarDeclNode):
        """Генерирует IR для объявления переменной из AST узла."""
        var_info = self.symbol_table.lookup(node.name)
        var_type = var_info.type if var_info else None

        # Если тип не найден, определяем по имени типа
        if not var_type:
            if node.type_name == 'int':
                var_type = Type('int', size_bytes=4, alignment=4)
            elif node.type_name == 'float':
                var_type = Type('float', size_bytes=8, alignment=8)
            elif node.type_name == 'bool':
                var_type = Type('bool', size_bytes=1, alignment=1)

        # Выделяем память на стеке
        var_addr = self.current_function.new_temp(f"{node.name}_addr", var_type)
        size = self._get_type_size(var_type)
        self._emit_alloca(var_addr, size, node)

        # Сохраняем соответствие
        self.current_function.var_to_temp[node.name] = var_addr
        self.current_function.local_vars[node.name] = var_type

        # Инициализация
        if node.initializer:
            self._generate_expression_from_ast(node.initializer)
            val = self.last_value
            self._emit_store(var_addr, val, node)

    def _new_label(self, base: str) -> str:
        """Создаёт уникальную метку."""
        self.label_counter += 1
        return f"{base}_{self.label_counter}"

    def _generate_if_from_ast(self, node: IfStmtNode):
        """Генерирует IR для if из AST узла."""
        self._generate_expression_from_ast(node.condition)
        cond_val = self.last_value

        # Уникальные метки
        then_label = self._new_label("if_then")
        else_label = self._new_label("if_else") if node.else_branch else None
        endif_label = self._new_label("if_endif")

        then_block = self.current_function.create_block(then_label)
        else_block = self.current_function.create_block(else_label) if else_label else None
        endif_block = self.current_function.create_block(endif_label)

        # Проверяем, является ли условие отрицанием
        is_negated = self._is_negated_condition(node.condition)

        if else_block:
            if is_negated:
                self._emit_jump_if_not(cond_val, else_block.label, node)
                self._emit_jump(then_block.label, node)
            else:
                self._emit_jump_if(cond_val, then_block.label, node)
                self._emit_jump(else_block.label, node)
        else:
            if is_negated:
                self._emit_jump_if_not(cond_val, endif_block.label, node)
                self._emit_jump(then_block.label, node)
            else:
                self._emit_jump_if(cond_val, then_block.label, node)
                self._emit_jump(endif_block.label, node)

        # Then блок
        self.current_block = then_block
        self._generate_statement_from_ast(node.then_branch)
        if not self.current_block.is_terminated():
            self._emit_jump(endif_block.label, node)

        # Else блок
        if else_block:
            self.current_block = else_block
            self._generate_statement_from_ast(node.else_branch)
            if not self.current_block.is_terminated():
                self._emit_jump(endif_block.label, node)

        self.current_block = endif_block

    def _is_negated_condition(self, expr) -> bool:
        """Проверяет, является ли выражение отрицанием (!expr)."""
        if isinstance(expr, UnaryExprNode):
            return expr.operator == '!'
        return False

    def _generate_while_from_ast(self, node: WhileStmtNode):
        """Генерирует IR для while из AST узла."""
        header_label = self._new_label("while_header")
        body_label = self._new_label("while_body")
        exit_label = self._new_label("while_exit")

        header_block = self.current_function.create_block(header_label)
        body_block = self.current_function.create_block(body_label)
        exit_block = self.current_function.create_block(exit_label)

        self.break_stack.append(exit_block)
        self.continue_stack.append(header_block)

        self._emit_jump(header_block.label, node)

        # Заголовок: условие
        self.current_block = header_block
        self._generate_expression_from_ast(node.condition)
        cond_val = self.last_value

        if self._is_negated_condition(node.condition):
            self._emit_jump_if_not(cond_val, exit_block.label, node)
            self._emit_jump(body_block.label, node)
        else:
            self._emit_jump_if(cond_val, body_block.label, node)
            self._emit_jump(exit_block.label, node)

        # Тело цикла
        self.current_block = body_block
        self._generate_statement_from_ast(node.body)
        if not self.current_block.is_terminated():
            self._emit_jump(header_block.label, node)

        # Выход
        self.current_block = exit_block
        self.break_stack.pop()
        self.continue_stack.pop()

    def _generate_for_from_ast(self, node: ForStmtNode):
        """Генерирует IR для for из AST узла."""
        if node.init:
            self._generate_statement_from_ast(node.init)

        # Уникальные метки
        header_label = self._new_label("for_header")
        body_label = self._new_label("for_body")
        update_label = self._new_label("for_update")
        exit_label = self._new_label("for_exit")

        header_block = self.current_function.create_block(header_label)
        body_block = self.current_function.create_block(body_label)
        update_block = self.current_function.create_block(update_label)
        exit_block = self.current_function.create_block(exit_label)

        self.break_stack.append(exit_block)
        self.continue_stack.append(update_block)

        self._emit_jump(header_block.label, node)

        # Заголовок: условие
        self.current_block = header_block
        if node.condition:
            self._generate_expression_from_ast(node.condition)
            cond_val = self.last_value
            if self._is_negated_condition(node.condition):
                self._emit_jump_if_not(cond_val, exit_block.label, node)
                self._emit_jump(body_block.label, node)
            else:
                self._emit_jump_if(cond_val, body_block.label, node)
                self._emit_jump(exit_block.label, node)
        else:
            self._emit_jump(body_block.label, node)

        # Тело цикла
        self.current_block = body_block
        self._generate_statement_from_ast(node.body)
        if not self.current_block.is_terminated():
            self._emit_jump(update_block.label, node)  # Переход к обновлению

        # Обновление
        self.current_block = update_block
        if node.update:
            self._generate_expression_from_ast(node.update)
        self._emit_jump(header_block.label, node)  # Переход к заголовку

        # Выход
        self.current_block = exit_block
        self.break_stack.pop()
        self.continue_stack.pop()

    def _generate_return_from_ast(self, node: ReturnStmtNode):
        """Генерирует IR для return из AST узла."""
        if node.value:
            self._generate_expression_from_ast(node.value)
            self._emit_return(self.last_value, node)
        else:
            self._emit_return(None, node)

    def _generate_expr_stmt_from_ast(self, node: ExprStmtNode):
        """Генерирует IR для оператора-выражения из AST узла."""
        self._generate_expression_from_ast(node.expression)

    def _generate_expression_from_ast(self, expr):
        """Генерирует IR для выражения из AST узла."""
        self.current_node = expr

        if isinstance(expr, LiteralExprNode):
            expr_type = self._get_type_from_symbol_table(expr)
            self.last_value = Lit(expr.value, expr_type)

        elif isinstance(expr, IdentifierExprNode):
            # Проверяем, является ли это параметром функции
            is_param = False
            for param in self.current_function.parameters:
                if param.value == expr.name:
                    self.last_value = param
                    is_param = True
                    break

            if not is_param:
                var_addr = self.current_function.var_to_temp.get(expr.name)
                if var_addr:
                    expr_type = self._get_type_from_symbol_table(expr)
                    result = self.current_function.new_temp("load", expr_type)
                    self._emit_load(result, var_addr, expr)
                    self.last_value = result
                else:
                    # Глобальная переменная
                    expr_type = self._get_type_from_symbol_table(expr)
                    global_var = Global(expr.name, expr_type)
                    result = self.current_function.new_temp("load", expr_type)
                    self._emit_load(result, global_var, expr)
                    self.last_value = result

        elif isinstance(expr, BinaryExprNode):
            self._generate_expression_from_ast(expr.left)
            left_val = self.last_value
            self._generate_expression_from_ast(expr.right)
            right_val = self.last_value

            expr_type = self._get_type_from_symbol_table(expr)
            result = self.current_function.new_temp("binop", expr_type)
            self._emit_binary(result, expr.operator, left_val, right_val, expr_type, expr)
            self.last_value = result

        elif isinstance(expr, UnaryExprNode):
            self._generate_expression_from_ast(expr.operand)
            op_val = self.last_value

            expr_type = self._get_type_from_symbol_table(expr)
            result = self.current_function.new_temp("unary", expr_type)
            self._emit_unary(result, expr.operator, op_val, expr)
            self.last_value = result

        elif isinstance(expr, CallExprNode):
            self._generate_call_from_ast(expr)

        elif isinstance(expr, AssignmentExprNode):
            self._generate_assignment_from_ast(expr)

        elif isinstance(expr, GroupingExprNode):
            self._generate_expression_from_ast(expr.expression)

        elif isinstance(expr, CastExprNode):
            self._generate_expression_from_ast(expr.expression)

        return self.last_value

    def _generate_call_from_ast(self, expr: CallExprNode):
        """Генерирует IR для вызова функции из AST узла."""
        args = []
        for arg in expr.arguments:
            self._generate_expression_from_ast(arg)
            args.append(self.last_value)

        for i, arg in enumerate(args):
            self._emit_param(i, arg, expr)

        expr_type = self._get_type_from_symbol_table(expr)
        result = self.current_function.new_temp("call", expr_type)

        callee_name = expr.callee.name if hasattr(expr.callee, 'name') else "unknown"
        self._emit_call(result, callee_name, len(args), expr)
        self.last_value = result

    def _generate_assignment_from_ast(self, expr: AssignmentExprNode):
        """Генерирует IR для присваивания из AST узла."""

        # Если это составное присваивание (+=, -=, *=, /=, %=)
        if expr.operator in ('+=', '-=', '*=', '/=', '%='):
            # Загружаем текущее значение переменной
            if isinstance(expr.target, IdentifierExprNode):
                var_addr = self.current_function.var_to_temp.get(expr.target.name)
                if var_addr:
                    # Загружаем старое значение
                    old_val = self.current_function.new_temp("load", self._get_type_from_symbol_table(expr.target))
                    self._emit_load(old_val, var_addr, expr)

                    # Вычисляем новое значение
                    self._generate_expression_from_ast(expr.value)
                    right_val = self.last_value

                    # Выполняем операцию
                    result = self.current_function.new_temp("binop", self._get_type_from_symbol_table(expr))
                    op = expr.operator[0]  # '+=' -> '+', '-=' -> '-', и т.д.
                    self._emit_binary(result, op, old_val, right_val, self._get_type_from_symbol_table(expr), expr)

                    # Сохраняем результат
                    self._emit_store(var_addr, result, expr)
                    self.last_value = result
                    return
        else:
            # Обычное присваивание (=)
            self._generate_expression_from_ast(expr.value)
            val = self.last_value

            if isinstance(expr.target, IdentifierExprNode):
                var_addr = self.current_function.var_to_temp.get(expr.target.name)
                if var_addr:
                    self._emit_store(var_addr, val, expr)
                else:
                    found = False
                    for param in self.current_function.parameters:
                        if param.value == expr.target.name:
                            expr_type = self._get_type_from_symbol_table(expr.target)
                            param_copy = self.current_function.new_temp(f"{expr.target.name}_copy", expr_type)
                            self._emit_store(param_copy, val, expr)
                            self.current_function.var_to_temp[expr.target.name] = param_copy
                            found = True
                            break

                    if not found:
                        expr_type = self._get_type_from_symbol_table(expr.target)
                        global_var = Global(expr.target.name, expr_type)
                        self._emit_store(global_var, val, expr)

            self.last_value = val

    def _get_type_from_symbol_table(self, expr) -> Optional[Type]:
        """Получает тип выражения из таблицы символов."""
        if isinstance(expr, IdentifierExprNode):
            info = self.symbol_table.lookup(expr.name)
            if info:
                return info.type
        elif isinstance(expr, LiteralExprNode):
            if isinstance(expr.value, bool):
                return Type('bool', size_bytes=1, alignment=1)
            elif isinstance(expr.value, int):
                return Type('int', size_bytes=4, alignment=4)
            elif isinstance(expr.value, float):
                return Type('float', size_bytes=8, alignment=8)
            elif isinstance(expr.value, str):
                return Type('string', size_bytes=8, alignment=8)
        return Type('int', size_bytes=4, alignment=4)

    # ============= Методы эмиссии инструкций =============

    def _emit(self, instr: IRInstruction, node=None):
        """Добавляет инструкцию в текущий блок."""
        if node and hasattr(node, 'line'):
            instr.comment = f"line {node.line}"
        if self.current_block:
            self.current_block.add_instruction(instr)

    def _emit_binary(self, dest: IROperand, op: str, left: IROperand, right: IROperand, ir_type=None, node=None):
        opcode_map = {
            '+': IROpcode.ADD, '-': IROpcode.SUB, '*': IROpcode.MUL,
            '/': IROpcode.DIV, '%': IROpcode.MOD,
            '&&': IROpcode.AND, '||': IROpcode.OR,
            '==': IROpcode.CMP_EQ, '!=': IROpcode.CMP_NE,
            '<': IROpcode.CMP_LT, '<=': IROpcode.CMP_LE,
            '>': IROpcode.CMP_GT, '>=': IROpcode.CMP_GE,
            '^': IROpcode.XOR
        }
        opcode = opcode_map.get(op)
        if opcode:
            instr = IRInstruction(opcode, [dest, left, right])
            if ir_type:
                dest.ir_type = ir_type
            self._emit(instr, node)

    def _emit_unary(self, dest: IROperand, op: str, operand: IROperand, node=None):
        if op == '-':
            self._emit(IRInstruction(IROpcode.NEG, [dest, operand]), node)
        elif op == '!':
            self._emit(IRInstruction(IROpcode.NOT, [dest, operand]), node)
        elif op == '+':
            self._emit(IRInstruction(IROpcode.MOVE, [dest, operand]), node)

    def _emit_load(self, dest: IROperand, addr: IROperand, node=None):
        self._emit(IRInstruction(IROpcode.LOAD, [dest, addr]), node)

    def _emit_store(self, addr: IROperand, src: IROperand, node=None):
        self._emit(IRInstruction(IROpcode.STORE, [addr, src]), node)

    def _emit_alloca(self, dest: IROperand, size: int, node=None):
        self._emit(IRInstruction(IROpcode.ALLOCA, [dest, Lit(size)]), node)

    def _emit_jump(self, label: str, node=None):
        self._emit(IRInstruction(IROpcode.JUMP, [Label(label)]), node)

    def _emit_jump_if(self, cond: IROperand, true_label: str, node=None):
        self._emit(IRInstruction(IROpcode.JUMP_IF, [cond, Label(true_label)]), node)

    def _emit_jump_if_not(self, cond: IROperand, false_label: str, node=None):
        self._emit(IRInstruction(IROpcode.JUMP_IF_NOT, [cond, Label(false_label)]), node)

    def _emit_param(self, index: int, value: IROperand, node=None):
        self._emit(IRInstruction(IROpcode.PARAM, [Lit(index), value]), node)

    def _emit_call(self, dest: Optional[IROperand], callee: str, arg_count: int, node=None):
        ops = [dest] if dest else [Temp("void")]
        ops.append(Lit(callee))
        ops.append(Lit(arg_count))
        self._emit(IRInstruction(IROpcode.CALL, ops), node)

    def _emit_return(self, value: Optional[IROperand], node=None):
        ops = [value] if value else []
        self._emit(IRInstruction(IROpcode.RETURN, ops), node)

    def _get_type_size(self, ir_type: Type) -> int:
        """Возвращает размер типа в байтах."""
        if ir_type:
            if ir_type.name == 'int':
                return 4
            elif ir_type.name == 'float':
                return 8
            elif ir_type.name == 'bool':
                return 1
            elif ir_type.name == 'void':
                return 0
        return 4