# codegen/stack_frame.py
"""
Управление стековым фреймом для x86-64 кодогенерации.
"""

class StackFrame:
    def __init__(self):
        self.variables = {}  # имя_переменной -> (offset, size_bytes)
        self.current_offset = 0

    def allocate(self, name: str, size_bytes: int = 8) -> int:
        """
        Выделяет место на стеке для переменной.
        Возвращает отрицательное смещение от RBP.
        """
        if name in self.variables:
            return self.variables[name][0]

        # Выравнивание по размеру
        align = size_bytes
        self.current_offset = (self.current_offset + align - 1) & ~(align - 1)
        self.current_offset += size_bytes

        offset = -self.current_offset
        self.variables[name] = (offset, size_bytes)
        return offset

    def get_offset(self, name: str) -> int | None:
        """Возвращает смещение переменной или None."""
        info = self.variables.get(name)
        return info[0] if info else None

    def get_size(self, name: str) -> int | None:
        """Возвращает размер переменной в байтах или None."""
        info = self.variables.get(name)
        return info[1] if info else None

    def get_type_name(self, name: str) -> str:
        """Возвращает строку размера для ассемблера."""
        size = self.get_size(name)
        if size == 8:
            return "qword"
        elif size == 4:
            return "dword"
        elif size == 1:
            return "byte"
        return "qword"

    def get_total_size(self) -> int:
        """
        Возвращает общий размер стекового фрейма, выровненный до 16 байт.
        System V ABI требует выравнивания стека на 16 байт перед CALL.
        """
        # +8 для сохраненного RBP
        size = self.current_offset + 8
        # Выравнивание до 16 байт
        return (size + 15) & ~15