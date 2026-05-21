# ir/optimizer.py
"""
Модуль оптимизации промежуточного представления (IR).
Реализует константную свертку, распространение констант и dead code elimination.
"""

from typing import List, Dict, Set, Optional, Any, Tuple
from .control_flow import IRProgram, IRFunction
from .basic_block import BasicBlock
from .ir_instructions import (
    IRInstruction, IROpcode, IROperand, IROperandType,
    Temp, Lit, Label, Var, Global, LabelInst, PhiInst
)


class ConstantFolder:
    """Константная свертка - вычисление константных выражений на этапе компиляции."""

    def __init__(self):
        self.stats = {"folded": 0}

    def fold(self, program: IRProgram) -> IRProgram:
        """Выполняет константную свертку над всей программой."""
        for func in program.functions:
            self._fold_function(func)
        return program

    def _fold_function(self, func: IRFunction):
        """Выполняет константную свертку над одной функцией."""
        for block in func.blocks:
            self._fold_block(block)

    def _fold_block(self, block: BasicBlock):
        """Выполняет константную свертку над блоком."""
        new_instructions = []

        for instr in block.instructions:
            # Пропускаем PHI и LABEL инструкции
            if isinstance(instr, (PhiInst, LabelInst)):
                new_instructions.append(instr)
                continue

            folded_instr = self._try_fold_instruction(instr)
            new_instructions.append(folded_instr)

        block.instructions = new_instructions

    def _try_fold_instruction(self, instr: IRInstruction) -> IRInstruction:
        """Пытается свернуть инструкцию, если все операнды - константы."""
        # Проверяем, все ли операнды - литералы
        all_literals = all(
            op.operand_type == IROperandType.LITERAL
            for op in instr.operands
        )

        if not all_literals:
            return instr

        # Для разных типов инструкций выполняем свертку
        if instr.opcode in (IROpcode.ADD, IROpcode.SUB, IROpcode.MUL,
                            IROpcode.DIV, IROpcode.MOD):
            return self._fold_arithmetic(instr)

        elif instr.opcode in (IROpcode.AND, IROpcode.OR, IROpcode.XOR):
            return self._fold_bitwise(instr)

        elif instr.opcode in (IROpcode.CMP_EQ, IROpcode.CMP_NE,
                              IROpcode.CMP_LT, IROpcode.CMP_LE,
                              IROpcode.CMP_GT, IROpcode.CMP_GE):
            return self._fold_comparison(instr)

        elif instr.opcode == IROpcode.NOT:
            return self._fold_not(instr)

        elif instr.opcode == IROpcode.NEG:
            return self._fold_neg(instr)

        return instr

    def _fold_arithmetic(self, instr: IRInstruction) -> IRInstruction:
        """Сворачивает арифметические операции."""
        if len(instr.operands) < 3:
            return instr

        dest = instr.operands[0]
        left = instr.operands[1]
        right = instr.operands[2]

        if not isinstance(left.value, (int, float)) or not isinstance(right.value, (int, float)):
            return instr

        try:
            if instr.opcode == IROpcode.ADD:
                result = left.value + right.value
            elif instr.opcode == IROpcode.SUB:
                result = left.value - right.value
            elif instr.opcode == IROpcode.MUL:
                result = left.value * right.value
            elif instr.opcode == IROpcode.DIV:
                if right.value == 0:
                    return instr
                result = left.value / right.value
            elif instr.opcode == IROpcode.MOD:
                if right.value == 0:
                    return instr
                result = left.value % right.value
            else:
                return instr

            # Создаем новую инструкцию MOVE с константой
            lit_type = left.ir_type if left.ir_type else right.ir_type
            lit = Lit(result, lit_type)
            self.stats["folded"] += 1
            return IRInstruction(IROpcode.MOVE, [dest, lit])

        except Exception:
            return instr

    def _fold_bitwise(self, instr: IRInstruction) -> IRInstruction:
        """Сворачивает побитовые операции."""
        if len(instr.operands) < 3:
            return instr

        dest = instr.operands[0]
        left = instr.operands[1]
        right = instr.operands[2]

        if not isinstance(left.value, int) or not isinstance(right.value, int):
            return instr

        if instr.opcode == IROpcode.AND:
            result = left.value & right.value
        elif instr.opcode == IROpcode.OR:
            result = left.value | right.value
        elif instr.opcode == IROpcode.XOR:
            result = left.value ^ right.value
        else:
            return instr

        lit = Lit(result, left.ir_type)
        self.stats["folded"] += 1
        return IRInstruction(IROpcode.MOVE, [dest, lit])

    def _fold_comparison(self, instr: IRInstruction) -> IRInstruction:
        """Сворачивает операции сравнения."""
        if len(instr.operands) < 3:
            return instr

        dest = instr.operands[0]
        left = instr.operands[1]
        right = instr.operands[2]

        if not isinstance(left.value, (int, float, bool)) or \
                not isinstance(right.value, (int, float, bool)):
            return instr

        if instr.opcode == IROpcode.CMP_EQ:
            result = left.value == right.value
        elif instr.opcode == IROpcode.CMP_NE:
            result = left.value != right.value
        elif instr.opcode == IROpcode.CMP_LT:
            result = left.value < right.value
        elif instr.opcode == IROpcode.CMP_LE:
            result = left.value <= right.value
        elif instr.opcode == IROpcode.CMP_GT:
            result = left.value > right.value
        elif instr.opcode == IROpcode.CMP_GE:
            result = left.value >= right.value
        else:
            return instr

        lit = Lit(1 if result else 0, dest.ir_type)
        self.stats["folded"] += 1
        return IRInstruction(IROpcode.MOVE, [dest, lit])

    def _fold_not(self, instr: IRInstruction) -> IRInstruction:
        """Сворачивает логическое отрицание."""
        if len(instr.operands) < 2:
            return instr

        dest = instr.operands[0]
        operand = instr.operands[1]

        if operand.operand_type != IROperandType.LITERAL:
            return instr

        result = not operand.value
        lit = Lit(1 if result else 0, dest.ir_type)
        self.stats["folded"] += 1
        return IRInstruction(IROpcode.MOVE, [dest, lit])

    def _fold_neg(self, instr: IRInstruction) -> IRInstruction:
        """Сворачивает унарный минус."""
        if len(instr.operands) < 2:
            return instr

        dest = instr.operands[0]
        operand = instr.operands[1]

        if operand.operand_type != IROperandType.LITERAL:
            return instr

        result = -operand.value
        lit = Lit(result, dest.ir_type)
        self.stats["folded"] += 1
        return IRInstruction(IROpcode.MOVE, [dest, lit])


