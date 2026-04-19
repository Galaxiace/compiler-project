# ir/dot_generator.py
"""
Генерация DOT файла для визуализации CFG.
"""

from .control_flow import IRProgram, IRFunction
from .basic_block import BasicBlock


class IRDotGenerator:
    """Генерирует Graphviz DOT представление CFG."""

    def __init__(self):
        self.node_counter = 0

    def generate_program(self, program: IRProgram) -> str:
        """Генерирует DOT для всей программы."""
        lines = ["digraph CFG {", '  rankdir=TB;', '  node [shape=box, fontname="Courier"];', ""]

        for func in program.functions:
            lines.append(f"  subgraph cluster_{func.name} {{")
            lines.append(f'    label="{func.name}";')
            lines.append(f'    color=blue;')
            lines.append(f'    fontname="Arial";')
            lines.append("")

            for block in func.blocks:
                label = self._format_block_label(block)
                color = self._get_block_color(block)
                node_id = f"{func.name}_{block.label}"
                # Экранируем кавычки и переносы строк
                label = label.replace('"', '\\"').replace('\n', '\\n')
                lines.append(f'    {node_id} [label="{label}", style=filled, fillcolor={color}];')

            lines.append("  }")
            lines.append("")

        # Добавляем рёбра
        for func in program.functions:
            for block in func.blocks:
                from_id = f"{func.name}_{block.label}"
                for succ in block.successors:
                    to_id = f"{func.name}_{succ.label}"
                    lines.append(f"  {from_id} -> {to_id};")

        lines.append("}")
        return "\n".join(lines)

    def generate_function(self, func: IRFunction) -> str:
        """Генерирует DOT для одной функции."""
        lines = ["digraph CFG {", '  rankdir=TB;', '  node [shape=box, fontname="Courier"];', ""]
        lines.append(f'  label="{func.name}";')
        lines.append(f'  fontname="Arial";')
        lines.append("")

        for block in func.blocks:
            label = self._format_block_label(block)
            color = self._get_block_color(block)
            label = label.replace('"', '\\"').replace('\n', '\\n')
            lines.append(f'  {block.label} [label="{label}", style=filled, fillcolor={color}];')

        lines.append("")
        for block in func.blocks:
            for succ in block.successors:
                lines.append(f"  {block.label} -> {succ.label};")

        lines.append("}")
        return "\n".join(lines)

    def _format_block_label(self, block: BasicBlock) -> str:
        """Форматирует содержимое блока для метки."""
        label_lines = [f"{block.label}:"]
        for instr in block.instructions:
            instr_str = str(instr)
            # Заменяем пробелы в именах временных на подчёркивания для DOT
            # Но сохраняем оригинальное отображение
            label_lines.append(instr_str)
        return "\\l".join(label_lines) + "\\l"  # \\l для выравнивания влево

    def _get_block_color(self, block: BasicBlock) -> str:
        if block.label == "entry":
            return "lightgreen"
        elif not block.successors:
            return "lightcoral"
        elif any("RETURN" in str(instr) for instr in block.instructions):
            return "lightsalmon"
        return "lightblue"