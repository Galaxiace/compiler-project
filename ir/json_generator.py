# ir/json_generator.py
"""
Генерация JSON представления IR.
"""

import json
from typing import Any, Dict, List

from .control_flow import IRProgram, IRFunction
from .basic_block import BasicBlock
from .ir_instructions import IRInstruction, IROperand, PhiInst, LabelInst


class IRJsonGenerator:
    """Генерирует JSON представление IR программы."""

    def generate(self, program: IRProgram) -> str:
        """Генерирует JSON строку для IR программы."""
        data = self._serialize_program(program)
        return json.dumps(data, indent=2, ensure_ascii=False)

    def _serialize_program(self, program: IRProgram) -> Dict[str, Any]:
        """Сериализует IR программу."""
        return {
            "global_vars": {
                name: self._serialize_operand(var)
                for name, var in program.global_vars.items()
            },
            "functions": [
                self._serialize_function(func)
                for func in program.functions
            ]
        }

    def _serialize_function(self, func: IRFunction) -> Dict[str, Any]:
        """Сериализует IR функцию."""
        return {
            "name": func.name,
            "return_type": func.return_type.name if func.return_type else "void",
            "parameters": [
                self._serialize_operand(p) for p in func.parameters
            ],
            "blocks": [
                self._serialize_block(b) for b in func.blocks
            ],
            "entry_block": func.entry_block.label if func.entry_block else None,
            "exit_block": func.exit_block.label if func.exit_block else None
        }

    def _serialize_block(self, block: BasicBlock) -> Dict[str, Any]:
        """Сериализует базовый блок."""
        return {
            "label": block.label,
            "instructions": [
                self._serialize_instruction(instr)
                for instr in block.instructions
            ],
            "predecessors": [p.label for p in block.predecessors],
            "successors": [s.label for s in block.successors]
        }

    def _serialize_instruction(self, instr: IRInstruction) -> Dict[str, Any]:
        """Сериализует инструкцию IR."""
        if isinstance(instr, LabelInst):
            return {
                "type": "label",
                "name": instr.name
            }
        elif isinstance(instr, PhiInst):
            return {
                "type": "phi",
                "opcode": instr.opcode.name,
                "dest": self._serialize_operand(instr.operands[0]),
                "sources": [
                    {"value": self._serialize_operand(val), "block": block}
                    for val, block in instr.sources
                ],
                "comment": instr.comment
            }
        else:
            return {
                "type": "instruction",
                "opcode": instr.opcode.name,
                "operands": [
                    self._serialize_operand(op) for op in instr.operands
                ],
                "comment": instr.comment
            }

    def _serialize_operand(self, op: IROperand) -> Dict[str, Any]:
        """Сериализует операнд IR."""
        result = {
            "type": op.operand_type.name,
            "value": str(op.value) if op.value is not None else None,
            "string": str(op)
        }
        if op.ir_type:
            result["ir_type"] = op.ir_type.name if hasattr(op.ir_type, 'name') else str(op.ir_type)
        if op.operand_type.name == "MEMORY":
            result["base"] = op.base
            result["offset"] = op.offset
        return result