class ConstantPropagator:
    """Распространение констант - замена переменных на известные константы."""

    def __init__(self):
        self.stats = {"propagated": 0}
        self.constants: Dict[str, Any] = {}

    def propagate(self, program: IRProgram) -> IRProgram:
        """Выполняет распространение констант."""
        for func in program.functions:
            self.constants.clear()
            self._propagate_function(func)
        return program

    def _propagate_function(self, func: IRFunction):
        """Выполняет распространение констант в функции."""
        changed = True
        iteration = 0
        max_iterations = 10

        while changed and iteration < max_iterations:
            changed = False
            for block in func.blocks:
                if self._propagate_block(block):
                    changed = True
            iteration += 1

    def _propagate_block(self, block: BasicBlock) -> bool:
        """Выполняет распространение констант в блоке."""
        changed = False
        new_instructions = []

        for instr in block.instructions:
            # Пытаемся заменить операнды на известные константы
            propagated = self._propagate_instruction(instr)
            if propagated != instr:
                changed = True

            # Если это MOVE с константой, запоминаем
            if instr.opcode == IROpcode.MOVE and len(instr.operands) >= 2:
                dest = instr.operands[0]
                src = instr.operands[1]

                if dest.operand_type == IROperandType.TEMPORARY and \
                        src.operand_type == IROperandType.LITERAL:
                    self.constants[dest.value] = src.value
                    self.stats["propagated"] += 1

            new_instructions.append(propagated)

        block.instructions = new_instructions
        return changed

    def _propagate_instruction(self, instr: IRInstruction) -> IRInstruction:
        """Заменяет операнды-переменные на известные константы."""
        new_operands = []
        changed = False

        for op in instr.operands:
            if op.operand_type == IROperandType.TEMPORARY and op.value in self.constants:
                # Заменяем на константу
                const_val = self.constants[op.value]
                lit = Lit(const_val, op.ir_type)
                new_operands.append(lit)
                changed = True
            else:
                new_operands.append(op)

        if changed:
            return IRInstruction(instr.opcode, new_operands, instr.comment)
        return instr


