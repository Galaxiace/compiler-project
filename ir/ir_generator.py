# ir/ir_generator.py
"""
Генератор IR из декорированного AST.
"""

from semantic.symbol_table import SymbolTable, SymbolInfo, SymbolKind, Type
from typing import List, Optional, Any, Dict, Tuple, Union
from semantic.decorated_ast import (
    DecoratedProgram, DecoratedFunction, DecoratedBlock, DecoratedVar,
    DecoratedIf, DecoratedWhile, DecoratedFor, DecoratedReturn,
    DecoratedExprStmt, DecoratedExpr, DecoratedLiteralExpr,
    DecoratedIdentifierExpr, DecoratedBinaryExpr, DecoratedUnaryExpr,
    DecoratedCallExpr, DecoratedAssignmentExpr, DecoratedGroupingExpr
)

from parser.ast import (
    ProgramNode, FunctionDeclNode, VarDeclNode, StructDeclNode, ArrayDeclNode,
    BlockStmtNode, IfStmtNode, WhileStmtNode, ForStmtNode,
    ReturnStmtNode, ExprStmtNode, EmptyStmtNode,
    LiteralExprNode, IdentifierExprNode, BinaryExprNode,
    UnaryExprNode, CallExprNode, AssignmentExprNode, GroupingExprNode,
    CastExprNode, ArrayAccessExprNode, StructFieldAccessExprNode,
    ExpressionNode, StatementNode, DeclarationNode
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
        self.analyzer = None
        self.program = IRProgram()
        self.current_function: Optional[IRFunction] = None
        self.current_block: Optional[BasicBlock] = None
        self.break_stack: List[BasicBlock] = []
        self.continue_stack: List[BasicBlock] = []
        self.last_value: Optional[IROperand] = None
        self.current_node = None
        self.label_counter = 0

    def generate(self, ast: DecoratedProgram) -> IRProgram:
        return self.program

    def generate_from_ast(self, ast: ProgramNode) -> IRProgram:
        for decl in ast.declarations:
            if isinstance(decl, FunctionDeclNode):
                self._generate_function_from_ast(decl)
            elif isinstance(decl, VarDeclNode):
                self._generate_global_var_from_ast(decl)
            elif isinstance(decl, ArrayDeclNode):
                self._generate_global_var_from_ast(decl)
        return self.program

    def _generate_global_var_from_ast(self, node: Union[VarDeclNode, ArrayDeclNode]):
        var_info = self.symbol_table.lookup(node.name)
        var_type = var_info.type if var_info else None
        var_op = Global(node.name, var_type)
        self.program.global_vars[node.name] = var_op

    def _generate_function_from_ast(self, node: FunctionDeclNode):
        self.current_node = node
        func_info = self.symbol_table.lookup(node.name)
        return_type = func_info.return_type_node if func_info else None

        func = IRFunction(node.name, return_type)

        entry_block = func.create_block("entry")
        func.set_entry(entry_block)
        self.current_block = entry_block

        for i, param in enumerate(node.parameters):
            param_info = self.symbol_table.lookup(param.name)

            # Проверяем, является ли параметр массивом
            if hasattr(param, 'is_array') and param.is_array:
                param_type = Type('ptr', is_array=True, size_bytes=8, alignment=8)
            elif param.type_name == 'int':
                param_type = Type('int', size_bytes=4, alignment=4)
            elif param.type_name == 'float':
                param_type = Type('float', size_bytes=4, alignment=4)
            elif param.type_name == 'bool':
                param_type = Type('bool', size_bytes=1, alignment=1)
            else:
                param_type = param_info.type if param_info else Type('int')

            param_var = Var(param.name, param_type)
            func.parameters.append(param_var)
            func.local_vars[param.name] = param_type

            param_temp = func.new_temp(f"param_{param.name}", param_type)
            func.var_to_temp[param.name] = param_temp

            self._emit(IRInstruction(IROpcode.MOVE, [param_temp, param_var]), node)

        self.current_function = func
        self.program.add_function(func)

        self._generate_block_from_ast(node.body)

        if self.current_block and not self.current_block.is_terminated():
            if return_type and return_type.name == 'void':
                self._emit_return(None, node)
            else:
                self._emit_return(Lit(0, return_type), node)

        self.current_function = None
        self.current_block = None
        self.current_node = None

    def _generate_block_from_ast(self, node: BlockStmtNode):
        for stmt in node.statements:
            self._generate_statement_from_ast(stmt)

    def _generate_statement_from_ast(self, stmt):
        self.current_node = stmt

        if isinstance(stmt, VarDeclNode):
            self._generate_var_decl_from_ast(stmt)
        elif isinstance(stmt, ArrayDeclNode):
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

    def _generate_var_decl_from_ast(self, node: Union[VarDeclNode, ArrayDeclNode]):
        """Анализирует объявление переменной или массива."""
        var_info = self.symbol_table.lookup(node.name)

        if isinstance(node, ArrayDeclNode):
            # Массив - выделяем память в куче через malloc
            element_size = 4

            if node.size and isinstance(node.size, LiteralExprNode):
                array_size = node.size.value
            else:
                array_size = 10

            element_type = Type('int', size_bytes=4, alignment=4)
            array_type = Type(
                name=f"array_{node.type_name}",
                is_array=True,
                array_size=array_size,
                element_type=element_type,
                size_bytes=array_size * element_size
            )

            self.current_function.local_vars[node.name] = array_type

            # Создаем временную для указателя на массив (ptr_type для 64-бит)
            ptr_type = Type(
                name=f"array_{node.type_name}",
                is_array=True,
                size_bytes=8
            )
            array_ptr = self.current_function.new_temp(f"array_{node.name}", ptr_type)
            self.current_function.var_to_temp[node.name] = array_ptr

            # Выделяем память через malloc
            total_size = array_size * element_size
            # PARAM 0, total_size
            self._emit_param(0, Lit(total_size, Type('int')), node)
            # CALL malloc — результат сразу в array_ptr
            self._emit_call(array_ptr, "malloc", 1, node)

            # Инициализация массива значениями
            if node.initializer and isinstance(node.initializer, list):
                for i, init_expr in enumerate(node.initializer):
                    if i < array_size:
                        self._generate_expression_from_ast(init_expr)
                        init_val = self.last_value

                        offset_temp = self.current_function.new_temp("offset", Type('int'))
                        self._emit(IRInstruction(IROpcode.MUL, [offset_temp, Lit(i), Lit(element_size)]), node)
                        addr_temp = self.current_function.new_temp("addr", Type('ptr'))
                        self._emit(IRInstruction(IROpcode.ADD, [addr_temp, array_ptr, offset_temp]), node)
                        self._emit_store(addr_temp, init_val, node)

        elif node.type_name and node.type_name not in ('int', 'float', 'bool'):
            # Проверяем, является ли тип структурой
            struct_info = self.symbol_table.lookup(node.type_name)
            if struct_info and struct_info.type and struct_info.type.is_struct:
                # Это структура - выделяем память через ALLOCA
                struct_type = struct_info.type
                total_size = struct_type.size_bytes if struct_type.size_bytes else len(struct_type.fields) * 4

                self.current_function.local_vars[node.name] = struct_type
                struct_ptr = self.current_function.new_temp(f"struct_{node.name}", struct_type)

                # Помечаем как указатель для кодогенератора (чтобы использовался qword)
                ptr_type = Type(
                    name=struct_type.name,
                    is_array=True,  # сигнал использовать qword
                    size_bytes=8
                )
                struct_ptr.ir_type = ptr_type
                self.current_function.var_to_temp[node.name] = struct_ptr

                # Выделяем память через ALLOCA
                self._emit_alloca(struct_ptr, total_size, node)

                # Обработка инициализатора для структур
                if node.initializer:
                    self._generate_expression_from_ast(node.initializer)
                    init_val = self.last_value
                    self._emit_struct_copy(struct_ptr, init_val, struct_type, node)
                return

        elif var_info and var_info.type and var_info.type.is_struct:
            # Структура через var_info (запасной вариант)
            struct_type = var_info.type
            total_size = struct_type.size_bytes if struct_type.size_bytes else len(struct_type.fields) * 4

            self.current_function.local_vars[node.name] = struct_type
            struct_ptr = self.current_function.new_temp(f"struct_{node.name}", struct_type)

            # Помечаем как указатель для кодогенератора (чтобы использовался qword)
            ptr_type = Type(
                name=struct_type.name,
                is_array=True,  # сигнал использовать qword
                size_bytes=8
            )
            struct_ptr.ir_type = ptr_type
            self.current_function.var_to_temp[node.name] = struct_ptr

            # Выделяем память через ALLOCA
            self._emit_alloca(struct_ptr, total_size, node)

            # Обработка инициализатора для структур
            if node.initializer:
                self._generate_expression_from_ast(node.initializer)
                init_val = self.last_value
                self._emit_struct_copy(struct_ptr, init_val, struct_type, node)
            return

        else:
            # Обычная переменная
            var_type = var_info.type if var_info else None

            if not var_type:
                if node.type_name == 'int':
                    var_type = Type('int', size_bytes=4, alignment=4)
                elif node.type_name == 'float':
                    var_type = Type('float', size_bytes=4, alignment=4)
                elif node.type_name == 'bool':
                    var_type = Type('bool', size_bytes=1, alignment=1)
                else:
                    var_type = Type('int', size_bytes=4, alignment=4)

            self.current_function.local_vars[node.name] = var_type

            var_temp = self.current_function.new_temp(f"var_{node.name}", var_type)
            self.current_function.var_to_temp[node.name] = var_temp

            if node.initializer:
                self._generate_expression_from_ast(node.initializer)
                init_val = self.last_value
                self._emit(IRInstruction(IROpcode.MOVE, [var_temp, init_val]), node)
            else:
                zero = Lit(0, var_type)
                self._emit(IRInstruction(IROpcode.MOVE, [var_temp, zero]), node)

    def _emit_struct_copy(self, dest_ptr: IROperand, src_ptr: IROperand, struct_type: Type, node=None):
        """Генерирует побайтовое копирование структуры из src_ptr в dest_ptr."""
        total_size = struct_type.size_bytes if struct_type.size_bytes else len(struct_type.fields) * 4

        # Копируем по 4 байта (размер int/float)
        for offset in range(0, total_size, 4):
            # Вычисляем адрес поля в источнике
            src_addr = self.current_function.new_temp(f"copy_src_{offset}", Type('ptr'))
            if offset > 0:
                self._emit(IRInstruction(IROpcode.ADD, [src_addr, src_ptr, Lit(offset)]), node)
            else:
                self._emit(IRInstruction(IROpcode.MOVE, [src_addr, src_ptr]), node)

            # Загружаем значение из источника
            temp_val = self.current_function.new_temp(f"copy_val_{offset}", Type('int'))
            self._emit_load(temp_val, src_addr, node)

            # Вычисляем адрес поля в назначении
            dst_addr = self.current_function.new_temp(f"copy_dst_{offset}", Type('ptr'))
            if offset > 0:
                self._emit(IRInstruction(IROpcode.ADD, [dst_addr, dest_ptr, Lit(offset)]), node)
            else:
                self._emit(IRInstruction(IROpcode.MOVE, [dst_addr, dest_ptr]), node)

            # Сохраняем значение в назначение
            self._emit_store(dst_addr, temp_val, node)

    def _new_label(self, base: str) -> str:
        self.label_counter += 1
        return f"{base}_{self.label_counter}"

    def _generate_if_from_ast(self, node: IfStmtNode):
        self._generate_expression_from_ast(node.condition)
        cond_val = self.last_value

        then_label = self._new_label("if_then")
        else_label = self._new_label("if_else") if node.else_branch else None
        endif_label = self._new_label("if_endif")

        then_block = self.current_function.create_block(then_label)
        else_block = self.current_function.create_block(else_label) if else_label else None
        endif_block = self.current_function.create_block(endif_label)

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

        self.current_block = then_block
        self._generate_statement_from_ast(node.then_branch)
        if not self.current_block.is_terminated():
            self._emit_jump(endif_block.label, node)

        if else_block:
            self.current_block = else_block
            self._generate_statement_from_ast(node.else_branch)
            if not self.current_block.is_terminated():
                self._emit_jump(endif_block.label, node)

        self.current_block = endif_block

    def _is_negated_condition(self, expr) -> bool:
        if isinstance(expr, UnaryExprNode):
            return expr.operator == '!'
        return False

    def _generate_while_from_ast(self, node: WhileStmtNode):
        header_label = self._new_label("while_header")
        body_label = self._new_label("while_body")
        exit_label = self._new_label("while_exit")

        header_block = self.current_function.create_block(header_label)
        body_block = self.current_function.create_block(body_label)
        exit_block = self.current_function.create_block(exit_label)

        self.break_stack.append(exit_block)
        self.continue_stack.append(header_block)

        self._emit_jump(header_block.label, node)

        self.current_block = header_block
        self._generate_expression_from_ast(node.condition)
        cond_val = self.last_value

        if self._is_negated_condition(node.condition):
            self._emit_jump_if_not(cond_val, exit_block.label, node)
            self._emit_jump(body_block.label, node)
        else:
            self._emit_jump_if(cond_val, body_block.label, node)
            self._emit_jump(exit_block.label, node)

        self.current_block = body_block
        self._generate_statement_from_ast(node.body)
        if not self.current_block.is_terminated():
            self._emit_jump(header_block.label, node)

        self.current_block = exit_block
        self.break_stack.pop()
        self.continue_stack.pop()

    def _generate_for_from_ast(self, node: ForStmtNode):
        if node.init:
            self._generate_statement_from_ast(node.init)

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

        self.current_block = body_block
        self._generate_statement_from_ast(node.body)
        if not self.current_block.is_terminated():
            self._emit_jump(update_block.label, node)

        self.current_block = update_block
        if node.update:
            self._generate_expression_from_ast(node.update)
        self._emit_jump(header_block.label, node)

        self.current_block = exit_block
        self.break_stack.pop()
        self.continue_stack.pop()

    def _generate_return_from_ast(self, node: ReturnStmtNode):
        if node.value:
            self._generate_expression_from_ast(node.value)
            ret_val = self.last_value
            self._emit_return(ret_val, node)
        else:
            self._emit_return(None, node)

    def _generate_expr_stmt_from_ast(self, node: ExprStmtNode):
        self._generate_expression_from_ast(node.expression)

    def _generate_logical_and(self, node: BinaryExprNode):
        result_type = self._get_type_from_symbol_table(node)
        result_temp = self.current_function.new_temp("land", result_type)

        eval_right_label = self._new_label("land_eval_right")
        true_label = self._new_label("land_true")
        false_label = self._new_label("land_false")
        end_label = self._new_label("land_end")

        self._generate_expression_from_ast(node.left)
        left_val = self.last_value

        self._emit(IRInstruction(IROpcode.JUMP_IF_NOT, [left_val, Label(false_label)]), node)
        self._emit_jump(eval_right_label, node)

        self.current_block = self.current_function.create_block(eval_right_label)
        self._generate_expression_from_ast(node.right)
        right_val = self.last_value

        self._emit(IRInstruction(IROpcode.JUMP_IF_NOT, [right_val, Label(false_label)]), node)
        self._emit_jump(true_label, node)

        self.current_block = self.current_function.create_block(true_label)
        self._emit(IRInstruction(IROpcode.MOVE, [result_temp, Lit(1, result_type)]), node)
        self._emit_jump(end_label, node)

        self.current_block = self.current_function.create_block(false_label)
        self._emit(IRInstruction(IROpcode.MOVE, [result_temp, Lit(0, result_type)]), node)
        self._emit_jump(end_label, node)

        self.current_block = self.current_function.create_block(end_label)
        self.last_value = result_temp

    def _generate_logical_or(self, node: BinaryExprNode):
        result_type = self._get_type_from_symbol_table(node)
        result_temp = self.current_function.new_temp("lor", result_type)

        eval_right_label = self._new_label("lor_eval_right")
        true_label = self._new_label("lor_true")
        false_label = self._new_label("lor_false")
        end_label = self._new_label("lor_end")

        self._generate_expression_from_ast(node.left)
        left_val = self.last_value

        self._emit(IRInstruction(IROpcode.JUMP_IF, [left_val, Label(true_label)]), node)
        self._emit_jump(eval_right_label, node)

        self.current_block = self.current_function.create_block(eval_right_label)
        self._generate_expression_from_ast(node.right)
        right_val = self.last_value

        self._emit(IRInstruction(IROpcode.JUMP_IF, [right_val, Label(true_label)]), node)
        self._emit_jump(false_label, node)

        self.current_block = self.current_function.create_block(true_label)
        self._emit(IRInstruction(IROpcode.MOVE, [result_temp, Lit(1, result_type)]), node)
        self._emit_jump(end_label, node)

        self.current_block = self.current_function.create_block(false_label)
        self._emit(IRInstruction(IROpcode.MOVE, [result_temp, Lit(0, result_type)]), node)
        self._emit_jump(end_label, node)

        self.current_block = self.current_function.create_block(end_label)
        self.last_value = result_temp

    def _generate_expression_from_ast(self, expr):
        self.current_node = expr

        if isinstance(expr, LiteralExprNode):
            expr_type = self._get_type_from_symbol_table(expr)
            self.last_value = Lit(expr.value, expr_type)

        elif isinstance(expr, IdentifierExprNode):
            var_temp = self.current_function.var_to_temp.get(expr.name)
            if var_temp:
                self.last_value = var_temp
            else:
                found = False
                for param in self.current_function.parameters:
                    if param.value == expr.name:
                        self.last_value = param
                        found = True
                        break

                if not found:
                    expr_type = self._get_type_from_symbol_table(expr)
                    global_var = Global(expr.name, expr_type)
                    result = self.current_function.new_temp("load_global", expr_type)
                    self._emit_load(result, global_var, expr)
                    self.last_value = result

        elif isinstance(expr, BinaryExprNode):
            if expr.operator == '&&':
                self._generate_logical_and(expr)
            elif expr.operator == '||':
                self._generate_logical_or(expr)
            else:
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

        elif isinstance(expr, ArrayAccessExprNode):
            self._generate_array_access(expr)

        elif isinstance(expr, StructFieldAccessExprNode):
            self._generate_struct_field_access(expr)

        return self.last_value

    def _generate_array_access(self, node: ArrayAccessExprNode):
        """
        Генерация доступа к элементу массива arr[index]
        """
        self._generate_expression_from_ast(node.array)
        array_ptr = self.last_value

        # Убираем лишнюю загрузку для массивов
        # array_ptr уже содержит правильный указатель из var_to_temp

        self._generate_expression_from_ast(node.index)
        index = self.last_value

        element_size = 4
        if hasattr(node, 'element_type'):
            if node.element_type and node.element_type.name == 'float':
                element_size = 4

        offset_temp = self.current_function.new_temp("offset", Type('int'))
        self._emit(IRInstruction(IROpcode.MUL, [offset_temp, index, Lit(element_size)]), node)

        addr_temp = self.current_function.new_temp("addr", Type('ptr'))
        self._emit(IRInstruction(IROpcode.ADD, [addr_temp, array_ptr, offset_temp]), node)

        elem_type = self._get_type_from_symbol_table(node)
        result = self.current_function.new_temp("array_elem", elem_type)
        self._emit_load(result, addr_temp, node)
        self.last_value = result

    def _generate_struct_field_access(self, node: StructFieldAccessExprNode):
        """
        Генерация доступа к полю структуры struct.field
        """
        self._generate_expression_from_ast(node.struct)
        struct_ptr = self.last_value

        field_offset = 0
        if isinstance(node.struct, IdentifierExprNode):
            # Получаем тип структуры из local_vars функции
            struct_type = self.current_function.local_vars.get(node.struct.name)
            if struct_type and struct_type.is_struct and hasattr(struct_type, 'fields'):
                field_names = list(struct_type.fields.keys())
                if node.field_name in field_names:
                    field_offset = field_names.index(node.field_name) * 4

        addr_temp = self.current_function.new_temp("field_addr", Type('ptr'))
        if field_offset > 0:
            self._emit(IRInstruction(IROpcode.ADD, [addr_temp, struct_ptr, Lit(field_offset)]), node)
        else:
            self._emit(IRInstruction(IROpcode.MOVE, [addr_temp, struct_ptr]), node)

        field_type = self._get_type_from_symbol_table(node)
        result = self.current_function.new_temp("field", field_type)
        self._emit_load(result, addr_temp, node)
        self.last_value = result

    def _generate_call_from_ast(self, expr: CallExprNode):
        args = []
        for arg in expr.arguments:
            self._generate_expression_from_ast(arg)
            args.append(self.last_value)

        for i, arg in enumerate(args):
            self._emit_param(i, arg, expr)

        callee_name = expr.callee.name if hasattr(expr.callee, 'name') else "unknown"

        # Определяем тип возвращаемого значения
        func_info = self.symbol_table.lookup(callee_name)
        return_type = None
        if func_info:
            return_type = func_info.return_type_node

        if return_type and return_type.is_struct:
            # Для функций, возвращающих структуру, результат - это указатель
            total_size = return_type.size_bytes if return_type.size_bytes else len(return_type.fields) * 4
            result_ptr = self.current_function.new_temp("call_struct", return_type)
            ptr_type = Type(name=return_type.name, is_array=True, size_bytes=8)
            result_ptr.ir_type = ptr_type
            self._emit_alloca(result_ptr, total_size, expr)

            # Вызываем функцию
            self._emit_call(result_ptr, callee_name, len(args), expr)
            self.last_value = result_ptr
        else:
            # Обычный вызов функции, возвращающей простой тип
            expr_type = self._get_type_from_symbol_table(expr)
            result = self.current_function.new_temp("call", expr_type)
            self._emit_call(result, callee_name, len(args), expr)
            self.last_value = result

    def _generate_assignment_from_ast(self, expr: AssignmentExprNode):
        # Присваивание в элемент массива: arr[index] = value
        if isinstance(expr.target, ArrayAccessExprNode):
            self._generate_array_assignment(expr.target, expr.value)
            return

        # Присваивание в поле структуры: struct.field = value
        elif isinstance(expr.target, StructFieldAccessExprNode):
            self._generate_struct_assignment(expr.target, expr.value)
            return

        # Составные операторы присваивания (+=, -=, etc)
        elif expr.operator in ('+=', '-=', '*=', '/=', '%='):
            if isinstance(expr.target, IdentifierExprNode):
                var_temp = self.current_function.var_to_temp.get(expr.target.name)
                if var_temp:
                    old_val = var_temp
                    self._generate_expression_from_ast(expr.value)
                    right_val = self.last_value
                    result = self.current_function.new_temp("binop", self._get_type_from_symbol_table(expr))
                    op = expr.operator[0]
                    self._emit_binary(result, op, old_val, right_val, self._get_type_from_symbol_table(expr), expr)
                    self._emit(IRInstruction(IROpcode.MOVE, [var_temp, result]), expr)
                    self.last_value = var_temp
                    return

        # Обычное присваивание переменной
        self._generate_expression_from_ast(expr.value)
        val = self.last_value

        if isinstance(expr.target, IdentifierExprNode):
            var_temp = self.current_function.var_to_temp.get(expr.target.name)
            if var_temp:
                self._emit(IRInstruction(IROpcode.MOVE, [var_temp, val]), expr)
                self.last_value = var_temp
            else:
                found = False
                for param in self.current_function.parameters:
                    if param.value == expr.target.name:
                        expr_type = self._get_type_from_symbol_table(expr.target)
                        param_temp = self.current_function.new_temp(f"param_{expr.target.name}", expr_type)
                        self._emit(IRInstruction(IROpcode.MOVE, [param_temp, val]), expr)
                        self.current_function.var_to_temp[expr.target.name] = param_temp
                        self.last_value = param_temp
                        found = True
                        break

                if not found:
                    expr_type = self._get_type_from_symbol_table(expr.target)
                    global_var = Global(expr.target.name, expr_type)
                    self._emit_store(global_var, val, expr)
                    self.last_value = val

    def _generate_array_assignment(self, target: ArrayAccessExprNode, value: ExpressionNode):
        """Генерация присваивания в элемент массива."""
        self._generate_expression_from_ast(target.array)
        array_ptr = self.last_value

        # Убираем лишнюю загрузку
        # array_ptr уже содержит правильный указатель

        self._generate_expression_from_ast(target.index)
        index = self.last_value

        element_size = 4
        offset_temp = self.current_function.new_temp("offset", Type('int'))
        self._emit(IRInstruction(IROpcode.MUL, [offset_temp, index, Lit(element_size)]), target)

        addr_temp = self.current_function.new_temp("addr", Type('ptr'))
        self._emit(IRInstruction(IROpcode.ADD, [addr_temp, array_ptr, offset_temp]), target)

        self._generate_expression_from_ast(value)
        val = self.last_value

        self._emit_store(addr_temp, val, target)
        self.last_value = val

    def _generate_struct_assignment(self, target: StructFieldAccessExprNode, value: ExpressionNode):
        """Генерация присваивания в поле структуры."""
        self._generate_expression_from_ast(target.struct)
        struct_ptr = self.last_value

        field_offset = 0
        if isinstance(target.struct, IdentifierExprNode):
            struct_type = self.current_function.local_vars.get(target.struct.name)
            if struct_type and struct_type.is_struct and hasattr(struct_type, 'fields'):
                field_names = list(struct_type.fields.keys())
                if target.field_name in field_names:
                    field_offset = field_names.index(target.field_name) * 4

        addr_temp = self.current_function.new_temp("field_addr", Type('ptr'))
        if field_offset > 0:
            self._emit(IRInstruction(IROpcode.ADD, [addr_temp, struct_ptr, Lit(field_offset)]), target)
        else:
            self._emit(IRInstruction(IROpcode.MOVE, [addr_temp, struct_ptr]), target)

        self._generate_expression_from_ast(value)
        val = self.last_value

        self._emit_store(addr_temp, val, target)
        self.last_value = val

    def _get_type_from_symbol_table(self, expr) -> Optional[Type]:
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
                return Type('float', size_bytes=4, alignment=4)
            elif isinstance(expr.value, str):
                return Type('string', size_bytes=8, alignment=8)
        elif isinstance(expr, ArrayAccessExprNode):
            # Возвращаем тип элемента массива
            if hasattr(expr, 'element_type') and expr.element_type:
                return expr.element_type
            return Type('int', size_bytes=4, alignment=4)
        return Type('int', size_bytes=4, alignment=4)

    def _op(self, operand: IROperand) -> str:
        """Форматирует операнд для вывода в IR."""
        if operand.operand_type == IROperandType.TEMPORARY:
            return f"%{operand.value}"
        elif operand.operand_type == IROperandType.VARIABLE:
            return f"@{operand.value}"
        elif operand.operand_type == IROperandType.LITERAL:
            if isinstance(operand.value, bool):
                return "true" if operand.value else "false"
            elif isinstance(operand.value, str):
                return f'"{operand.value}"'
            return str(operand.value)
        elif operand.operand_type == IROperandType.LABEL:
            return operand.value
        elif operand.operand_type == IROperandType.GLOBAL:
            return f"@{operand.value}"
        return str(operand.value)

    # ============= Методы эмиссии инструкций =============

    def _emit(self, instr: IRInstruction, node=None):
        if node and hasattr(node, 'line'):
            instr.comment = f"line {node.line}"
        if self.current_block:
            self.current_block.add_instruction(instr)

    def _emit_binary(self, dest: IROperand, op: str, left: IROperand, right: IROperand, ir_type=None, node=None):
        opcode_map = {
            '+': IROpcode.ADD, '-': IROpcode.SUB, '*': IROpcode.MUL,
            '/': IROpcode.DIV, '%': IROpcode.MOD,
            '==': IROpcode.CMP_EQ, '!=': IROpcode.CMP_NE,
            '<': IROpcode.CMP_LT, '<=': IROpcode.CMP_LE,
            '>': IROpcode.CMP_GT, '>=': IROpcode.CMP_GE,
            '^': IROpcode.XOR,
            '&': IROpcode.AND, '|': IROpcode.OR
        }
        opcode = opcode_map.get(op)
        if opcode:
            instr = IRInstruction(opcode, [dest, left, right])
            if ir_type:
                dest.ir_type = ir_type

            if ir_type and ir_type.name == 'float' and opcode in [
                IROpcode.CMP_EQ, IROpcode.CMP_NE, IROpcode.CMP_LT,
                IROpcode.CMP_LE, IROpcode.CMP_GT, IROpcode.CMP_GE
            ]:
                instr.is_float_comparison = True

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
        if ir_type:
            if ir_type.name == 'int':
                return 4
            elif ir_type.name == 'float':
                return 4
            elif ir_type.name == 'bool':
                return 1
            elif ir_type.name == 'void':
                return 0
        return 4