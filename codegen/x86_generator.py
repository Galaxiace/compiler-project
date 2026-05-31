# codegen/x86_generator.py
"""
Генератор x86-64 ассемблерного кода из IR представления.
"""

import sys
import struct
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from ir.ir_instructions import IROpcode, IROperandType
from .stack_frame import StackFrame


class X86Generator:
    def __init__(self, ir_program):
        self.ir_program = ir_program
        self.output = []
        self.current_stack_frame = None
        self.current_function_name = None
        self.string_literals = []
        self.float_literals = []
        self.emitted_labels = set()
        self.param_to_temp = {}
        self.pending_params = []
        self.float_compare_counter = 0
        self.external_functions = set()
        self.emitted_globals = set()

    def generate(self) -> str:
        self.output = []
        self.float_literals = []
        self.string_literals = []
        self.external_functions = set()
        self.emitted_globals = set()

        self._collect_external_functions()
        self._generate_data_section()

        self.output.append("section .text")
        self._generate_extern_declarations()

        for func in self.ir_program.functions:
            self._generate_function(func)

        # Генерируем .rodata ПОСЛЕ всех функций
        self._generate_rodata_section()

        return "\n".join(self.output)

    def _collect_external_functions(self):
        for func in self.ir_program.functions:
            for block in func.blocks:
                for instr in block.instructions:
                    if instr.opcode == IROpcode.CALL and len(instr.operands) >= 2:
                        callee = instr.operands[1]
                        if callee.operand_type == IROperandType.LITERAL:
                            callee_name = str(callee.value)
                            is_defined = any(f.name == callee_name for f in self.ir_program.functions)
                            if not is_defined:
                                self.external_functions.add(callee_name)

    def _generate_extern_declarations(self):
        for func in self.external_functions:
            self.output.append(f"extern {func}")
        if self.external_functions:
            self.output.append("")
        self.output.append("extern print_int, print_string, read_int, exit, malloc, free")
        self.output.append("")

    def _generate_data_section(self):
        bss_lines = []
        data_lines = []

        for name, var in self.ir_program.global_vars.items():
            if hasattr(var, 'ir_type') and var.ir_type:
                type_name = var.ir_type.name if hasattr(var.ir_type, 'name') else 'int'
                if type_name == 'int':
                    bss_lines.append(f"    {name}: resd 1")
                elif type_name == 'float':
                    data_lines.append(f"    {name}: dd 0.0")
                elif type_name == 'bool':
                    bss_lines.append(f"    {name}: resb 1")
                elif type_name.startswith('array'):
                    size = getattr(var.ir_type, 'array_size', 10) * 4
                    bss_lines.append(f"    {name}: resb {size}")
                else:
                    bss_lines.append(f"    {name}: resq 1")
            else:
                bss_lines.append(f"    {name}: resq 1")

        if bss_lines:
            self.output.append("section .bss")
            for line in bss_lines:
                self.output.append(line)
            self.output.append("")

        if data_lines:
            self.output.append("section .data")
            for line in data_lines:
                self.output.append(line)
            self.output.append("")

    def _generate_rodata_section(self):
        rodata_lines = []
        for i, (label, string) in enumerate(self.string_literals):
            escaped = self._escape_string(string)
            rodata_lines.append(f"{label}: db {escaped}, 0")
        for label, val in self.float_literals:
            bits = struct.unpack('>I', struct.pack('>f', val))[0]
            rodata_lines.append(f"{label}: dd {bits}  ; float {val}")
        if rodata_lines:
            self.output.append("section .rodata")
            for line in rodata_lines:
                self.output.append(f"    {line}")
            self.output.append("")

    def _escape_string(self, s: str) -> str:
        """Преобразует строку в формат NASM с escape-последовательностями."""
        result = []
        current_chars = []

        def flush_chars():
            if current_chars:
                result.append("'" + "".join(current_chars) + "'")
                current_chars.clear()

        for ch in s:
            if ch == '\n':
                flush_chars()
                result.append('10')
            elif ch == '\t':
                flush_chars()
                result.append('9')
            elif ch == "'":
                current_chars.append("', 39, '")
            elif 32 <= ord(ch) < 127:
                current_chars.append(ch)
            else:
                current_chars.append(str(ord(ch)))

        flush_chars()

        if not result:
            return "''"
        return ", ".join(result)

    def _is_float_type(self, operand) -> bool:
        if hasattr(operand, 'ir_type') and operand.ir_type:
            type_name = operand.ir_type.name if hasattr(operand.ir_type, 'name') else ''
            return type_name == 'float'
        return False

    def _is_float_op_str(self, op_str: str) -> bool:
        return 'LC' in op_str or 'LC' in str(op_str)

    def _is_ptr_type(self, operand) -> bool:
        if hasattr(operand, 'ir_type') and operand.ir_type:
            if hasattr(operand.ir_type, 'is_array') and operand.ir_type.is_array:
                return True
            if hasattr(operand.ir_type, 'is_struct') and operand.ir_type.is_struct:
                return True
            if hasattr(operand.ir_type, 'name'):
                name = operand.ir_type.name
                if name == 'ptr' or name.startswith('ptr'):
                    return True
        return False

    def _make_label(self, label: str) -> str:
        # Строковые и float метки не префиксуем
        if label.startswith('str_') or label.startswith('LC'):
            return label
        if label.startswith('.'):
            return f"{self.current_function_name}{label}"
        return f"{self.current_function_name}.{label}"

    def _generate_function(self, func):
        self.current_function_name = func.name
        self.current_stack_frame = StackFrame()
        self.emitted_labels = set()
        self.param_to_temp = {}
        self.pending_params = []
        self.float_compare_counter = 0

        # Выводим блоки в правильном порядке: entry, потом в порядке следования в IR
        blocks_in_order = self._order_blocks(func)
        for block in blocks_in_order:
            for instr in block.instructions:
                if instr.opcode == IROpcode.MOVE and len(instr.operands) >= 2:
                    dest = instr.operands[0]
                    src = instr.operands[1]
                    if src.operand_type == IROperandType.VARIABLE:
                        for param in func.parameters:
                            if param.value == src.value:
                                self.param_to_temp[param.value] = dest.value
                                break

        temps_in_func = {}
        for block in func.blocks:
            for instr in block.instructions:
                for op in instr.operands:
                    if op.operand_type == IROperandType.TEMPORARY:
                        if self._is_ptr_type(op):
                            size = 8
                        else:
                            size = 4
                        temps_in_func[op.value] = max(temps_in_func.get(op.value, 4), size)

        for temp_name, size in temps_in_func.items():
            self.current_stack_frame.allocate(temp_name, size)

        for name, var_type in func.local_vars.items():
            if hasattr(var_type, 'is_struct') and var_type.is_struct:
                continue
            if hasattr(var_type, 'is_array') and var_type.is_array:
                continue

            size = 4
            if hasattr(var_type, 'size_bytes'):
                size = var_type.size_bytes
            elif hasattr(var_type, 'name'):
                type_sizes = {'int': 4, 'float': 4, 'bool': 1}
                size = type_sizes.get(var_type.name, 4)
            self.current_stack_frame.allocate(name, size)

        for param in func.parameters:
            param_name = param.value if hasattr(param, 'value') else str(param)
            param_size = 4
            if hasattr(param, 'ir_type') and param.ir_type:
                type_name = param.ir_type.name if hasattr(param.ir_type, 'name') else 'int'
                if type_name == 'float':
                    param_size = 4

            if param_name in self.param_to_temp:
                temp_name = self.param_to_temp[param_name]
                temp_offset = self.current_stack_frame.get_offset(temp_name)
                if temp_offset is not None:
                    self.current_stack_frame.variables[param_name] = (temp_offset, param_size)
            elif param_name not in self.current_stack_frame.variables:
                self.current_stack_frame.allocate(param_name, param_size)

        if func.name not in self.emitted_globals:
            self.output.append(f"global {func.name}")
            self.emitted_globals.add(func.name)

        self.output.append(f"{func.name}:")
        self._emit("push rbp")
        self._emit("mov rbp, rsp")

        total_size = self.current_stack_frame.get_total_size()
        if total_size > 0:
            self._emit(f"sub rsp, {total_size}")

        self._save_parameters(func)

        for block in func.blocks:
            unique_label = self._make_label(block.label)
            if unique_label not in self.emitted_labels:
                self.emitted_labels.add(unique_label)
                self.output.append(f"{unique_label}:")

            for instr in block.instructions:
                if instr.opcode == IROpcode.ALLOCA:
                    self._translate_alloca(instr, func)
                    continue

                if instr.opcode == IROpcode.MOVE and len(instr.operands) >= 2:
                    src = instr.operands[1]
                    if src.operand_type == IROperandType.VARIABLE:
                        is_param = any(p.value == src.value for p in func.parameters)
                        if is_param:
                            continue

                if instr.opcode == IROpcode.PARAM:
                    self.pending_params.append(instr)
                    continue

                if instr.opcode == IROpcode.CALL:
                    for param_instr in self.pending_params:
                        asm = self._translate_instruction(param_instr, func)
                        if asm:
                            for line in asm.split('\n'):
                                line = line.strip()
                                if line:
                                    self._emit(line)
                    self.pending_params = []

                    asm = self._translate_instruction(instr, func)
                    if asm:
                        for line in asm.split('\n'):
                            line = line.strip()
                            if line:
                                self._emit(line)

                    if len(instr.operands) > 0:
                        dest = instr.operands[0]
                        if dest.operand_type == IROperandType.TEMPORARY:
                            dest_str = self._op(dest)
                            is_float = self._is_float_type(dest)
                            is_ptr = self._is_ptr_type(dest)
                            if is_float:
                                self._emit(f"movss {dest_str}, xmm0")
                            elif is_ptr:
                                self._emit(f"mov qword {dest_str}, rax")
                            else:
                                self._emit(f"mov dword {dest_str}, eax")
                    continue

                asm = self._translate_instruction(instr, func)
                if asm:
                    for line in asm.split('\n'):
                        line = line.strip()
                        if line:
                            self._emit(line)

        return_label = self._make_label(f"{func.name}_return")
        if return_label not in self.emitted_labels:
            self.emitted_labels.add(return_label)
            self.output.append(f"{return_label}:")
        self._emit("mov rsp, rbp")
        self._emit("pop rbp")
        self._emit("ret")
        self.output.append("")


    def _translate_alloca(self, instr, func):
        """ALLOCA для структур (стек)."""
        ops = instr.operands
        if len(ops) >= 2:
            dest = ops[0]
            size = ops[1].value
            aligned_size = (size + 15) & ~15
            self._emit(f"sub rsp, {aligned_size}")

            dest_name = dest.value
            offset = self.current_stack_frame.get_offset(dest_name)
            if offset is None:
                offset = self.current_stack_frame.allocate(dest_name, 8)

            self._emit(f"mov qword [rbp{offset}], rsp")

    def _order_blocks(self, func):
        """Упорядочивает блоки для корректного вывода: entry первым, затем по связям."""
        blocks = list(func.blocks)
        if not blocks:
            return blocks

        # Начинаем с entry блока
        ordered = []
        visited = set()

        # Находим entry блок
        entry = func.entry_block if hasattr(func, 'entry_block') else blocks[0]

        def dfs(block):
            if block.label in visited:
                return
            visited.add(block.label)
            ordered.append(block)

            # Ищем, куда ведут переходы из этого блока
            for instr in block.instructions:
                if instr.opcode in (IROpcode.JUMP, IROpcode.JUMP_IF, IROpcode.JUMP_IF_NOT):
                    for op in instr.operands:
                        if op.operand_type == IROperandType.LABEL:
                            target_label = op.value
                            # Ищем блок с такой меткой
                            for b in blocks:
                                if b.label == target_label and b.label not in visited:
                                    dfs(b)
                                    break

        dfs(entry)

        # Добавляем оставшиеся блоки (если есть недостижимые)
        for block in blocks:
            if block.label not in visited:
                ordered.append(block)

        return ordered

    def _save_parameters(self, func):
        int_regs_64 = ['rdi', 'rsi', 'rdx', 'rcx', 'r8', 'r9']
        int_regs_32 = ['edi', 'esi', 'edx', 'ecx', 'r8d', 'r9d']
        float_regs = ['xmm0', 'xmm1', 'xmm2', 'xmm3', 'xmm4', 'xmm5', 'xmm6', 'xmm7']
        int_idx = 0
        float_idx = 0

        for param in func.parameters:
            param_name = param.value if hasattr(param, 'value') else str(param)
            offset = self.current_stack_frame.get_offset(param_name)
            if offset is None:
                continue

            is_float = self._is_float_type(param)
            is_ptr = self._is_ptr_type(param)

            if is_float and float_idx < len(float_regs):
                self._emit(f"movss dword [rbp{offset}], {float_regs[float_idx]}")
                float_idx += 1
            elif is_ptr and int_idx < len(int_regs_64):
                self._emit(f"mov qword [rbp{offset}], {int_regs_64[int_idx]}")
                int_idx += 1
            elif not is_float and int_idx < len(int_regs_32):
                self._emit(f"mov dword [rbp{offset}], {int_regs_32[int_idx]}")
                int_idx += 1

    def _translate_instruction(self, instr, func):
        opcode = instr.opcode
        ops = instr.operands

        is_float_compare = getattr(instr, 'is_float_comparison', False)
        is_float = self._is_float_type(ops[0]) if ops else False

        if opcode == IROpcode.ALLOCA:
            return None

        elif opcode == IROpcode.MOVE:
            if len(ops) < 2:
                return None
            dest = self._op(ops[0])
            src = self._op(ops[1])
            if dest == src:
                return None

            is_float_move = self._is_float_type(ops[0]) or self._is_float_type(ops[1]) or self._is_float_op_str(src)
            is_ptr_move = self._is_ptr_type(ops[0]) or self._is_ptr_type(ops[1])

            if is_float_move:
                return f"movss xmm0, {src}\n    movss {dest}, xmm0"
            elif is_ptr_move:
                return f"mov rax, qword {src}\n    mov qword {dest}, rax"
            else:
                return f"mov eax, dword {src}\n    mov dword {dest}, eax"

        elif opcode == IROpcode.RETURN:
            if ops:
                ret_val = self._op(ops[0])
                ret_label = self._make_label(f"{func.name}_return")
                if self._is_float_type(ops[0]):
                    return f"movss xmm0, {ret_val}\n    jmp {ret_label}"
                return f"mov eax, dword {ret_val}\n    jmp {ret_label}"
            else:
                ret_label = self._make_label(f"{func.name}_return")
                return f"xor eax, eax\n    jmp {ret_label}"

        elif opcode == IROpcode.CALL:
            if len(ops) < 2:
                return None
            callee = ops[1].value
            # Для variadic-функций обнуляем AL (количество XMM-регистров)
            if callee in ('printf', 'scanf', 'fprintf', 'sprintf') or callee in self.external_functions:
                return f"xor eax, eax\n    call {callee}"
            return f"call {callee}"

        elif opcode == IROpcode.PARAM:
            if len(ops) < 2:
                return None
            idx = ops[0].value
            if isinstance(idx, int):
                val = self._op(ops[1])
                is_float_param = self._is_float_type(ops[1]) or self._is_float_op_str(val)
                is_ptr_param = self._is_ptr_type(ops[1])
                if is_float_param:
                    float_regs = ['xmm0', 'xmm1', 'xmm2', 'xmm3', 'xmm4', 'xmm5', 'xmm6', 'xmm7']
                    if idx < len(float_regs):
                        return f"movss {float_regs[idx]}, {val}"
                elif is_ptr_param:
                    int_regs = ['rdi', 'rsi', 'rdx', 'rcx', 'r8', 'r9']
                    if idx < len(int_regs):
                        return f"mov {int_regs[idx]}, {val}"
                else:
                    int_regs = ['edi', 'esi', 'edx', 'ecx', 'r8d', 'r9d']
                    if idx < len(int_regs):
                        return f"mov {int_regs[idx]}, {val}"
            return None

        elif opcode == IROpcode.JUMP:
            target = self._make_label(ops[0].value)
            return f"jmp {target}"

        elif opcode == IROpcode.JUMP_IF:
            cond = self._op(ops[0])
            target = self._make_label(ops[1].value)
            return f"cmp dword {cond}, 0\n    jne {target}"

        elif opcode == IROpcode.JUMP_IF_NOT:
            cond = self._op(ops[0])
            target = self._make_label(ops[1].value)
            return f"cmp dword {cond}, 0\n    je {target}"

        elif opcode in [IROpcode.CMP_EQ, IROpcode.CMP_NE, IROpcode.CMP_LT,
                        IROpcode.CMP_LE, IROpcode.CMP_GT, IROpcode.CMP_GE]:

            dest = self._op(ops[0])
            left = self._op(ops[1])
            right = self._op(ops[2])

            if is_float_compare or self._is_float_type(ops[1]) or self._is_float_type(ops[2]):
                return self._translate_float_comparison(opcode, dest, left, right)

            setcc_map = {
                IROpcode.CMP_EQ: "sete",
                IROpcode.CMP_NE: "setne",
                IROpcode.CMP_LT: "setl",
                IROpcode.CMP_LE: "setle",
                IROpcode.CMP_GT: "setg",
                IROpcode.CMP_GE: "setge"
            }
            return f"mov eax, dword {left}\n    cmp eax, dword {right}\n    {setcc_map[opcode]} al\n    movzx eax, al\n    mov dword {dest}, eax"

        elif opcode == IROpcode.ADD:
            dest = self._op(ops[0])
            src1 = self._op(ops[1])
            src2 = self._op(ops[2])
            if is_float:
                if dest == src1:
                    return f"addss {dest}, {src2}"
                return f"movss xmm0, {src1}\n    addss xmm0, {src2}\n    movss {dest}, xmm0"
            else:
                is_ptr = self._is_ptr_type(ops[1])
                if is_ptr:
                    if ops[2].operand_type == IROperandType.LITERAL:
                        return f"mov rax, qword {src1}\n    add rax, {src2}\n    mov qword {dest}, rax"
                    else:
                        return f"mov rax, qword {src1}\n    movsxd rdx, dword {src2}\n    add rax, rdx\n    mov qword {dest}, rax"
                else:
                    if dest == src1:
                        return f"add dword {dest}, {src2}"
                    return f"mov eax, dword {src1}\n    add eax, dword {src2}\n    mov dword {dest}, eax"

        elif opcode == IROpcode.SUB:
            dest = self._op(ops[0])
            src1 = self._op(ops[1])
            src2 = self._op(ops[2])
            if is_float:
                if dest == src1:
                    return f"subss {dest}, {src2}"
                return f"movss xmm0, {src1}\n    subss xmm0, {src2}\n    movss {dest}, xmm0"
            else:
                if dest == src1:
                    return f"sub dword {dest}, {src2}"
                return f"mov eax, dword {src1}\n    sub eax, dword {src2}\n    mov dword {dest}, eax"

        elif opcode == IROpcode.MUL:
            dest = self._op(ops[0])
            src1 = self._op(ops[1])
            src2 = self._op(ops[2])
            if is_float or self._is_float_op_str(src1) or self._is_float_op_str(src2):
                if dest == src1:
                    return f"mulss {dest}, {src2}"
                return f"movss xmm0, {src1}\n    mulss xmm0, {src2}\n    movss {dest}, xmm0"
            else:
                if dest == src1:
                    return f"imul dword {dest}, {src2}"
                return f"mov eax, dword {src1}\n    imul eax, dword {src2}\n    mov dword {dest}, eax"

        elif opcode == IROpcode.DIV:
            dest = self._op(ops[0])
            left = self._op(ops[1])
            right = self._op(ops[2])
            if is_float:
                if dest == left:
                    return f"divss {dest}, {right}"
                return f"movss xmm0, {left}\n    divss xmm0, {right}\n    movss {dest}, xmm0"
            else:
                if ops[2].operand_type == IROperandType.LITERAL:
                    return f"mov eax, dword {left}\n    cdq\n    mov ecx, {right}\n    idiv ecx\n    mov dword {dest}, eax"
                return f"mov eax, dword {left}\n    cdq\n    idiv dword {right}\n    mov dword {dest}, eax"

        elif opcode == IROpcode.MOD:
            dest = self._op(ops[0])
            left = self._op(ops[1])
            right = self._op(ops[2])
            # Если right - литерал, загружаем в регистр
            if ops[2].operand_type == IROperandType.LITERAL:
                return f"mov eax, dword {left}\n    cdq\n    mov ecx, {right}\n    idiv ecx\n    mov dword {dest}, edx"
            return f"mov eax, dword {left}\n    cdq\n    idiv dword {right}\n    mov dword {dest}, edx"

        elif opcode == IROpcode.NEG:
            dest = self._op(ops[0])
            src = self._op(ops[1])
            if is_float:
                return f"movss xmm0, {src}\n    xorps xmm0, xmm0\n    subss xmm0, {src}\n    movss {dest}, xmm0"
            if dest == src:
                return f"neg dword {dest}"
            return f"mov eax, dword {src}\n    neg eax\n    mov dword {dest}, eax"

        elif opcode == IROpcode.NOT:
            dest = self._op(ops[0])
            src = self._op(ops[1])
            if dest == src:
                return f"not dword {dest}"
            return f"mov eax, dword {src}\n    not eax\n    mov dword {dest}, eax"

        elif opcode == IROpcode.AND:
            dest = self._op(ops[0])
            src1 = self._op(ops[1])
            src2 = self._op(ops[2])
            if dest == src1:
                return f"and dword {dest}, {src2}"
            return f"mov eax, dword {src1}\n    and eax, dword {src2}\n    mov dword {dest}, eax"

        elif opcode == IROpcode.OR:
            dest = self._op(ops[0])
            src1 = self._op(ops[1])
            src2 = self._op(ops[2])
            if dest == src1:
                return f"or dword {dest}, {src2}"
            return f"mov eax, dword {src1}\n    or eax, dword {src2}\n    mov dword {dest}, eax"

        elif opcode == IROpcode.XOR:
            dest = self._op(ops[0])
            src1 = self._op(ops[1])
            src2 = self._op(ops[2])
            if dest == src1:
                return f"xor dword {dest}, {src2}"
            return f"mov eax, dword {src1}\n    xor eax, dword {src2}\n    mov dword {dest}, eax"

        elif opcode == IROpcode.LOAD:
            if len(ops) < 2:
                return None
            dest = self._op(ops[0])
            src = self._op(ops[1])

            # Если src - глобальная переменная (не содержит '['), читаем напрямую
            if '[' not in src:
                if self._is_float_type(ops[0]):
                    return f"movss xmm0, dword [{src}]\n    movss {dest}, xmm0"
                else:
                    return f"mov eax, dword [{src}]\n    mov dword {dest}, eax"

            if self._is_float_type(ops[0]):
                return f"mov rbx, qword {src}\n    movss xmm0, dword [rbx]\n    movss {dest}, xmm0"
            else:
                return f"mov rbx, qword {src}\n    mov eax, dword [rbx]\n    mov dword {dest}, eax"

        elif opcode == IROpcode.STORE:
            if len(ops) < 2:
                return None
            addr = self._op(ops[0])
            src = self._op(ops[1])

            # Если адрес - глобальная переменная (не содержит '['), пишем напрямую
            if '[' not in addr:
                if self._is_float_type(ops[1]):
                    return f"movss xmm0, {src}\n    movss dword [{addr}], xmm0"
                else:
                    return f"mov eax, dword {src}\n    mov dword [{addr}], eax"

            if self._is_float_type(ops[1]):
                return f"mov rbx, qword {addr}\n    movss xmm0, {src}\n    movss dword [rbx], xmm0"
            else:
                return f"mov rbx, qword {addr}\n    mov eax, dword {src}\n    mov dword [rbx], eax"

        return f"; Unknown: {opcode.name}"

    def _translate_float_comparison(self, opcode, dest, left, right):
        counter = self.float_compare_counter
        self.float_compare_counter += 1

        unordered_label = self._make_label(f".unordered_{counter}")
        equal_label = self._make_label(f".equal_{counter}")
        ne_label = self._make_label(f".ne_{counter}")
        lt_label = self._make_label(f".lt_{counter}")
        le_label = self._make_label(f".le_{counter}")
        gt_label = self._make_label(f".gt_{counter}")
        ge_label = self._make_label(f".ge_{counter}")
        end_label = self._make_label(f".end_{counter}")

        if opcode == IROpcode.CMP_EQ:
            return f"""; Float comparison EQ
    movss xmm0, {left}
    ucomiss xmm0, {right}
    jp {unordered_label}
    je {equal_label}
    mov eax, 0
    jmp {end_label}
{unordered_label}:
    mov eax, 0
    jmp {end_label}
{equal_label}:
    mov eax, 1
{end_label}:
    mov dword {dest}, eax"""

        elif opcode == IROpcode.CMP_NE:
            return f"""; Float comparison NE
    movss xmm0, {left}
    ucomiss xmm0, {right}
    jp {unordered_label}
    jne {ne_label}
    mov eax, 0
    jmp {end_label}
{unordered_label}:
    mov eax, 1
    jmp {end_label}
{ne_label}:
    mov eax, 1
{end_label}:
    mov dword {dest}, eax"""

        elif opcode == IROpcode.CMP_LT:
            return f"""; Float comparison LT
    movss xmm0, {left}
    ucomiss xmm0, {right}
    jp {unordered_label}
    jb {lt_label}
    mov eax, 0
    jmp {end_label}
{unordered_label}:
    mov eax, 0
    jmp {end_label}
{lt_label}:
    mov eax, 1
{end_label}:
    mov dword {dest}, eax"""

        elif opcode == IROpcode.CMP_LE:
            return f"""; Float comparison LE
    movss xmm0, {left}
    ucomiss xmm0, {right}
    jp {unordered_label}
    jbe {le_label}
    mov eax, 0
    jmp {end_label}
{unordered_label}:
    mov eax, 0
    jmp {end_label}
{le_label}:
    mov eax, 1
{end_label}:
    mov dword {dest}, eax"""

        elif opcode == IROpcode.CMP_GT:
            return f"""; Float comparison GT (swapped)
    movss xmm0, {right}
    ucomiss xmm0, {left}
    jp {unordered_label}
    jb {gt_label}
    mov eax, 0
    jmp {end_label}
{unordered_label}:
    mov eax, 0
    jmp {end_label}
{gt_label}:
    mov eax, 1
{end_label}:
    mov dword {dest}, eax"""

        elif opcode == IROpcode.CMP_GE:
            return f"""; Float comparison GE (swapped)
    movss xmm0, {right}
    ucomiss xmm0, {left}
    jp {unordered_label}
    jbe {ge_label}
    mov eax, 0
    jmp {end_label}
{unordered_label}:
    mov eax, 0
    jmp {end_label}
{ge_label}:
    mov eax, 1
{end_label}:
    mov dword {dest}, eax"""

        return f"; Unknown float comparison: {opcode}"

    def _op(self, operand):
        if operand.operand_type == IROperandType.TEMPORARY:
            offset = self.current_stack_frame.get_offset(operand.value)
            if offset is not None:
                return f"[rbp{offset}]"
            return f"[rbp-8]"

        elif operand.operand_type == IROperandType.VARIABLE:
            offset = self.current_stack_frame.get_offset(operand.value)
            if offset is not None:
                return f"[rbp{offset}]"
            return f"[{operand.value}]"

        elif operand.operand_type == IROperandType.LITERAL:
            val = operand.value
            if isinstance(val, float):
                label = f"LC{len(self.float_literals)}"
                self.float_literals.append((label, val))
                return f"dword [{label}]"
            elif isinstance(val, bool):
                return "1" if val else "0"
            elif isinstance(val, str):
                label = f"str_{len(self.string_literals)}"
                self.string_literals.append((label, val))
                return label
            return str(val)

        elif operand.operand_type == IROperandType.LABEL:
            return self._make_label(str(operand.value))

        elif operand.operand_type == IROperandType.GLOBAL:
            # Возвращаем просто имя, LOAD/STORE сами добавят скобки
            return operand.value

        return str(operand.value)

    def _emit(self, line: str, indent: bool = True):
        if indent:
            self.output.append(f"    {line}")
        else:
            self.output.append(line)