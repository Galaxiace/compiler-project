# ir/validator.py
"""
Валидатор IR программы.
"""

from typing import List, Set, Dict, Tuple

from .control_flow import IRProgram, IRFunction
from .basic_block import BasicBlock
from .ir_instructions import IRInstruction, IROpcode, IROperandType, PhiInst


class IRValidator:
    """Проверяет корректность IR программы."""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate(self, program: IRProgram) -> Tuple[List[str], List[str]]:
        """
        Проверяет IR программу.

        Returns:
            tuple: (errors, warnings)
        """
        self.errors = []
        self.warnings = []

        # Проверяем каждую функцию
        for func in program.functions:
            self._validate_function(func)

        # Проверяем, что все вызываемые функции существуют
        self._validate_calls(program)

        return self.errors, self.warnings

    def _validate_function(self, func: IRFunction):
        """Проверяет функцию IR."""
        # Проверка наличия entry блока
        if not func.entry_block:
            self.errors.append(f"Function '{func.name}': missing entry block")

        # Собираем все метки
        labels: Set[str] = set()
        for block in func.blocks:
            labels.add(block.label)

        # Проверяем достижимость entry блока
        reachable = self._compute_reachable_blocks(func)
        for block in func.blocks:
            if block not in reachable:
                self.warnings.append(
                    f"Function '{func.name}', block '{block.label}': unreachable block"
                )

        # Проверяем каждый блок
        defined_temps: Dict[str, BasicBlock] = {}
        for block in func.blocks:
            self._validate_block(block, func, labels, defined_temps)

        # Проверяем PHI nodes
        for block in func.blocks:
            self._validate_phi_nodes(block, func)

    def _compute_reachable_blocks(self, func: IRFunction) -> Set[BasicBlock]:
        """Вычисляет достижимые блоки от entry."""
        if not func.entry_block:
            return set()

        reachable = set()
        worklist = [func.entry_block]

        while worklist:
            block = worklist.pop()
            if block in reachable:
                continue
            reachable.add(block)
            worklist.extend(block.successors)

        return reachable

    def _validate_block(self, block: BasicBlock, func: IRFunction,
                        all_labels: Set[str], defined_temps: Dict[str, BasicBlock]):
        """Проверяет базовый блок."""
        # Проверка терминатора
        if not block.is_terminated():
            self.errors.append(
                f"Function '{func.name}', block '{block.label}': "
                f"block not terminated with control flow instruction"
            )

        # Проверка инструкций
        for instr in block.instructions:
            self._validate_instruction(instr, func, block, all_labels, defined_temps)

    def _validate_instruction(self, instr: IRInstruction, func: IRFunction,
                              block: BasicBlock, all_labels: Set[str],
                              defined_temps: Dict[str, BasicBlock]):
        """Проверяет отдельную инструкцию."""
        # Проверка переходов на существующие метки
        if instr.opcode in (IROpcode.JUMP, IROpcode.JUMP_IF, IROpcode.JUMP_IF_NOT):
            for op in instr.operands:
                if op.operand_type == IROperandType.LABEL:
                    label_name = str(op.value)
                    if label_name not in all_labels:
                        self.errors.append(
                            f"Function '{func.name}', block '{block.label}': "
                            f"jump to undefined label '{label_name}'"
                        )

        # Проверка использования неопределённых временных
        for op in instr.operands:
            if op.operand_type == IROperandType.TEMPORARY:
                temp_name = str(op.value)
                if temp_name not in defined_temps:
                    # Может быть параметром
                    is_param = any(p.value == temp_name for p in func.parameters)
                    if not is_param:
                        self.errors.append(
                            f"Function '{func.name}', block '{block.label}': "
                            f"use of undefined temporary '%{temp_name}'"
                        )

        # Отслеживание определённых временных
        if instr.opcode in (IROpcode.ADD, IROpcode.SUB, IROpcode.MUL, IROpcode.DIV,
                            IROpcode.MOD, IROpcode.LOAD, IROpcode.ALLOCA, IROpcode.CALL,
                            IROpcode.NEG, IROpcode.NOT, IROpcode.AND, IROpcode.OR,
                            IROpcode.XOR, IROpcode.CMP_EQ, IROpcode.CMP_NE,
                            IROpcode.CMP_LT, IROpcode.CMP_LE, IROpcode.CMP_GT,
                            IROpcode.CMP_GE, IROpcode.MOVE, IROpcode.GEP):
            if instr.operands:
                dest = instr.operands[0]
                if dest.operand_type == IROperandType.TEMPORARY:
                    temp_name = str(dest.value)
                    if temp_name in defined_temps:
                        self.warnings.append(
                            f"Function '{func.name}', block '{block.label}': "
                            f"temporary '%{temp_name}' redefined"
                        )
                    defined_temps[temp_name] = block

    def _validate_phi_nodes(self, block: BasicBlock, func: IRFunction):
        """Проверяет PHI инструкции."""
        for instr in block.instructions:
            if isinstance(instr, PhiInst):
                # PHI должен иметь источник для каждого предшественника
                source_blocks = {block_name for _, block_name in instr.sources}
                pred_labels = {p.label for p in block.predecessors}

                if source_blocks != pred_labels:
                    self.errors.append(
                        f"Function '{func.name}', block '{block.label}': "
                        f"PHI node sources ({source_blocks}) don't match "
                        f"predecessors ({pred_labels})"
                    )

    def _validate_calls(self, program: IRProgram):
        """Проверяет, что все вызываемые функции существуют."""
        function_names = {func.name for func in program.functions}

        for func in program.functions:
            for block in func.blocks:
                for instr in block.instructions:
                    if instr.opcode == IROpcode.CALL:
                        if len(instr.operands) >= 2:
                            callee_op = instr.operands[1]
                            if callee_op.operand_type == IROperandType.LITERAL:
                                callee = str(callee_op.value)
                                if callee not in function_names:
                                    self.errors.append(
                                        f"Function '{func.name}', block '{block.label}': "
                                        f"call to undefined function '{callee}'"
                                    )

    def is_valid(self, program: IRProgram) -> bool:
        """Проверяет, валидна ли программа."""
        self.validate(program)
        return len(self.errors) == 0