class DeadCodeEliminator:
    """Удаление мертвого кода - инструкций, результат которых не используется."""

    def __init__(self):
        self.stats = {"removed": 0}

    def eliminate(self, program: IRProgram) -> IRProgram:
        """Удаляет мертвый код."""
        for func in program.functions:
            self._eliminate_function(func)
        return program

    def _eliminate_function(self, func: IRFunction):
        """Удаляет мертвый код из функции."""
        for block in func.blocks:
            self._eliminate_block(block)

    def _eliminate_block(self, block: BasicBlock):
        """Удаляет мертвый код из блока."""
        used_temps: Set[str] = set()

        # Сначала собираем все используемые временные
        for instr in block.instructions:
            for op in instr.operands:
                if op.operand_type == IROperandType.TEMPORARY:
                    used_temps.add(op.value)

        # Удаляем инструкции, результат которых не используется
        new_instructions = []

        for instr in block.instructions:
            # Всегда оставляем терминаторы и инструкции с побочными эффектами
            if instr.opcode in (IROpcode.STORE, IROpcode.CALL, IROpcode.RETURN,
                                IROpcode.JUMP, IROpcode.JUMP_IF, IROpcode.JUMP_IF_NOT):
                new_instructions.append(instr)
                continue

            # PHI и LABEL инструкции всегда оставляем
            if isinstance(instr, (PhiInst, LabelInst)):
                new_instructions.append(instr)
                continue

            # Проверяем, используется ли результат
            if len(instr.operands) > 0 and instr.operands[0].operand_type == IROperandType.TEMPORARY:
                dest = instr.operands[0].value
                if dest in used_temps:
                    new_instructions.append(instr)
                else:
                    self.stats["removed"] += 1
            else:
                new_instructions.append(instr)

        block.instructions = new_instructions

    def _is_side_effect_free(self, instr: IRInstruction) -> bool:
        """Проверяет, есть ли у инструкции побочные эффекты."""
        return instr.opcode not in (IROpcode.STORE, IROpcode.CALL, IROpcode.RETURN)


class UnreachableCodeEliminator:
    """Удаление недостижимых блоков."""

    def __init__(self):
        self.stats = {"blocks_removed": 0}

    def eliminate(self, program: IRProgram) -> IRProgram:
        """Удаляет недостижимые блоки."""
        for func in program.functions:
            self._eliminate_function(func)
        return program

    def _eliminate_function(self, func: IRFunction):
        """Удаляет недостижимые блоки из функции."""
        if not func.entry_block:
            return

        # Находим достижимые блоки
        reachable = set()
        worklist = [func.entry_block]

        while worklist:
            block = worklist.pop()
            if block in reachable:
                continue
            reachable.add(block)
            worklist.extend(block.successors)

        # Удаляем недостижимые блоки
        new_blocks = [b for b in func.blocks if b in reachable]

        removed_count = len(func.blocks) - len(new_blocks)
        self.stats["blocks_removed"] += removed_count

        func.blocks = new_blocks


class IROptimizer:
    """Основной класс оптимизатора IR."""

    def __init__(self, program: IRProgram):
        self.program = program
        self.folder = ConstantFolder()
        self.propagator = ConstantPropagator()
        self.dce = DeadCodeEliminator()
        self.uce = UnreachableCodeEliminator()

        self.stats = {
            "constant_folding": 0,
            "constant_propagation": 0,
            "dead_code_removed": 0,
            "unreachable_blocks_removed": 0,
            "total_instructions_before": 0,
            "total_instructions_after": 0
        }

    def optimize(self, max_passes: int = 3) -> IRProgram:
        """Выполняет полную оптимизацию IR."""
        # Подсчет инструкций до оптимизации
        self.stats["total_instructions_before"] = self._count_instructions()

        for _ in range(max_passes):
            # Константная свертка
            self.program = self.folder.fold(self.program)

            # Распространение констант
            self.program = self.propagator.propagate(self.program)

            # Еще раз свертка после распространения
            self.program = self.folder.fold(self.program)

            # Удаление мертвого кода
            self.program = self.dce.eliminate(self.program)

            # Удаление недостижимых блоков
            self.program = self.uce.eliminate(self.program)

        # Сбор статистики
        self.stats["total_instructions_after"] = self._count_instructions()
        self.stats["constant_folding"] = self.folder.stats["folded"]
        self.stats["constant_propagation"] = self.propagator.stats["propagated"]
        self.stats["dead_code_removed"] = self.dce.stats["removed"]
        self.stats["unreachable_blocks_removed"] = self.uce.stats["blocks_removed"]

        return self.program

    def _count_instructions(self) -> int:
        """Подсчитывает общее количество инструкций в программе."""
        count = 0
        for func in self.program.functions:
            for block in func.blocks:
                count += len(block.instructions)
        return count

    def get_stats(self) -> Dict[str, int]:
        """Возвращает статистику оптимизации."""
        reduction = 0
        if self.stats["total_instructions_before"] > 0:
            reduction = int((1 - self.stats["total_instructions_after"] /
                             self.stats["total_instructions_before"]) * 100)

        return {
            **self.stats,
            "reduction_percent": reduction
        }

    def print_stats(self) -> str:
        """Возвращает отформатированную статистику оптимизации."""
        stats = self.get_stats()
        lines = [
            "Optimization Report:",
            f"  Constant folding: {stats['constant_folding']} expressions folded",
            f"  Constant propagation: {stats['constant_propagation']} variables propagated",
            f"  Dead code elimination: {stats['dead_code_removed']} instructions removed",
            f"  Unreachable blocks removed: {stats['unreachable_blocks_removed']} blocks",
            f"  Total instructions: {stats['total_instructions_before']} → {stats['total_instructions_after']}",
            f"  Reduction: {stats['reduction_percent']}%"
        ]
        return "\n".join(lines)