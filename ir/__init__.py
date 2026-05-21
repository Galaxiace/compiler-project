# ir/__init__.py
"""
Модуль для Intermediate Representation (IR).
"""

from .ir_instructions import *
from .basic_block import *
from .control_flow import *
from .ir_generator import IRGenerator
from .ir_writer import IRWriter
from .dot_generator import IRDotGenerator
from .json_generator import IRJsonGenerator
from .validator import IRValidator
from .optimizer import IROptimizer, ConstantFolder, ConstantPropagator, DeadCodeEliminator, UnreachableCodeEliminator

__all__ = [
    # IR instructions
    'IROpcode',
    'IROperandType',
    'IROperand',
    'IRInstruction',
    'Temp',
    'Var',
    'Lit',
    'Label',
    'Mem',
    'Global',
    'LabelInst',
    'PhiInst',
    # Basic blocks
    'BasicBlock',
    # Control flow
    'IRFunction',
    'IRProgram',
    # Generators
    'IRGenerator',
    'IRWriter',
    'IRDotGenerator',
    'IRJsonGenerator',
    # Validator
    'IRValidator',
    # Optimizer
    'IROptimizer',
    'ConstantFolder',
    'ConstantPropagator',
    'DeadCodeEliminator',
    'UnreachableCodeEliminator'
]