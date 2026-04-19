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