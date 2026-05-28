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
if [ ${PIPESTATUS[0]} -ne 0 ]; then
    echo -e "${RED}Ошибка компиляции!${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Компиляция успешна${NC}"

echo -e "${YELLOW}[2/3] Ассемблирование и линковка...${NC}"
nasm -f elf64 -o /tmp/demo.o /tmp/demo.asm 2>/dev/null
gcc -no-pie -o /tmp/demo_program /tmp/demo.o 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${RED}Ошибка сборки!${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Готово${NC}"

echo -e "${YELLOW}[3/3] Запуск...${NC}"
echo ""
echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}  OUTPUT${NC}"
echo -e "${BLUE}==========================================${NC}"
echo ""

/tmp/demo_program
EXIT_CODE=$?

echo ""
echo -e "${BLUE}==========================================${NC}"
echo -e "  Exit code: ${GREEN}$EXIT_CODE${NC}"
echo -e "  Expected: ${GREEN}94${NC}"
if [ "$EXIT_CODE" -eq 94 ]; then
    echo -e "  Status: ${GREEN}✓ PASS${NC}"
else
    echo -e "  Status: ${RED}✗ FAIL${NC}"
fi
echo -e "${BLUE}==========================================${NC}"

rm -f /tmp/demo.asm /tmp/demo.o /tmp/demo_program

exit 0
