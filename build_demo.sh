#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
DEMO_FILE="$PROJECT_DIR/examples/quicksort.src"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}  MiniCompiler Demo - Quicksort${NC}"
echo -e "${BLUE}==========================================${NC}"
echo ""

echo -e "${YELLOW}[1/3] Компиляция...${NC}"
python -m lexer.cli --input "$DEMO_FILE" --mode compile --output /tmp/demo.asm 2>&1 | tail -1
if [ $? -ne 0 ]; then
    echo -e "${RED}Ошибка компиляции!${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Компиляция успешна${NC}"

echo -e "${YELLOW}[2/3] Ассемблирование...${NC}"
nasm -f elf64 -o /tmp/demo.o /tmp/demo.asm 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${RED}Ошибка ассемблирования!${NC}"
    exit 1
fi
nasm -f elf64 -o /tmp/runtime.o "$PROJECT_DIR/runtime/runtime.asm" 2>/dev/null
echo -e "${GREEN}✓ Ассемблирование успешно${NC}"

echo -e "${YELLOW}[3/3] Линковка и запуск...${NC}"
ld -o /tmp/demo_program /tmp/runtime.o /tmp/demo.o 2>/dev/null

echo ""
echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}  OUTPUT${NC}"
echo -e "${BLUE}==========================================${NC}"
echo ""

/tmp/demo_program
EXIT_CODE=$?

echo ""
echo -e "${BLUE}==========================================${NC}"
echo -e "  Array: [42, 23, 17, 8, 4]"
echo -e "  Sorted sum (exit code): ${GREEN}$EXIT_CODE${NC}"
echo -e "  Expected: 4+8+17+23+42 = ${GREEN}94${NC}"
if [ "$EXIT_CODE" -eq 94 ]; then
    echo -e "  Status: ${GREEN}✓ PASS${NC}"
else
    echo -e "  Status: ${RED}✗ FAIL${NC}"
fi
echo -e "${BLUE}==========================================${NC}"

rm -f /tmp/demo.asm /tmp/demo.o /tmp/runtime.o /tmp/demo_program

exit 0
