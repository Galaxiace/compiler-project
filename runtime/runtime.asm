; runtime/runtime.asm
; Минимальная runtime библиотека для MiniCompiler
; System V AMD64 ABI, Linux x86-64

section .text
global print_int, print_string, read_int, exit, _start
extern main

;------------------------------------------------------
; print_int - печатает целое число из RDI в stdout
;------------------------------------------------------
print_int:
    push rbp
    mov rbp, rsp
    sub rsp, 32              ; буфер для строки
    mov rax, rdi             ; число для печати
    
    ; Обработка отрицательных чисел
    test rax, rax
    jns .convert
    neg rax
    push rax
    mov rax, 1               ; syscall write
    mov rdi, 1               ; stdout
    mov rsi, minus_sign
    mov rdx, 1
    syscall
    pop rax
    
.convert:
    mov rcx, 10              ; делитель
    lea rsi, [rbp-1]         ; конец буфера
    mov byte [rsi], 0        ; нуль-терминатор
    
.convert_loop:
    xor rdx, rdx
    div rcx
    add dl, '0'
    dec rsi
    mov [rsi], dl
    test rax, rax
    jnz .convert_loop
    
    mov rdx, rbp
    sub rdx, rsi
    dec rdx                  ; длина строки
    mov rax, 1               ; syscall write
    mov rdi, 1               ; stdout
    syscall
    
    mov rsp, rbp
    pop rbp
    ret

section .data
minus_sign db '-'

section .text
;------------------------------------------------------
; print_string - печатает строку
; RDI = указатель на строку, RSI = длина
;------------------------------------------------------
print_string:
    mov rax, 1               ; syscall write
    mov rdx, rsi             ; длина строки
    mov rsi, rdi             ; указатель на строку
    mov rdi, 1               ; stdout
    syscall
    ret

;------------------------------------------------------
; read_int - читает целое число из stdin (возвращает в RAX)
;------------------------------------------------------
read_int:
    push rbp
    mov rbp, rsp
    sub rsp, 32              ; буфер для ввода
    
    mov rax, 0               ; syscall read
    mov rdi, 0               ; stdin
    mov rsi, rsp             ; буфер
    mov rdx, 32              ; максимум 32 байта
    syscall
    
    ; Преобразование строки в число
    xor rax, rax             ; результат
    xor rcx, rcx             ; индекс
    mov rsi, rsp             ; начало буфера
    
    ; Проверка на отрицательное число
    movzx rdx, byte [rsi]
    cmp rdx, '-'
    jne .parse_loop
    inc rsi                  ; пропускаем минус
    mov r8, 1                ; флаг отрицательности
    jmp .parse_digit
    
.parse_loop:
    mov rsi, rsp
    xor r8, r8               ; положительное число
    
.parse_digit:
    movzx rdx, byte [rsi]
    cmp rdx, 0xa             ; новая строка
    je .done
    cmp rdx, '0'
    jl .done
    cmp rdx, '9'
    jg .done
    
    sub rdx, '0'
    imul rax, 10
    add rax, rdx
    inc rsi
    jmp .parse_digit
    
.done:
    test r8, r8
    jz .positive
    neg rax                  ; делаем отрицательным
    
.positive:
    mov rsp, rbp
    pop rbp
    ret

;------------------------------------------------------
; exit - завершает программу с кодом из RDI
;------------------------------------------------------
exit:
    mov rax, 60              ; syscall exit
    syscall

;------------------------------------------------------
; _start - точка входа в программу
;------------------------------------------------------
_start:
    ; Сохраняем argc и argv (при необходимости)
    mov rdi, [rsp]           ; argc
    lea rsi, [rsp+8]         ; argv
    
    call main
    
    mov rdi, rax             ; код возврата из main
    call exit